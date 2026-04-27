import sys
import json
import psycopg
from psycopg.rows import dict_row
from shared.settings import get_settings

SUMMARY_SQL = """
with base as (
  select
    s.analysis_date,
    s.market_type,
    s.target_metric,
    s.confidence_tier,
    s.team_id,
    t.team_name,
    s.score,
    s.success
  from propicks.analysis_snapshots s
  left join core.teams t
    on t.team_id = s.team_id
  where s.grade_status = 'GRADED'
    and s.analysis_date = %s::date
    and s.target_metric in ('team_3plus_runs', 'team_5plus_runs')
),
overall as (
  select
    count(*)::int as total_records,
    count(*) filter (where success = true)::int as wins,
    count(*) filter (where success = false)::int as losses,
    0::int as pushes,
    round(
      count(*) filter (where success = true)::numeric / nullif(count(*), 0),
      4
    ) as success_rate
  from base
),
by_metric as (
  select coalesce(jsonb_agg(
    jsonb_build_object(
      'target_metric', target_metric,
      'sample_size', sample_size,
      'wins', wins,
      'losses', losses,
      'success_rate', success_rate
    )
    order by target_metric
  ), '[]'::jsonb) as data
  from (
    select
      target_metric,
      count(*)::int as sample_size,
      count(*) filter (where success = true)::int as wins,
      count(*) filter (where success = false)::int as losses,
      round(
        count(*) filter (where success = true)::numeric / nullif(count(*), 0),
        4
      ) as success_rate
    from base
    group by target_metric
  ) x
),
by_tier as (
  select coalesce(jsonb_agg(
    jsonb_build_object(
      'confidence_tier', confidence_tier,
      'sample_size', sample_size,
      'wins', wins,
      'losses', losses,
      'success_rate', success_rate
    )
    order by confidence_tier
  ), '[]'::jsonb) as data
  from (
    select
      confidence_tier,
      count(*)::int as sample_size,
      count(*) filter (where success = true)::int as wins,
      count(*) filter (where success = false)::int as losses,
      round(
        count(*) filter (where success = true)::numeric / nullif(count(*), 0),
        4
      ) as success_rate
    from base
    group by confidence_tier
  ) x
),
top_wins as (
  select coalesce(jsonb_agg(
    jsonb_build_object(
      'team', team_name,
      'target_metric', target_metric,
      'score', score,
      'result', 'WIN'
    )
    order by score desc nulls last
  ), '[]'::jsonb) as data
  from (
    select *
    from base
    where success = true
    order by score desc nulls last
    limit 10
  ) x
),
top_losses as (
  select coalesce(jsonb_agg(
    jsonb_build_object(
      'team', team_name,
      'target_metric', target_metric,
      'score', score,
      'result', 'LOSS'
    )
    order by score desc nulls last
  ), '[]'::jsonb) as data
  from (
    select *
    from base
    where success = false
    order by score desc nulls last
    limit 10
  ) x
)
select
  overall.total_records,
  overall.wins,
  overall.losses,
  overall.pushes,
  overall.success_rate,
  by_metric.data as by_target_metric,
  by_tier.data as by_confidence_tier,
  top_wins.data as top_wins,
  top_losses.data as top_losses
from overall, by_metric, by_tier, top_wins, top_losses;
"""

UPSERT_SQL = """
insert into ops.postgame_daily_summary (
  summary_date,
  system_name,
  system_version,
  total_records,
  wins,
  losses,
  pushes,
  success_rate,
  by_target_metric,
  by_confidence_tier,
  top_wins,
  top_losses,
  summary_text,
  updated_at
)
values (
  %(summary_date)s,
  'ProPicksMLB',
  'v1.0',
  %(total_records)s,
  %(wins)s,
  %(losses)s,
  %(pushes)s,
  %(success_rate)s,
  %(by_target_metric)s::jsonb,
  %(by_confidence_tier)s::jsonb,
  %(top_wins)s::jsonb,
  %(top_losses)s::jsonb,
  %(summary_text)s,
  now()
)
on conflict (summary_date, system_name, system_version)
do update set
  total_records = excluded.total_records,
  wins = excluded.wins,
  losses = excluded.losses,
  pushes = excluded.pushes,
  success_rate = excluded.success_rate,
  by_target_metric = excluded.by_target_metric,
  by_confidence_tier = excluded.by_confidence_tier,
  top_wins = excluded.top_wins,
  top_losses = excluded.top_losses,
  summary_text = excluded.summary_text,
  updated_at = now();
"""

def pct(value):
    if value is None:
        return "0.0%"
    return f"{float(value) * 100:.1f}%"

def build_summary_text(summary_date, row):
    lines = [
        f"Resumen ProPicksMLB — {summary_date}",
        "",
        f"Total analizados: {row['total_records']}",
        f"Ganados: {row['wins']}",
        f"Perdidos: {row['losses']}",
        f"Acierto: {pct(row['success_rate'])}",
        "",
        "Por mercado:"
    ]

    for item in row["by_target_metric"]:
        lines.append(
            f"- {item['target_metric']}: {item['wins']}-{item['losses']} ({pct(item['success_rate'])})"
        )

    return "\n".join(lines)

def main():
    if len(sys.argv) < 2:
        print("Uso: python -m propicks.postgame_daily_summary YYYY-MM-DD")
        sys.exit(1)

    summary_date = sys.argv[1]
    settings = get_settings()

    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL, (summary_date,))
            row = cur.fetchone()

            if not row or row["total_records"] == 0:
                print({
                    "system": "ProPicksMLB",
                    "summary_date": summary_date,
                    "status": "NO_GRADED_RECORDS"
                })
                return

            summary_text = build_summary_text(summary_date, row)

            payload = {
                "summary_date": summary_date,
                "total_records": row["total_records"],
                "wins": row["wins"],
                "losses": row["losses"],
                "pushes": row["pushes"],
                "success_rate": row["success_rate"],
                "by_target_metric": json.dumps(row["by_target_metric"]),
                "by_confidence_tier": json.dumps(row["by_confidence_tier"]),
                "top_wins": json.dumps(row["top_wins"]),
                "top_losses": json.dumps(row["top_losses"]),
                "summary_text": summary_text,
            }

            cur.execute(UPSERT_SQL, payload)

        conn.commit()

    print({
        "system": "ProPicksMLB",
        "summary_date": summary_date,
        "total_records": row["total_records"],
        "wins": row["wins"],
        "losses": row["losses"],
        "success_rate": float(row["success_rate"]) if row["success_rate"] is not None else None,
        "status": "SUMMARY_CREATED"
    })
    print(summary_text)

if __name__ == "__main__":
    main()
