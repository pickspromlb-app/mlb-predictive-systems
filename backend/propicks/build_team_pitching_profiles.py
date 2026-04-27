import psycopg
from shared.settings import get_settings

SQL = """
insert into propicks.team_pitching_profile (
  profile_date,
  team_id,
  stat_window,
  games_sample,
  ip_outs,
  innings_pitched,
  runs_allowed_avg,
  earned_runs_allowed_avg,
  era,
  whip,
  fip_internal,
  k_rate,
  bb_rate,
  k_bb_rate,
  k_per_9,
  bb_per_9,
  hr_per_9,
  h_allowed,
  r_allowed,
  er_allowed,
  bb_allowed,
  ibb_allowed,
  so_recorded,
  hr_allowed,
  hbp_allowed,
  batters_faced,
  pitches,
  strikes,
  metric_status,
  calculated_at,
  updated_at
)
with profile_keys as (
  select distinct
    profile_date,
    team_id
  from propicks.daily_team_profile
),
windows(stat_window, n_games) as (
  values
    ('L1', 1),
    ('L3', 3),
    ('L5', 5),
    ('L7', 7),
    ('L10', 10)
),
rolled as (
  select
    pk.profile_date,
    pk.team_id,
    w.stat_window,
    count(p.*)::integer as games_sample,
    coalesce(sum(p.ip_outs), 0)::integer as ip_outs,
    coalesce(sum(p.h), 0)::integer as h_allowed,
    coalesce(sum(p.r), 0)::integer as r_allowed,
    coalesce(sum(p.er), 0)::integer as er_allowed,
    coalesce(sum(p.bb), 0)::integer as bb_allowed,
    coalesce(sum(p.ibb), 0)::integer as ibb_allowed,
    coalesce(sum(p.so), 0)::integer as so_recorded,
    coalesce(sum(p.hr), 0)::integer as hr_allowed,
    coalesce(sum(p.hbp), 0)::integer as hbp_allowed,
    coalesce(sum(p.bf), 0)::integer as batters_faced,
    coalesce(sum(p.pitches), 0)::integer as pitches,
    coalesce(sum(p.strikes), 0)::integer as strikes
  from profile_keys pk
  cross join windows w
  left join lateral (
    select *
    from core.team_boxscore_pitching p
    where p.team_id = pk.team_id
      and p.game_date <= pk.profile_date
    order by p.game_date desc, p.game_pk desc
    limit w.n_games
  ) p on true
  group by
    pk.profile_date,
    pk.team_id,
    w.stat_window
)
select
  profile_date,
  team_id,
  stat_window,
  games_sample,
  ip_outs,
  round(ip_outs::numeric / 3, 4) as innings_pitched,

  round(r_allowed::numeric / nullif(games_sample, 0), 4) as runs_allowed_avg,
  round(er_allowed::numeric / nullif(games_sample, 0), 4) as earned_runs_allowed_avg,

  round((er_allowed::numeric * 27) / nullif(ip_outs, 0), 4) as era,
  round(((bb_allowed + h_allowed)::numeric * 3) / nullif(ip_outs, 0), 4) as whip,

  round(
    (
      (
        (13 * hr_allowed)
        + (3 * (bb_allowed + hbp_allowed))
        - (2 * so_recorded)
      )::numeric * 3 / nullif(ip_outs, 0)
    ) + 3.10,
    4
  ) as fip_internal,

  round(so_recorded::numeric / nullif(batters_faced, 0), 4) as k_rate,
  round(bb_allowed::numeric / nullif(batters_faced, 0), 4) as bb_rate,
  round((so_recorded - bb_allowed)::numeric / nullif(batters_faced, 0), 4) as k_bb_rate,

  round((so_recorded::numeric * 27) / nullif(ip_outs, 0), 4) as k_per_9,
  round((bb_allowed::numeric * 27) / nullif(ip_outs, 0), 4) as bb_per_9,
  round((hr_allowed::numeric * 27) / nullif(ip_outs, 0), 4) as hr_per_9,

  h_allowed,
  r_allowed,
  er_allowed,
  bb_allowed,
  ibb_allowed,
  so_recorded,
  hr_allowed,
  hbp_allowed,
  batters_faced,
  pitches,
  strikes,

  case
    when ip_outs > 0 then 'OK_INTERNAL'
    else 'NO_IP'
  end as metric_status,
  now() as calculated_at,
  now() as updated_at
from rolled
where games_sample > 0
on conflict (profile_date, team_id, stat_window) do update set
  games_sample = excluded.games_sample,
  ip_outs = excluded.ip_outs,
  innings_pitched = excluded.innings_pitched,
  runs_allowed_avg = excluded.runs_allowed_avg,
  earned_runs_allowed_avg = excluded.earned_runs_allowed_avg,
  era = excluded.era,
  whip = excluded.whip,
  fip_internal = excluded.fip_internal,
  k_rate = excluded.k_rate,
  bb_rate = excluded.bb_rate,
  k_bb_rate = excluded.k_bb_rate,
  k_per_9 = excluded.k_per_9,
  bb_per_9 = excluded.bb_per_9,
  hr_per_9 = excluded.hr_per_9,
  h_allowed = excluded.h_allowed,
  r_allowed = excluded.r_allowed,
  er_allowed = excluded.er_allowed,
  bb_allowed = excluded.bb_allowed,
  ibb_allowed = excluded.ibb_allowed,
  so_recorded = excluded.so_recorded,
  hr_allowed = excluded.hr_allowed,
  hbp_allowed = excluded.hbp_allowed,
  batters_faced = excluded.batters_faced,
  pitches = excluded.pitches,
  strikes = excluded.strikes,
  metric_status = excluded.metric_status,
  calculated_at = now(),
  updated_at = now();
"""

def main():
    settings = get_settings()
    with psycopg.connect(settings.database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
        conn.commit()

    print({"team_pitching_profiles": "completed"})

if __name__ == "__main__":
    main()
