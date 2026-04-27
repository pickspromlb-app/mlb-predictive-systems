create schema if not exists core;

create table if not exists core.teams (
  team_id integer primary key,
  team_name text not null,
  abbreviation text,
  league_name text,
  division_name text,
  active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists core.venues (
  venue_id integer primary key,
  venue_name text not null,
  city text,
  state text,
  roof_type text,
  altitude_ft integer,
  park_factor_runs numeric,
  park_factor_hr numeric,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists core.players (
  player_id integer primary key,
  full_name text not null,
  current_team_id integer references core.teams(team_id),
  bat_side text,
  throw_side text,
  primary_position text,
  active boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists core.games (
  game_pk bigint primary key,
  season integer not null,
  game_date date not null,
  game_datetime timestamptz,
  status text,
  detailed_state text,
  away_team_id integer references core.teams(team_id),
  home_team_id integer references core.teams(team_id),
  away_score integer,
  home_score integer,
  total_runs integer generated always as (coalesce(away_score,0) + coalesce(home_score,0)) stored,
  venue_id integer references core.venues(venue_id),
  away_probable_pitcher_id integer,
  home_probable_pitcher_id integer,
  data_source text default 'MLB_STATS_API',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
create index if not exists idx_core_games_date on core.games(game_date);

create table if not exists core.game_linescore (
  game_pk bigint primary key references core.games(game_pk) on delete cascade,
  away_runs integer,
  home_runs integer,
  away_hits integer,
  home_hits integer,
  away_errors integer,
  home_errors integer,
  away_f5_runs integer,
  home_f5_runs integer,
  total_f5_runs integer generated always as (coalesce(away_f5_runs,0) + coalesce(home_f5_runs,0)) stored,
  innings jsonb not null default '[]'::jsonb,
  data_quality_status text default 'OK',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists core.team_boxscore_batting (
  game_pk bigint references core.games(game_pk) on delete cascade,
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  game_date date not null,
  home_away text check (home_away in ('home','away')),
  ab integer default 0,
  r integer default 0,
  h integer default 0,
  doubles integer default 0,
  triples integer default 0,
  hr integer default 0,
  rbi integer default 0,
  bb integer default 0,
  ibb integer default 0,
  hbp integer default 0,
  sf integer default 0,
  so integer default 0,
  sb integer default 0,
  cs integer default 0,
  lob integer default 0,
  tb integer default 0,
  pa integer default 0,
  data_quality_status text default 'OK',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (game_pk, team_id)
);
create index if not exists idx_tbb_team_date on core.team_boxscore_batting(team_id, game_date);

create table if not exists core.team_boxscore_pitching (
  game_pk bigint references core.games(game_pk) on delete cascade,
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  game_date date not null,
  home_away text check (home_away in ('home','away')),
  ip_outs integer default 0,
  h integer default 0,
  r integer default 0,
  er integer default 0,
  bb integer default 0,
  ibb integer default 0,
  so integer default 0,
  hr integer default 0,
  hbp integer default 0,
  bf integer default 0,
  pitches integer default 0,
  strikes integer default 0,
  data_quality_status text default 'OK',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (game_pk, team_id)
);
create index if not exists idx_tbp_team_date on core.team_boxscore_pitching(team_id, game_date);

create table if not exists core.player_boxscore_batting (
  game_pk bigint references core.games(game_pk) on delete cascade,
  player_id integer,
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  game_date date not null,
  lineup_spot integer,
  position text,
  ab integer default 0,
  r integer default 0,
  h integer default 0,
  doubles integer default 0,
  triples integer default 0,
  hr integer default 0,
  rbi integer default 0,
  bb integer default 0,
  ibb integer default 0,
  hbp integer default 0,
  sf integer default 0,
  so integer default 0,
  tb integer default 0,
  pa integer default 0,
  data_quality_status text default 'OK',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (game_pk, player_id)
);
create index if not exists idx_pbb_player_date on core.player_boxscore_batting(player_id, game_date);

create table if not exists core.player_boxscore_pitching (
  game_pk bigint references core.games(game_pk) on delete cascade,
  player_id integer,
  team_id integer references core.teams(team_id),
  opponent_team_id integer references core.teams(team_id),
  game_date date not null,
  started boolean default false,
  ip_outs integer default 0,
  h integer default 0,
  r integer default 0,
  er integer default 0,
  bb integer default 0,
  ibb integer default 0,
  so integer default 0,
  hr integer default 0,
  hbp integer default 0,
  bf integer default 0,
  pitches integer default 0,
  strikes integer default 0,
  data_quality_status text default 'OK',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (game_pk, player_id)
);

create table if not exists core.weather (
  game_pk bigint primary key references core.games(game_pk) on delete cascade,
  game_date date,
  venue_id integer references core.venues(venue_id),
  temperature_f numeric,
  humidity_pct numeric,
  wind_speed_mph numeric,
  wind_direction text,
  roof_status text,
  weather_risk text,
  source text,
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists core.metric_constants (
  season integer not null,
  metric_name text not null,
  constant_name text not null,
  constant_value numeric not null,
  source text not null default 'INTERNAL',
  effective_date date,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),
  primary key (season, metric_name, constant_name, source)
);
