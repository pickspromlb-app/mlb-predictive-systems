import sys
from datetime import date

from shared.db import fetch_one


def grade_saved_daily_signals(analysis_date: str) -> dict:
    graded = fetch_one(
        """
        with base as (
          select
            s.id,
            s.signal_type,
            s.system_id,
            s.team_id,
            s.primary_target,
            s.secondary_target,
            g.status,
            g.detailed_state,
            g.away_team_id,
            g.home_team_id,
            g.away_score,
            g.home_score,

            case
              when s.primary_target is null then null
              else nullif(substring(s.primary_target from '([0-9]+)'), '')::int
            end as primary_number,

            case
              when s.secondary_target is null then null
              else nullif(substring(s.secondary_target from '([0-9]+)'), '')::int
            end as secondary_number

          from propicks.saved_daily_signals s
          join core.games g
            on g.game_pk = s.game_pk
          where s.analysis_date = %s::date
        ),

        scored as (
          select
            b.*,

            case
              when lower(coalesce(b.status, '')) = 'final'
                and b.away_score is not null
                and b.home_score is not null
              then true
              else false
            end as game_is_final,

            case
              when b.team_id = b.away_team_id then b.away_score
              when b.team_id = b.home_team_id then b.home_score
              else null
            end as computed_score_for,

            case
              when b.team_id = b.away_team_id then b.home_score
              when b.team_id = b.home_team_id then b.away_score
              else null
            end as computed_score_against,

            case
              when b.away_score is not null and b.home_score is not null
              then b.away_score + b.home_score
              else null
            end as computed_total_runs

          from base b
        ),

        graded_logic as (
          select
            s.*,

            case
              when not s.game_is_final then null

              when s.signal_type = 'MONEYLINE'
              then s.computed_score_for > s.computed_score_against

              when s.signal_type = 'TEAM_RUNS'
                and s.primary_number is not null
              then s.computed_score_for >= s.primary_number

              when s.signal_type = 'RUN_LINE'
              then (s.computed_score_for - s.computed_score_against) >= 2

              when s.signal_type = 'TOTALS_OVER'
                and s.primary_number is not null
              then s.computed_total_runs >= s.primary_number

              when s.signal_type = 'TOTALS_UNDER'
                and s.primary_number is not null
              then s.computed_total_runs <= s.primary_number

              else null
            end as computed_hit_primary,

            case
              when not s.game_is_final then null
              when s.secondary_number is null then null

              when s.signal_type = 'TEAM_RUNS'
              then s.computed_score_for >= s.secondary_number

              when s.signal_type = 'TOTALS_OVER'
              then s.computed_total_runs >= s.secondary_number

              when s.signal_type = 'TOTALS_UNDER'
              then s.computed_total_runs <= s.secondary_number

              else null
            end as computed_hit_secondary

          from scored s
        ),

        updated as (
          update propicks.saved_daily_signals s
          set
            is_final = g.game_is_final,

            result_status = case
              when not g.game_is_final then 'PENDING'
              when g.computed_hit_primary is true then 'WIN'
              when g.computed_hit_primary is false then 'LOSS'
              else 'PENDING'
            end,

            score_for = case
              when g.game_is_final then g.computed_score_for
              else null
            end,

            score_against = case
              when g.game_is_final then g.computed_score_against
              else null
            end,

            away_score = case
              when g.game_is_final then g.away_score
              else null
            end,

            home_score = case
              when g.game_is_final then g.home_score
              else null
            end,

            total_runs = case
              when g.game_is_final then g.computed_total_runs
              else null
            end,

            hit_primary = case
              when g.game_is_final then g.computed_hit_primary
              else null
            end,

            hit_secondary = case
              when g.game_is_final then g.computed_hit_secondary
              else null
            end,

            updated_at = now()

          from graded_logic g
          where s.id = g.id
          returning
            s.id,
            s.result_status,
            s.is_final
        )

        select
          count(*)::int as total_checked,
          count(*) filter (where result_status = 'PENDING')::int as pending,
          count(*) filter (where result_status = 'WIN')::int as wins,
          count(*) filter (where result_status = 'LOSS')::int as losses,
          count(*) filter (where is_final is true)::int as finalized
        from updated
        """,
        (analysis_date,),
    )

    return {
        "status": "graded",
        "analysis_date": analysis_date,
        "total_checked": graded["total_checked"],
        "finalized": graded["finalized"],
        "pending": graded["pending"],
        "wins": graded["wins"],
        "losses": graded["losses"],
    }


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m propicks.grade_saved_daily_signals YYYY-MM-DD")

    analysis_date = sys.argv[1]
    date.fromisoformat(analysis_date)

    result = grade_saved_daily_signals(analysis_date)
    print(result)


if __name__ == "__main__":
    main()
