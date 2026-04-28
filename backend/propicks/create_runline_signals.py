import sys
from datetime import date

from shared.db import get_conn, fetch_all


def create_runline_signals(analysis_date: str) -> dict:
    sql = """
    with team_games as (
      select
        g.game_pk,
        g.game_date as analysis_date,
        g.status,
        g.detailed_state,
        g.away_team_id as team_id,
        g.home_team_id as opponent_team_id,
        'AWAY' as home_away,
        g.away_score as team_score,
        g.home_score as opponent_score
      from core.games g
      where g.game_date = %s::date

      union all

      select
        g.game_pk,
        g.game_date as analysis_date,
        g.status,
        g.detailed_state,
        g.home_team_id as team_id,
        g.away_team_id as opponent_team_id,
        'HOME' as home_away,
        g.home_score as team_score,
        g.away_score as opponent_score
      from core.games g
      where g.game_date = %s::date
    ),

    dataset as (
      select
        tg.*,

        t.abbreviation as team_abbr,
        t.team_name as team_name,
        o.abbreviation as opponent_abbr,
        o.team_name as opponent_name,

        case
          when lower(coalesce(tg.status, '')) = 'final'
            or lower(coalesce(tg.detailed_state, '')) like '%%final%%'
            or lower(coalesce(tg.detailed_state, '')) like '%%completed%%'
          then true
          else false
        end as is_final,

        case
          when tg.team_score is not null and tg.opponent_score is not null
          then tg.team_score - tg.opponent_score
          else null
        end as run_margin,

        dt3.runs_scored_avg as team_rs_l3,
        dt3.runs_allowed_avg as team_ra_l3,
        (dt3.runs_scored_avg - dto3.runs_scored_avg) as rs_edge_l3,
        (dto3.runs_allowed_avg - dt3.runs_allowed_avg) as ra_edge_l3,
        (dt3.run_diff_avg - dto3.run_diff_avg) as run_diff_edge_l3,
        (pto3.era - pt3.era) as era_edge_l3,
        (pto3.whip - pt3.whip) as whip_edge_l3,

        dt5.runs_scored_avg as team_rs_l5,
        dt5.runs_allowed_avg as team_ra_l5,
        (dt5.runs_scored_avg - dto5.runs_scored_avg) as rs_edge_l5,
        (dto5.runs_allowed_avg - dt5.runs_allowed_avg) as ra_edge_l5,
        (dt5.run_diff_avg - dto5.run_diff_avg) as run_diff_edge_l5,
        (pto5.era - pt5.era) as era_edge_l5,
        (pto5.whip - pt5.whip) as whip_edge_l5

      from team_games tg

      join core.teams t
        on t.team_id = tg.team_id
      join core.teams o
        on o.team_id = tg.opponent_team_id

      join propicks.daily_team_profile dt3
        on dt3.profile_date = tg.analysis_date
       and dt3.team_id = tg.team_id
       and dt3.stat_window = 'L3'
      join propicks.daily_team_profile dto3
        on dto3.profile_date = tg.analysis_date
       and dto3.team_id = tg.opponent_team_id
       and dto3.stat_window = 'L3'
      join propicks.team_pitching_profile pt3
        on pt3.profile_date = tg.analysis_date
       and pt3.team_id = tg.team_id
       and pt3.stat_window = 'L3'
      join propicks.team_pitching_profile pto3
        on pto3.profile_date = tg.analysis_date
       and pto3.team_id = tg.opponent_team_id
       and pto3.stat_window = 'L3'

      join propicks.daily_team_profile dt5
        on dt5.profile_date = tg.analysis_date
       and dt5.team_id = tg.team_id
       and dt5.stat_window = 'L5'
      join propicks.daily_team_profile dto5
        on dto5.profile_date = tg.analysis_date
       and dto5.team_id = tg.opponent_team_id
       and dto5.stat_window = 'L5'
      join propicks.team_pitching_profile pt5
        on pt5.profile_date = tg.analysis_date
       and pt5.team_id = tg.team_id
       and pt5.stat_window = 'L5'
      join propicks.team_pitching_profile pto5
        on pto5.profile_date = tg.analysis_date
       and pto5.team_id = tg.opponent_team_id
       and pto5.stat_window = 'L5'
    ),

    flags as (
      select
        *,
        (
          team_rs_l3 >= 4.0
          and team_ra_l3 <= 5.0
          and rs_edge_l3 >= 0.0
          and ra_edge_l3 >= 0.0
          and run_diff_edge_l3 >= 0.5
          and era_edge_l3 >= 2.0
          and whip_edge_l3 >= 0.05
        ) as pass_momentum_l3,

        (
          team_rs_l5 >= 4.0
          and team_ra_l5 <= 5.0
          and rs_edge_l5 >= 0.0
          and ra_edge_l5 >= 0.0
          and run_diff_edge_l5 >= 0.5
          and era_edge_l5 >= 2.0
          and whip_edge_l5 >= 0.05
        ) as pass_l5
      from dataset
    ),

    candidates as (
      select
        analysis_date,
        game_pk,
        'RUN_LINE_MOMENTUM_L3_V1' as system_id,
        'v1.0' as version,
        'MOMENTUM_L3' as run_line_tier,
        -1.5::numeric as target_line,
        team_id,
        team_abbr,
        team_name,
        opponent_team_id,
        opponent_abbr,
        opponent_name,
        home_away,
        team_score,
        opponent_score,
        run_margin,
        case
          when is_final and run_margin is not null then run_margin >= 2
          else null
        end as covered_runline,
        status,
        detailed_state,
        is_final,
        team_rs_l3,
        team_ra_l3,
        rs_edge_l3,
        ra_edge_l3,
        run_diff_edge_l3,
        era_edge_l3,
        whip_edge_l3,
        team_rs_l5,
        team_ra_l5,
        rs_edge_l5,
        ra_edge_l5,
        run_diff_edge_l5,
        era_edge_l5,
        whip_edge_l5
      from flags
      where pass_momentum_l3 is true

      union all

      select
        analysis_date,
        game_pk,
        'RUN_LINE_CONFLUENCE_L3_L5_V1' as system_id,
        'v1.0' as version,
        'CONFLUENCE_L3_L5' as run_line_tier,
        -1.5::numeric as target_line,
        team_id,
        team_abbr,
        team_name,
        opponent_team_id,
        opponent_abbr,
        opponent_name,
        home_away,
        team_score,
        opponent_score,
        run_margin,
        case
          when is_final and run_margin is not null then run_margin >= 2
          else null
        end as covered_runline,
        status,
        detailed_state,
        is_final,
        team_rs_l3,
        team_ra_l3,
        rs_edge_l3,
        ra_edge_l3,
        run_diff_edge_l3,
        era_edge_l3,
        whip_edge_l3,
        team_rs_l5,
        team_ra_l5,
        rs_edge_l5,
        ra_edge_l5,
        run_diff_edge_l5,
        era_edge_l5,
        whip_edge_l5
      from flags
      where pass_momentum_l3 is true
        and pass_l5 is true
    ),

    upserted as (
      insert into propicks.run_line_signals (
        analysis_date,
        game_pk,
        system_id,
        version,
        run_line_tier,
        target_line,
        team_id,
        team_abbr,
        team_name,
        opponent_team_id,
        opponent_abbr,
        opponent_name,
        home_away,
        team_score,
        opponent_score,
        run_margin,
        covered_runline,
        status,
        detailed_state,
        is_final,
        team_rs_l3,
        team_ra_l3,
        rs_edge_l3,
        ra_edge_l3,
        run_diff_edge_l3,
        era_edge_l3,
        whip_edge_l3,
        team_rs_l5,
        team_ra_l5,
        rs_edge_l5,
        ra_edge_l5,
        run_diff_edge_l5,
        era_edge_l5,
        whip_edge_l5,
        updated_at
      )
      select
        analysis_date,
        game_pk,
        system_id,
        version,
        run_line_tier,
        target_line,
        team_id,
        team_abbr,
        team_name,
        opponent_team_id,
        opponent_abbr,
        opponent_name,
        home_away,
        team_score,
        opponent_score,
        run_margin,
        covered_runline,
        status,
        detailed_state,
        is_final,
        team_rs_l3,
        team_ra_l3,
        rs_edge_l3,
        ra_edge_l3,
        run_diff_edge_l3,
        era_edge_l3,
        whip_edge_l3,
        team_rs_l5,
        team_ra_l5,
        rs_edge_l5,
        ra_edge_l5,
        run_diff_edge_l5,
        era_edge_l5,
        whip_edge_l5,
        now()
      from candidates
      on conflict (analysis_date, game_pk, system_id, team_id)
      do update set
        run_line_tier = excluded.run_line_tier,
        target_line = excluded.target_line,
        team_abbr = excluded.team_abbr,
        team_name = excluded.team_name,
        opponent_team_id = excluded.opponent_team_id,
        opponent_abbr = excluded.opponent_abbr,
        opponent_name = excluded.opponent_name,
        home_away = excluded.home_away,
        team_score = excluded.team_score,
        opponent_score = excluded.opponent_score,
        run_margin = excluded.run_margin,
        covered_runline = excluded.covered_runline,
        status = excluded.status,
        detailed_state = excluded.detailed_state,
        is_final = excluded.is_final,
        team_rs_l3 = excluded.team_rs_l3,
        team_ra_l3 = excluded.team_ra_l3,
        rs_edge_l3 = excluded.rs_edge_l3,
        ra_edge_l3 = excluded.ra_edge_l3,
        run_diff_edge_l3 = excluded.run_diff_edge_l3,
        era_edge_l3 = excluded.era_edge_l3,
        whip_edge_l3 = excluded.whip_edge_l3,
        team_rs_l5 = excluded.team_rs_l5,
        team_ra_l5 = excluded.team_ra_l5,
        rs_edge_l5 = excluded.rs_edge_l5,
        ra_edge_l5 = excluded.ra_edge_l5,
        run_diff_edge_l5 = excluded.run_diff_edge_l5,
        era_edge_l5 = excluded.era_edge_l5,
        whip_edge_l5 = excluded.whip_edge_l5,
        updated_at = now()
      returning system_id
    )

    select
      count(*)::int as total_upserted,
      count(*) filter (where system_id = 'RUN_LINE_MOMENTUM_L3_V1')::int as momentum_l3,
      count(*) filter (where system_id = 'RUN_LINE_CONFLUENCE_L3_L5_V1')::int as confluence_l3_l5
    from upserted
    """

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (analysis_date, analysis_date))
            result = cur.fetchone()

    return dict(result)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m propicks.create_runline_signals YYYY-MM-DD")

    analysis_date = sys.argv[1]
    date.fromisoformat(analysis_date)

    result = create_runline_signals(analysis_date)
    print(result)

    rows = fetch_all("""
    select
      system_id,
      count(*)::int as signals
    from propicks.run_line_signals
    where analysis_date = %s::date
    group by system_id
    order by system_id
    """, (analysis_date,))

    for r in rows:
        print(dict(r))


if __name__ == "__main__":
    main()
