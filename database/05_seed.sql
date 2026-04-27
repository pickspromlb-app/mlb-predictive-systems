insert into propicks.systems (system_id, system_name, market_group, description, version, active)
values ('PROPICKS_MLB', 'ProPicksMLB', 'Game Markets', 'Sistema para moneyline, run line, totales, team runs y F5.', 'v1.0', true)
on conflict (system_id) do update set updated_at = now();

insert into prohits.systems (system_id, system_name, market_group, description, version, active)
values ('PROHITS_MLB', 'ProHitsMLB', 'Player Hits', 'Sistema especializado Ãºnicamente en Over 0.5 hits de jugadores.', 'v1.0', true)
on conflict (system_id) do update set updated_at = now();

insert into propicks.filter_definitions (filter_id, system_id, filter_name, description, metric_a, operator_a, value_a, metric_b, operator_b, value_b, stat_window, weight, required, status)
values
('PEF_001', 'PROPICKS_MLB', 'wOBA diff + wRC+ diff', 'Ventaja ofensiva por wOBA y wRC+.', 'woba_diff', '>=', 0.040, 'wrc_plus_diff', '>=', 30, 'L5', 1.0, false, 'EXPERIMENTAL'),
('PEF_002', 'PROPICKS_MLB', 'OPS diff + wRC+ diff', 'Ventaja ofensiva por OPS y wRC+.', 'ops_diff', '>=', 0.150, 'wrc_plus_diff', '>=', 30, 'L5', 1.0, false, 'EXPERIMENTAL'),
('PEF_003', 'PROPICKS_MLB', 'Premium offensive mismatch', 'Diferencial premium wRC+, wRAA y wOBA.', 'wrc_plus_diff', '>=', 50, 'woba_diff', '>=', 0.070, 'L5', 1.5, false, 'EXPERIMENTAL_STRONG')
on conflict (filter_id) do update set updated_at = now();

