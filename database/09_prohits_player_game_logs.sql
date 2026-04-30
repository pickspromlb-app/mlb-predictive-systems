-- 09_prohits_player_game_logs.sql
-- Raw player game logs for ProHitsMLB.
-- Independent from ProPicksMLB. Do not use propicks.* here.

create schema if not exists prohits;

create table if not exists prohits.player_game_logs (
  game_pk bigint not null,
  game_date date not null,

  player_id integer not null,
  player_name text,

  team_id integer,
  opponent_team_id integer,
  home_away text,

  lineup_spot integer,
  position text,
  bat_side text,
  throw_side text,

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

  hit_1plus boolean,

  data_quality_status text default 'OK',
  source text default 'MLB_STATS_API_BOXSCORE',
  source_timestamp timestamptz,
  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  primary key (game_pk, player_id)
);

create index if not exists idx_prohits_player_game_logs_date
on prohits.player_game_logs(game_date);

create index if not exists idx_prohits_player_game_logs_player_date
on prohits.player_game_logs(player_id, game_date);

create index if not exists idx_prohits_player_game_logs_team_date
on prohits.player_game_logs(team_id, game_date);

create index if not exists idx_prohits_player_game_logs_hit
on prohits.player_game_logs(hit_1plus);
