import sys
import psycopg
from shared.settings import get_settings

GRADE_SQL = """
with eligible as (
  select
    s.id,
    s.analysis_date,
    s.game_pk,
    s.team_id,
    s.target_metric,
    g.away_team_id,
    g.home_team_id,
    coalesce(gl.away_runs, g.away_score) as away_runs,
    coalesce(gl.home_runs, g.home_score) as home_runs
  from propicks.analysis_snapshots s
  join core.games g
    on g.game_pk = s.game_pk
  left join core.game_linescore gl
    on gl.game_pk = s.game_pk
  where s.grade_status = 'PENDING'
    and s.target_metric in ('team_3plus_runs', 'team_5plus_runs')
    and (%s::date is null or s.analysis_date = %s::date)
    and coalesce(gl.away_runs, g.away_score) is not null
    and coalesce(gl.home_runs, g.home_score) is not null
),
graded as (
  select
    id,
    case
      when team_id = away_team_id then away_runs
      when team_id = home_team_id then home_runs
      else null
    end as team_runs,
    case
      when target_metric = 'team_3plus_runs'
        then (
          case
            when team_id = away_team_id then away_runs
            when team_id = home_team_id then home_runs
            else null
          end
        ) >= 3
      when target_metric = 'team_5plus_runs'
        then (
          case
            when team_id = away_team_id then away_runs
            when team_id = home_team_id then home_runs
            else null
          end
        ) >= 5
      else null
    end as actual_result
  from eligible
)
update propicks.analysis_snapshots s
set
  actual_result = graded.actual_result,
  success = graded.actual_result,
  grade_status = 'GRADED',
  graded_at = now(),
  updated_at = now()
from graded
where s.id = graded.id;
"""

SUMMARY_SQL = """
select
  target_metric,
  count(*)::int as records_graded,
  count(*) filter (where success = true)::int as wins,
  count(*) filter (where success = false)::int as losses,
  0::int as pushes,
  round(
    (count(*) filter (where success = true))::numeric
    / nullif(count(*), 0),
    4
  ) as success_rate
from propicks.analysis_snapshots
where grade_status = 'GRADED'
  and target_metric in ('team_3plus_runs', 'team_5plus_runs')
  and (%s::date is null or analysis_date = %s::date)
group by target_metric
order by target_metric;
"""

def main():
    grade_date = sys.argv[1] if len(sys.argv) > 1 else None
    settings = get_settings()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(GRADE_SQL, (grade_date, grade_date))
            cur.execute(SUMMARY_SQL, (grade_date, grade_date))
            rows = cur.fetchall()
        conn.commit()

    print({
        "system": "ProPicksMLB",
        "grader": "team_runs",
        "grade_date": grade_date or "ALL",
        "summary": [
            {
                "target_metric": r[0],
                "records_graded": r[1],
                "wins": r[2],
                "losses": r[3],
                "pushes": r[4],
                "success_rate": float(r[5]) if r[5] is not None else None,
            }
            for r in rows
        ],
    })

if __name__ == "__main__":
    main()
