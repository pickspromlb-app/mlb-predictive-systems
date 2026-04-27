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
    s.system_id,
    s.system_version,
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
    and s.target_metric = 'pre_game_offensive_edge'
    and (%s::date is null or s.analysis_date = %s::date)
    and coalesce(gl.away_runs, g.away_score) is not null
    and coalesce(gl.home_runs, g.home_score) is not null
),
graded as (
  select
    id,
    case
      when team_id = away_team_id and away_runs > home_runs then true
      when team_id = home_team_id and home_runs > away_runs then true
      else false
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
  and target_metric = 'pre_game_offensive_edge'
  and (%s::date is null or analysis_date = %s::date);
"""

PERFORMANCE_SQL = """
insert into ops.system_performance_summary (
  system_name,
  system_version,
  target_metric,
  sample_size,
  wins,
  losses,
  pushes,
  success_rate,
  last_updated
)
select
  'ProPicksMLB' as system_name,
  'v1.0' as system_version,
  'pre_game_offensive_edge' as target_metric,
  count(*)::int as sample_size,
  count(*) filter (where success = true)::int as wins,
  count(*) filter (where success = false)::int as losses,
  0::int as pushes,
  round(
    (count(*) filter (where success = true))::numeric
    / nullif(count(*), 0),
    4
  ) as success_rate,
  now() as last_updated
from propicks.analysis_snapshots
where grade_status = 'GRADED'
  and target_metric = 'pre_game_offensive_edge'
on conflict (system_name, system_version, target_metric)
do update set
  sample_size = excluded.sample_size,
  wins = excluded.wins,
  losses = excluded.losses,
  pushes = excluded.pushes,
  success_rate = excluded.success_rate,
  last_updated = now();
"""

INSERT_RUN_SQL = """
insert into ops.postgame_grade_runs (
  grade_date,
  system_name,
  system_version,
  games_checked,
  records_graded,
  wins,
  losses,
  pushes,
  success_rate,
  status,
  finished_at,
  notes
)
values (
  coalesce(%s::date, current_date),
  'ProPicksMLB',
  'v1.0',
  %s,
  %s,
  %s,
  %s,
  %s,
  %s,
  'SUCCESS',
  now(),
  'Base grader: pre_game_offensive_edge graded as team won game.'
);
"""

def main():
    grade_date = sys.argv[1] if len(sys.argv) > 1 else None
    settings = get_settings()

    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(GRADE_SQL, (grade_date, grade_date))
            cur.execute(SUMMARY_SQL, (grade_date, grade_date))
            summary = cur.fetchone()

            records_graded, wins, losses, pushes, success_rate = summary

            cur.execute(
                """
                select count(distinct game_pk)::int
                from propicks.analysis_snapshots
                where grade_status = 'GRADED'
                  and target_metric = 'pre_game_offensive_edge'
                  and (%s::date is null or analysis_date = %s::date)
                """,
                (grade_date, grade_date),
            )
            games_checked = cur.fetchone()[0]

            cur.execute(PERFORMANCE_SQL)

            cur.execute(
                INSERT_RUN_SQL,
                (
                    grade_date,
                    games_checked,
                    records_graded,
                    wins,
                    losses,
                    pushes,
                    success_rate,
                ),
            )

        conn.commit()

    print({
        "system": "ProPicksMLB",
        "target_metric": "pre_game_offensive_edge",
        "grade_date": grade_date or "ALL",
        "games_checked": games_checked,
        "records_graded": records_graded,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "success_rate": float(success_rate) if success_rate is not None else None
    })

if __name__ == "__main__":
    main()
