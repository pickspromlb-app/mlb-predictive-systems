create schema if not exists ops;

create table if not exists ops.job_runs (
  run_id text primary key,
  job_name text not null,
  run_date date not null,
  started_at timestamptz default now(),
  finished_at timestamptz,
  status text default 'RUNNING',
  metadata jsonb default '{}'::jsonb,
  errors jsonb default '[]'::jsonb,
  notes text
);

create table if not exists ops.daily_update_log (
  run_id text primary key references ops.job_runs(run_id),
  run_date date not null,
  games_found integer default 0,
  games_processed integer default 0,
  teams_processed integer default 0,
  players_processed integer default 0,
  propicks_profiles_created integer default 0,
  prohits_profiles_created integer default 0,
  systems_processed integer default 0,
  status text default 'RUNNING',
  errors jsonb default '[]'::jsonb,
  started_at timestamptz default now(),
  finished_at timestamptz
);

create table if not exists ops.data_quality_errors (
  id bigserial primary key,
  run_id text,
  source text,
  entity_type text,
  entity_id text,
  error_code text,
  error_message text,
  payload jsonb,
  created_at timestamptz default now()
);

