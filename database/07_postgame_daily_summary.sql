-- 07_postgame_daily_summary.sql
-- Stores daily postgame summary reports for dashboards and Telegram bots.

create table if not exists ops.postgame_daily_summary (
  id bigserial primary key,

  summary_date date not null,
  system_name text not null,
  system_version text default 'v1.0',

  total_records integer default 0,
  wins integer default 0,
  losses integer default 0,
  pushes integer default 0,
  success_rate numeric,

  by_target_metric jsonb default '[]'::jsonb,
  by_confidence_tier jsonb default '[]'::jsonb,
  top_wins jsonb default '[]'::jsonb,
  top_losses jsonb default '[]'::jsonb,

  summary_text text,

  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  unique(summary_date, system_name, system_version)
);

create index if not exists idx_postgame_daily_summary_date
on ops.postgame_daily_summary(summary_date);
