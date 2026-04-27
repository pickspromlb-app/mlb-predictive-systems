import psycopg
from shared.settings import get_settings

SQL = """
with ranked_market_results as (
  select
    mr.*,
    row_number() over (
      partition by
        mr.evaluation_date,
        mr.game_pk,
        mr.team_id,
        mr.market_type,
        mr.target_metric,
        'v1.0'
      order by
        mr.score desc nulls last,
        mr.id desc
    ) as rn
  from propicks.market_results mr
  where mr.game_pk is not null
    and mr.team_id is not null
    and mr.system_id = 'PROPICKS_MLB'
),
deduped as (
  select *
  from ranked_market_results
  where rn = 1
)

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
  mr.evaluation_date as analysis_date,
  now() as analysis_timestamp,
  mr.game_pk,
  mr.team_id,
  mr.opponent_team_id,
  mr.system_id,
  'v1.0' as system_version,
  mr.market_type,
  mr.target_metric,
  mr.score,

  case
    when mr.score >= 85 then 'A'
    when mr.score >= 75 then 'B'
    when mr.score >= 65 then 'C'
    else 'WATCH'
  end as confidence_tier,

  coalesce(mr.activation_status, 'PRE_GAME') as status,

  coalesce(mr.filters_passed, '[]'::jsonb) as filters_passed,
  coalesce(mr.filters_failed, '[]'::jsonb) as filters_failed,

  jsonb_build_object(
    'team_offense_L5', to_jsonb(tp),
    'team_pitching_L5', to_jsonb(tpp),
    'opponent_offense_L5', to_jsonb(op),
    'opponent_pitching_L5', to_jsonb(opp),
    'source_market_result_id', mr.id
  ) as metrics_snapshot,

  case
    when mr.score < 65 then jsonb_build_array('LOW_SCORE')
    else '[]'::jsonb
  end as risk_flags,

  concat(
    'ProPicksMLB snapshot | ',
    mr.market_type,
    ' | ',
    mr.target_metric,
    ' | score=',
    coalesce(mr.score::text, 'NA')
  ) as analysis_text,

  'PENDING' as grade_status,
  now() as created_at,
  now() as updated_at

from deduped mr

left join propicks.daily_team_profile tp
  on tp.profile_date = mr.evaluation_date
  and tp.team_id = mr.team_id
  and tp.stat_window = 'L5'

left join propicks.daily_team_profile op
  on op.profile_date = mr.evaluation_date
  and op.team_id = mr.opponent_team_id
  and op.stat_window = 'L5'

left join propicks.team_pitching_profile tpp
  on tpp.profile_date = mr.evaluation_date
  and tpp.team_id = mr.team_id
  and tpp.stat_window = 'L5'

left join propicks.team_pitching_profile opp
  on opp.profile_date = mr.evaluation_date
  and opp.team_id = mr.opponent_team_id
  and opp.stat_window = 'L5'

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
  updated_at = now();
"""

def main():
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()

    print({"propicks_analysis_snapshots": "completed"})

if __name__ == "__main__":
    main()
