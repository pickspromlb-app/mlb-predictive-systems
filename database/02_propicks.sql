create schema if not exists propicks;

create table if not exists propicks.systems (
  system_id text primary key,
  system_name text not null,
  market_group text not null,
  description text,
  version text not null default 'v1.0',
  active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists propicks.daily_team_profile (
  profile_date date not null,
  team_id integer not null references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  game_pk bigint references core.games(game_pk),
  home_away text,
  stat_window text not null,
  games_sample integer not null default 0,
  runs_scored_avg numeric,
  runs_allowed_avg numeric,
  run_diff_avg numeric,
  hit_avg numeric,
  win_rate numeric,
  scored_3plus_rate numeric,
  scored_5plus_rate numeric,
  ab integer default 0,
  pa integer default 0,
  h integer default 0,
  doubles integer default 0,
  triples integer default 0,
  hr integer default 0,
  bb integer default 0,
  ibb integer default 0,
  hbp integer default 0,
  sf integer default 0,
  so integer default 0,
  tb integer default 0,
  avg numeric,
  obp numeric,
  slg numeric,
  ops numeric,
  iso numeric,
  babip numeric,
  bb_rate numeric,
  k_rate numeric,
  bb_k_ratio numeric,
  woba_internal numeric,
  wraa_internal numeric,
  wrc_internal numeric,
  wrc_plus_internal numeric,
  calculation_version text default 'propicks_team_profile_v1',
  metric_status text default 'OK_INTERNAL',
  calculated_at timestamptz default now(),
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (profile_date, team_id, stat_window)
);
create index if not exists idx_propicks_profile_date on propicks.daily_team_profile(profile_date);

create table if not exists propicks.pitcher_derived_stats (
  stat_date date not null,
  pitcher_id integer not null,
  team_id integer references core.teams(team_id),
  stat_window text not null,
  games_sample integer not null default 0,
  ip_outs integer default 0,
  era numeric,
  whip numeric,
  fip_internal numeric,
  k_rate numeric,
  bb_rate numeric,
  k_bb_rate numeric,
  k_per_9 numeric,
  bb_per_9 numeric,
  hr_per_9 numeric,
  sample_size_ip numeric,
  calculation_version text default 'pitcher_derived_v1',
  metric_status text default 'OK_INTERNAL',
  calculated_at timestamptz default now(),
  primary key (stat_date, pitcher_id, stat_window)
);

create table if not exists propicks.filter_definitions (
  filter_id text primary key,
  system_id text references propicks.systems(system_id),
  filter_name text not null,
  description text,
  metric_a text,
  operator_a text,
  value_a numeric,
  metric_b text,
  operator_b text,
  value_b numeric,
  stat_window text default 'L5',
  weight numeric default 1.0,
  required boolean default false,
  status text default 'EXPERIMENTAL',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists propicks.market_results (
  id bigserial primary key,
  evaluation_date date not null,
  game_pk bigint references core.games(game_pk),
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  system_id text references propicks.systems(system_id),
  market_type text not null,
  target_metric text not null,
  projected_label text,
  score numeric,
  filters_passed jsonb default '[]'::jsonb,
  filters_failed jsonb default '[]'::jsonb,
  activation_status text default 'PRELIMINARY',
  actual_result boolean,
  success boolean,
  data_quality_status text default 'OK_INTERNAL',
  calculation_version text default 'propicks_v1',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_propicks_market_date on propicks.market_results(evaluation_date);

create table if not exists propicks.backtest_results (
  id bigserial primary key,
  system_id text references propicks.systems(system_id),
  version text not null,
  target_metric text not null,
  sample_size integer default 0,
  wins integer default 0,
  losses integer default 0,
  pushes integer default 0,
  success_rate numeric,
  last_updated timestamptz default now(),
  unique(system_id, version, target_metric)
);

