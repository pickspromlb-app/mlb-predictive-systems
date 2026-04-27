import sys
import psycopg
from shared.settings import get_settings

SQL = """
with base as (
  select
    s.analysis_date,
    s.analysis_timestamp,
    s.game_pk,
    s.team_id,
    s.opponent_team_id,
    s.system_id,
    s.system_version,

    tp.avg as team_avg_l5,
    tp.obp as team_obp_l5,
    tp.slg as team_slg_l5,
    tp.ops as team_ops_l5,
    tp.iso as team_iso_l5,
    tp.babip as team_babip_l5,
    tp.woba_internal as team_woba_l5,
    tp.wrc_plus_internal as team_wrc_plus_l5,
    tp.runs_scored_avg as team_runs_scored_avg_l5,

    opp.whip as opponent_whip_l5,
    opp.era as opponent_era_l5,
    opp.fip_internal as opponent_fip_l5,
    opp.runs_allowed_avg as opponent_runs_allowed_avg_l5,
    opp.k_bb_rate as opponent_k_bb_rate_l5,
    opp.hr_per_9 as opponent_hr9_l5

  from propicks.analysis_snapshots s

  left join propicks.daily_team_profile tp
    on tp.profile_date = s.analysis_date
    and tp.team_id = s.team_id
    and tp.stat_window = 'L5'

  left join propicks.team_pitching_profile opp
    on opp.profile_date = s.analysis_date
    and opp.team_id = s.opponent_team_id
    and opp.stat_window = 'L5'

  where s.target_metric = 'pre_game_offensive_edge'
    and s.confidence_tier = 'A'
    and opp.whip >= 1.35
    and opp.runs_allowed_avg >= 5.0
    and (%s::date is null or s.analysis_date = %s::date)
),

tr3 as (
  insert into propicks.analysis_snapshots (
    analysis_date,
    analysis_timestamp,
    game_pk,
    team_id,
    opponent_team_id,
    system_id,
    system_version,
    market_type,
    target_metric,
    score,
    confidence_tier,
    status,
    filters_passed,
    filters_failed,
    metrics_snapshot,
    risk_flags,
    analysis_text,
    grade_status,
    created_at,
    updated_at
  )
  select
    analysis_date,
    now(),
    game_pk,
    team_id,
    opponent_team_id,
    system_id,
    system_version,
    'TEAM_RUNS',
    'team_3plus_runs',
    92.5,
    'A',
    'PRE_GAME',
    jsonb_build_array(
      'OFFENSIVE_EDGE_A',
      'OPPONENT_WHIP_L5_GTE_1_35',
      'OPPONENT_RUNS_ALLOWED_AVG_L5_GTE_5_0'
    ),
    '[]'::jsonb,
    jsonb_build_object(
      'team_avg_l5', team_avg_l5,
      'team_obp_l5', team_obp_l5,
      'team_slg_l5', team_slg_l5,
      'team_ops_l5', team_ops_l5,
      'team_iso_l5', team_iso_l5,
      'team_babip_l5', team_babip_l5,
      'team_woba_l5', team_woba_l5,
      'team_wrc_plus_l5', team_wrc_plus_l5,
      'team_runs_scored_avg_l5', team_runs_scored_avg_l5,
      'opponent_whip_l5', opponent_whip_l5,
      'opponent_era_l5', opponent_era_l5,
      'opponent_fip_l5', opponent_fip_l5,
      'opponent_runs_allowed_avg_l5', opponent_runs_allowed_avg_l5,
      'opponent_k_bb_rate_l5', opponent_k_bb_rate_l5,
      'opponent_hr9_l5', opponent_hr9_l5,
      'backtest_initial_sample', 40,
      'backtest_initial_hit_rate', 0.925
    ),
    '[]'::jsonb,
    'ProPicksMLB Team Runs 3+ Pressure Filter v1 | Offensive Edge A + Opp WHIP L5 >= 1.35 + Opp Runs Allowed Avg L5 >= 5.0',
    'PENDING',
    now(),
    now()
  from base

  on conflict (
    analysis_date,
    game_pk,
    team_id,
    market_type,
    target_metric,
    system_version
  )
  do update set
    score = excluded.score,
    confidence_tier = excluded.confidence_tier,
    status = excluded.status,
    filters_passed = excluded.filters_passed,
    filters_failed = excluded.filters_failed,
    metrics_snapshot = excluded.metrics_snapshot,
    risk_flags = excluded.risk_flags,
    analysis_text = excluded.analysis_text,
    updated_at = now()

  returning id
),

tr5 as (
  insert into propicks.analysis_snapshots (
    analysis_date,
    analysis_timestamp,
    game_pk,
    team_id,
    opponent_team_id,
    system_id,
    system_version,
    market_type,
    target_metric,
    score,
    confidence_tier,
    status,
    filters_passed,
    filters_failed,
    metrics_snapshot,
    risk_flags,
    analysis_text,
    grade_status,
    created_at,
    updated_at
  )
  select
    analysis_date,
    now(),
    game_pk,
    team_id,
    opponent_team_id,
    system_id,
    system_version,
    'TEAM_RUNS',
    'team_5plus_runs',
    75.0,
    'B',
    'PRE_GAME',
    jsonb_build_array(
      'OFFENSIVE_EDGE_A',
      'OPPONENT_WHIP_L5_GTE_1_35',
      'OPPONENT_RUNS_ALLOWED_AVG_L5_GTE_5_0'
    ),
    '[]'::jsonb,
    jsonb_build_object(
      'team_avg_l5', team_avg_l5,
      'team_obp_l5', team_obp_l5,
      'team_slg_l5', team_slg_l5,
      'team_ops_l5', team_ops_l5,
      'team_iso_l5', team_iso_l5,
      'team_babip_l5', team_babip_l5,
      'team_woba_l5', team_woba_l5,
      'team_wrc_plus_l5', team_wrc_plus_l5,
      'team_runs_scored_avg_l5', team_runs_scored_avg_l5,
      'opponent_whip_l5', opponent_whip_l5,
      'opponent_era_l5', opponent_era_l5,
      'opponent_fip_l5', opponent_fip_l5,
      'opponent_runs_allowed_avg_l5', opponent_runs_allowed_avg_l5,
      'opponent_k_bb_rate_l5', opponent_k_bb_rate_l5,
      'opponent_hr9_l5', opponent_hr9_l5,
      'backtest_initial_sample', 40,
      'backtest_initial_hit_rate', 0.75
    ),
    '[]'::jsonb,
    'ProPicksMLB Team Runs 5+ Pressure Filter v1 | Offensive Edge A + Opp WHIP L5 >= 1.35 + Opp Runs Allowed Avg L5 >= 5.0',
    'PENDING',
    now(),
    now()
  from base

  on conflict (
    analysis_date,
    game_pk,
    team_id,
    market_type,
    target_metric,
    system_version
  )
  do update set
    score = excluded.score,
    confidence_tier = excluded.confidence_tier,
    status = excluded.status,
    filters_passed = excluded.filters_passed,
    filters_failed = excluded.filters_failed,
    metrics_snapshot = excluded.metrics_snapshot,
    risk_flags = excluded.risk_flags,
    analysis_text = excluded.analysis_text,
    updated_at = now()

  returning id
)

select
  (select count(*) from base) as qualified_teams,
  (select count(*) from tr3) as tr3_snapshots_created,
  (select count(*) from tr5) as tr5_snapshots_created;
"""

def main():
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    settings = get_settings()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL, (target_date, target_date))
            row = cur.fetchone()
        conn.commit()

    print({
        "target_date": target_date or "ALL",
        "qualified_teams": row[0],
        "tr3_snapshots_created": row[1],
        "tr5_snapshots_created": row[2],
    })

if __name__ == "__main__":
    main()
