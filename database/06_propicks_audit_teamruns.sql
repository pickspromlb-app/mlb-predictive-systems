-- 06_propicks_audit_teamruns.sql
-- Adds ProPicks pitching profiles, analysis snapshots, postgame audit tables,
-- and Team Runs Pressure Filter v1.

create table if not exists propicks.team_pitching_profile (
  profile_date date not null,
  team_id integer not null references core.teams(team_id),
  stat_window text not null,

  games_sample integer not null default 0,
  ip_outs integer default 0,
  innings_pitched numeric,

  runs_allowed_avg numeric,
  earned_runs_allowed_avg numeric,

  era numeric,
  whip numeric,
  fip_internal numeric,

  k_rate numeric,
  bb_rate numeric,
  k_bb_rate numeric,

  k_per_9 numeric,
  bb_per_9 numeric,
  hr_per_9 numeric,

  h_allowed integer default 0,
  r_allowed integer default 0,
  er_allowed integer default 0,
  bb_allowed integer default 0,
  ibb_allowed integer default 0,
  so_recorded integer default 0,
  hr_allowed integer default 0,
  hbp_allowed integer default 0,
  batters_faced integer default 0,
  pitches integer default 0,
  strikes integer default 0,

  calculation_version text default 'team_pitching_profile_v1',
  metric_status text default 'OK_INTERNAL',
  calculated_at timestamptz default now(),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  primary key (profile_date, team_id, stat_window)
);

create index if not exists idx_team_pitching_profile_date
on propicks.team_pitching_profile(profile_date);

create index if not exists idx_team_pitching_profile_team
on propicks.team_pitching_profile(team_id);


create table if not exists propicks.analysis_snapshots (
  id bigserial primary key,

  analysis_date date not null,
  analysis_timestamp timestamptz default now(),

  game_pk bigint references core.games(game_pk),
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),

  system_id text references propicks.systems(system_id),
  system_version text default 'v1.0',

  market_type text not null,
  target_metric text not null,

  score numeric,
  confidence_tier text,
  status text default 'PRE_GAME',

  filters_passed jsonb default '[]'::jsonb,
  filters_failed jsonb default '[]'::jsonb,
  metrics_snapshot jsonb default '{}'::jsonb,
  risk_flags jsonb default '[]'::jsonb,

  analysis_text text,

  actual_result boolean,
  success boolean,
  grade_status text default 'PENDING',
  graded_at timestamptz,

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_propicks_snapshots_date
on propicks.analysis_snapshots(analysis_date);

create index if not exists idx_propicks_snapshots_game
on propicks.analysis_snapshots(game_pk);

create index if not exists idx_propicks_snapshots_market
on propicks.analysis_snapshots(market_type, target_metric);

create unique index if not exists uq_propicks_analysis_snapshot
on propicks.analysis_snapshots (
  analysis_date,
  game_pk,
  team_id,
  market_type,
  target_metric,
  system_version
);


create table if not exists prohits.analysis_snapshots (
  id bigserial primary key,

  analysis_date date not null,
  analysis_timestamp timestamptz default now(),

  game_pk bigint references core.games(game_pk),

  player_id integer not null,
  player_name text,
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),

  lineup_spot integer,
  lineup_status text default 'UNCONFIRMED',

  pitcher_id integer,
  pitcher_name text,

  system_id text references prohits.systems(system_id),
  system_version text default 'v1.0',

  market_type text default 'OVER_0_5_HITS',
  target_metric text default 'PLAYER_1PLUS_HIT',

  hit_score numeric,
  confidence_tier text,
  status text default 'PRE_GAME',

  filters_passed jsonb default '[]'::jsonb,
  filters_failed jsonb default '[]'::jsonb,
  metrics_snapshot jsonb default '{}'::jsonb,
  risk_flags jsonb default '[]'::jsonb,

  analysis_text text,

  actual_1plus_hit boolean,
  final_hits integer,
  final_ab integer,
  final_pa integer,

  success boolean,
  grade_status text default 'PENDING',
  graded_at timestamptz,

  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create index if not exists idx_prohits_snapshots_date
on prohits.analysis_snapshots(analysis_date);

create index if not exists idx_prohits_snapshots_game
on prohits.analysis_snapshots(game_pk);

create index if not exists idx_prohits_snapshots_player
on prohits.analysis_snapshots(player_id);


create table if not exists ops.postgame_grade_runs (
  run_id bigserial primary key,

  grade_date date not null,
  started_at timestamptz default now(),
  finished_at timestamptz,

  system_name text not null,
  system_version text default 'v1.0',

  games_checked integer default 0,
  records_graded integer default 0,

  wins integer default 0,
  losses integer default 0,
  pushes integer default 0,

  success_rate numeric,

  status text default 'STARTED',
  errors jsonb default '[]'::jsonb,
  notes text,

  created_at timestamptz default now()
);

create index if not exists idx_postgame_grade_runs_date
on ops.postgame_grade_runs(grade_date);


create table if not exists ops.system_performance_summary (
  id bigserial primary key,

  system_name text not null,
  system_version text default 'v1.0',
  target_metric text not null,

  sample_size integer default 0,
  wins integer default 0,
  losses integer default 0,
  pushes integer default 0,

  success_rate numeric,

  best_filters jsonb default '[]'::jsonb,
  worst_filters jsonb default '[]'::jsonb,
  common_failure_reasons jsonb default '[]'::jsonb,

  last_updated timestamptz default now(),

  unique(system_name, system_version, target_metric)
);


insert into propicks.filter_definitions (
  filter_id,
  system_id,
  filter_name,
  description,
  metric_a,
  operator_a,
  value_a,
  metric_b,
  operator_b,
  value_b,
  stat_window,
  weight,
  required,
  status
)
values
(
  'PROPICKS_TR3_PRESSURE_V1',
  'PROPICKS_MLB',
  'Team Runs 3+ Pressure Filter v1',
  'Activa Team Runs 3+ cuando OFFENSIVE_EDGE = A, el rival tiene WHIP L5 >= 1.35 y permite 5.0+ carreras promedio L5. Backtest inicial: 37/40 = 92.5%.',
  'opponent_whip_l5',
  '>=',
  1.35,
  'opponent_runs_allowed_avg_l5',
  '>=',
  5.0,
  'L5',
  2.00,
  true,
  'EXPERIMENTAL_STRONG'
),
(
  'PROPICKS_TR5_PRESSURE_V1',
  'PROPICKS_MLB',
  'Team Runs 5+ Pressure Filter v1',
  'Activa Team Runs 5+ cuando OFFENSIVE_EDGE = A, el rival tiene WHIP L5 >= 1.35 y permite 5.0+ carreras promedio L5. Backtest inicial: 30/40 = 75.0%.',
  'opponent_whip_l5',
  '>=',
  1.35,
  'opponent_runs_allowed_avg_l5',
  '>=',
  5.0,
  'L5',
  2.25,
  true,
  'EXPERIMENTAL_STRONG'
)
on conflict (filter_id) do update set
  system_id = excluded.system_id,
  filter_name = excluded.filter_name,
  description = excluded.description,
  metric_a = excluded.metric_a,
  operator_a = excluded.operator_a,
  value_a = excluded.value_a,
  metric_b = excluded.metric_b,
  operator_b = excluded.operator_b,
  value_b = excluded.value_b,
  stat_window = excluded.stat_window,
  weight = excluded.weight,
  required = excluded.required,
  status = excluded.status,
  updated_at = now();
