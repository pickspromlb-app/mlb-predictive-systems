create schema if not exists prohits;

create table if not exists prohits.systems (
  system_id text primary key,
  system_name text not null,
  market_group text not null,
  description text,
  version text not null default 'v1.0',
  active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists prohits.player_derived_stats (
  stat_date date not null,
  player_id integer not null,
  team_id integer references core.teams(team_id),
  stat_window text not null,
  games_sample integer default 0,
  games_with_hit integer default 0,
  hit_rate numeric,
  avg_hits numeric,
  avg_plate_appearances numeric,
  avg_at_bats numeric,
  avg numeric,
  obp numeric,
  slg numeric,
  ops numeric,
  iso numeric,
  babip numeric,
  strikeout_rate numeric,
  bb_rate numeric,
  contact_proxy numeric,
  calculation_version text default 'prohits_player_derived_v1',
  metric_status text default 'OK_INTERNAL',
  calculated_at timestamptz default now(),
  primary key (stat_date, player_id, stat_window)
);

create table if not exists prohits.lineup_validation (
  game_pk bigint references core.games(game_pk) on delete cascade,
  team_id integer references core.teams(team_id),
  player_id integer,
  player_name text,
  lineup_spot integer,
  position text,
  confirmed_status text default 'UNCONFIRMED',
  source text,
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (game_pk, player_id)
);

create table if not exists prohits.hit_candidates (
  id bigserial primary key,
  evaluation_date date not null,
  game_pk bigint references core.games(game_pk),
  player_id integer not null,
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  system_id text references prohits.systems(system_id),
  market_type text default 'OVER_0_5_HITS',
  hit_score numeric,
  filters_passed jsonb default '[]'::jsonb,
  filters_failed jsonb default '[]'::jsonb,
  activation_status text default 'LINEUP_PENDING',
  actual_1plus_hit boolean,
  success boolean,
  data_quality_status text default 'PENDING_LINEUP',
  calculation_version text default 'prohits_v1',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

