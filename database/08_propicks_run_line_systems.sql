-- 08_propicks_run_line_systems.sql
-- Registers Run Line systems and creates signal table.

create table if not exists propicks.run_line_signals (
  analysis_date date,
  game_pk bigint,
  system_id text,
  version text default 'v1.0',

  run_line_tier text,
  target_line numeric default -1.5,

  team_id integer,
  team_abbr text,
  team_name text,
  opponent_team_id integer,
  opponent_abbr text,
  opponent_name text,
  home_away text,

  team_score integer,
  opponent_score integer,
  run_margin integer,
  covered_runline boolean,

  status text,
  detailed_state text,
  is_final boolean,

  team_rs_l3 numeric,
  team_ra_l3 numeric,
  rs_edge_l3 numeric,
  ra_edge_l3 numeric,
  run_diff_edge_l3 numeric,
  era_edge_l3 numeric,
  whip_edge_l3 numeric,

  team_rs_l5 numeric,
  team_ra_l5 numeric,
  rs_edge_l5 numeric,
  ra_edge_l5 numeric,
  run_diff_edge_l5 numeric,
  era_edge_l5 numeric,
  whip_edge_l5 numeric,

  created_at timestamptz default now(),
  updated_at timestamptz default now(),

  unique (analysis_date, game_pk, system_id, team_id)
);

create index if not exists idx_run_line_signals_date
on propicks.run_line_signals(analysis_date);

create index if not exists idx_run_line_signals_system
on propicks.run_line_signals(system_id);

create index if not exists idx_run_line_signals_game
on propicks.run_line_signals(game_pk);

insert into propicks.systems (
  system_id,
  system_name,
  market_group,
  description,
  version,
  active,
  updated_at
)
values
(
  'RUN_LINE_MOMENTUM_L3_V1',
  'Run Line Momentum L3 v1',
  'RUN_LINE',
  'Run Line -1.5 volume system based on L3 recent momentum. Detects teams with enough run production, controlled runs allowed, positive run differential edge and clear ERA/WHIP pitching edge.',
  'v1.0',
  true,
  now()
),
(
  'RUN_LINE_CONFLUENCE_L3_L5_V1',
  'Run Line Confluence L3/L5 v1',
  'RUN_LINE',
  'Selective Run Line -1.5 system based on L3 and L5 confluence. Signal activates only when production, recent defense, run differential and ERA/WHIP pitching edge appear simultaneously in L3 and L5.',
  'v1.0',
  true,
  now()
)
on conflict (system_id) do update set
  system_name = excluded.system_name,
  market_group = excluded.market_group,
  description = excluded.description,
  version = excluded.version,
  active = excluded.active,
  updated_at = now();

insert into propicks.backtest_results (
  system_id,
  version,
  target_metric,
  sample_size,
  wins,
  losses,
  pushes,
  success_rate,
  last_updated
)
values
(
  'RUN_LINE_MOMENTUM_L3_V1',
  'v1.0',
  'team_runline_minus_1_5_cover',
  81,
  56,
  25,
  0,
  69.14,
  now()
),
(
  'RUN_LINE_CONFLUENCE_L3_L5_V1',
  'v1.0',
  'team_runline_minus_1_5_cover',
  35,
  27,
  8,
  0,
  77.14,
  now()
);

-- Filter definitions for RUN_LINE_MOMENTUM_L3_V1
insert into propicks.filter_definitions (
  filter_id, system_id, filter_name, description,
  metric_a, operator_a, value_a, stat_window,
  weight, required, status, updated_at
)
values
('RUN_LINE_MOMENTUM_L3_V1_TEAM_RS_L3_MIN', 'RUN_LINE_MOMENTUM_L3_V1', 'TEAM_RS_L3_MIN', 'Team scores at least 4.0 runs per game in L3.', 'team_rs_l3', '>=', 4.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_MOMENTUM_L3_V1_TEAM_RA_L3_MAX', 'RUN_LINE_MOMENTUM_L3_V1', 'TEAM_RA_L3_MAX', 'Team allows no more than 5.0 runs per game in L3.', 'team_ra_l3', '<=', 5.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_MOMENTUM_L3_V1_RS_EDGE_L3_MIN', 'RUN_LINE_MOMENTUM_L3_V1', 'RS_EDGE_L3_MIN', 'Team run scoring average is equal or superior to opponent in L3.', 'rs_edge_l3', '>=', 0.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_MOMENTUM_L3_V1_RA_EDGE_L3_MIN', 'RUN_LINE_MOMENTUM_L3_V1', 'RA_EDGE_L3_MIN', 'Opponent allows equal or more runs than team in L3.', 'ra_edge_l3', '>=', 0.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_MOMENTUM_L3_V1_RUN_DIFF_EDGE_L3_MIN', 'RUN_LINE_MOMENTUM_L3_V1', 'RUN_DIFF_EDGE_L3_MIN', 'Minimum L3 run differential edge.', 'run_diff_edge_l3', '>=', 0.5, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_MOMENTUM_L3_V1_ERA_EDGE_L3_MIN', 'RUN_LINE_MOMENTUM_L3_V1', 'ERA_EDGE_L3_MIN', 'Minimum L3 ERA edge versus opponent.', 'era_edge_l3', '>=', 2.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_MOMENTUM_L3_V1_WHIP_EDGE_L3_MIN', 'RUN_LINE_MOMENTUM_L3_V1', 'WHIP_EDGE_L3_MIN', 'Minimum L3 WHIP edge versus opponent.', 'whip_edge_l3', '>=', 0.05, 'L3', 1.0, true, 'ACTIVE', now())

on conflict (filter_id) do update set
  system_id = excluded.system_id,
  filter_name = excluded.filter_name,
  description = excluded.description,
  metric_a = excluded.metric_a,
  operator_a = excluded.operator_a,
  value_a = excluded.value_a,
  stat_window = excluded.stat_window,
  weight = excluded.weight,
  required = excluded.required,
  status = excluded.status,
  updated_at = now();

-- Filter definitions for RUN_LINE_CONFLUENCE_L3_L5_V1
insert into propicks.filter_definitions (
  filter_id, system_id, filter_name, description,
  metric_a, operator_a, value_a, stat_window,
  weight, required, status, updated_at
)
values
('RUN_LINE_CONFLUENCE_L3_L5_V1_TEAM_RS_L3_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'TEAM_RS_L3_MIN', 'Team scores at least 4.0 runs per game in L3.', 'team_rs_l3', '>=', 4.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_TEAM_RA_L3_MAX', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'TEAM_RA_L3_MAX', 'Team allows no more than 5.0 runs per game in L3.', 'team_ra_l3', '<=', 5.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_RS_EDGE_L3_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'RS_EDGE_L3_MIN', 'Team run scoring average is equal or superior to opponent in L3.', 'rs_edge_l3', '>=', 0.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_RA_EDGE_L3_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'RA_EDGE_L3_MIN', 'Opponent allows equal or more runs than team in L3.', 'ra_edge_l3', '>=', 0.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_RUN_DIFF_EDGE_L3_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'RUN_DIFF_EDGE_L3_MIN', 'Minimum L3 run differential edge.', 'run_diff_edge_l3', '>=', 0.5, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_ERA_EDGE_L3_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'ERA_EDGE_L3_MIN', 'Minimum L3 ERA edge versus opponent.', 'era_edge_l3', '>=', 2.0, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_WHIP_EDGE_L3_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'WHIP_EDGE_L3_MIN', 'Minimum L3 WHIP edge versus opponent.', 'whip_edge_l3', '>=', 0.05, 'L3', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_TEAM_RS_L5_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'TEAM_RS_L5_MIN', 'Team scores at least 4.0 runs per game in L5.', 'team_rs_l5', '>=', 4.0, 'L5', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_TEAM_RA_L5_MAX', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'TEAM_RA_L5_MAX', 'Team allows no more than 5.0 runs per game in L5.', 'team_ra_l5', '<=', 5.0, 'L5', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_RS_EDGE_L5_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'RS_EDGE_L5_MIN', 'Team run scoring average is equal or superior to opponent in L5.', 'rs_edge_l5', '>=', 0.0, 'L5', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_RA_EDGE_L5_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'RA_EDGE_L5_MIN', 'Opponent allows equal or more runs than team in L5.', 'ra_edge_l5', '>=', 0.0, 'L5', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_RUN_DIFF_EDGE_L5_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'RUN_DIFF_EDGE_L5_MIN', 'Minimum L5 run differential edge.', 'run_diff_edge_l5', '>=', 0.5, 'L5', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_ERA_EDGE_L5_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'ERA_EDGE_L5_MIN', 'Minimum L5 ERA edge versus opponent.', 'era_edge_l5', '>=', 2.0, 'L5', 1.0, true, 'ACTIVE', now()),
('RUN_LINE_CONFLUENCE_L3_L5_V1_WHIP_EDGE_L5_MIN', 'RUN_LINE_CONFLUENCE_L3_L5_V1', 'WHIP_EDGE_L5_MIN', 'Minimum L5 WHIP edge versus opponent.', 'whip_edge_l5', '>=', 0.05, 'L5', 1.0, true, 'ACTIVE', now())

on conflict (filter_id) do update set
  system_id = excluded.system_id,
  filter_name = excluded.filter_name,
  description = excluded.description,
  metric_a = excluded.metric_a,
  operator_a = excluded.operator_a,
  value_a = excluded.value_a,
  stat_window = excluded.stat_window,
  weight = excluded.weight,
  required = excluded.required,
  status = excluded.status,
  updated_at = now();
