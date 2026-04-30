create table if not exists prohits.market_batter_hits_availability (
    id bigserial primary key,

    market_date date not null,
    event_id text not null,
    commence_time timestamptz,

    away_team text,
    home_team text,

    book_key text not null,
    book_title text,

    player_name text not null,

    market_status text not null,
    has_o05 boolean default false,
    o05_over_price integer,

    has_o15 boolean default false,
    o15_over_price integer,

    all_over_points text,

    source text default 'the_odds_api',
    created_at timestamptz default now(),
    updated_at timestamptz default now(),

    constraint uq_prohits_market_batter_hits
        unique (market_date, event_id, book_key, player_name)
);

create index if not exists idx_prohits_market_hits_date
on prohits.market_batter_hits_availability(market_date);

create index if not exists idx_prohits_market_hits_player
on prohits.market_batter_hits_availability(player_name);

create index if not exists idx_prohits_market_hits_status
on prohits.market_batter_hits_availability(market_status);

create index if not exists idx_prohits_market_hits_book
on prohits.market_batter_hits_availability(book_key);


create table if not exists prohits.market_event_game_map (
    id bigserial primary key,

    market_date date not null,
    event_id text not null,
    game_pk bigint not null,

    away_team text,
    home_team text,
    commence_time timestamptz,
    game_datetime timestamptz,

    match_method text default 'team_name_plus_time_window',
    created_at timestamptz default now(),
    updated_at timestamptz default now(),

    constraint uq_prohits_market_event_game_map
        unique (market_date, event_id, game_pk)
);

create index if not exists idx_prohits_market_event_game_map_date
on prohits.market_event_game_map(market_date);

create index if not exists idx_prohits_market_event_game_map_event
on prohits.market_event_game_map(event_id);

create index if not exists idx_prohits_market_event_game_map_game
on prohits.market_event_game_map(game_pk);


alter table prohits.hit_candidates
add column if not exists player_name text;

alter table prohits.hit_candidates
add column if not exists book_key text;

alter table prohits.hit_candidates
add column if not exists book_title text;

alter table prohits.hit_candidates
add column if not exists market_status text;

alter table prohits.hit_candidates
add column if not exists has_o05 boolean;

alter table prohits.hit_candidates
add column if not exists o05_over_price integer;

alter table prohits.hit_candidates
add column if not exists has_o15 boolean;

alter table prohits.hit_candidates
add column if not exists o15_over_price integer;

alter table prohits.hit_candidates
add column if not exists market_filter_status text;

create index if not exists idx_prohits_hit_candidates_eval_date
on prohits.hit_candidates(evaluation_date);

create index if not exists idx_prohits_hit_candidates_player_name
on prohits.hit_candidates(player_name);

create index if not exists idx_prohits_hit_candidates_market_status
on prohits.hit_candidates(market_status);

create index if not exists idx_prohits_hit_candidates_book_key
on prohits.hit_candidates(book_key);

create unique index if not exists uq_prohits_hit_candidates_daily_book_player_system
on prohits.hit_candidates (
    evaluation_date,
    book_key,
    system_id,
    market_type,
    player_id,
    game_pk
);


create unique index if not exists uq_prohits_lineup_validation_game_team_player
on prohits.lineup_validation (
    game_pk,
    team_id,
    player_id
);


insert into prohits.systems
(
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
    'PROHITS_CANDIDATE_A_SEP_L1_GUARD_BP_K250',
    'ProHits Candidate A + Sep L1 Guard + Bullpen K250',
    'Player Hits',
    'Candidato operativo para Over 0.5 Hits: hitter volume/contact + opposing starter L5 + September L1 guard + bullpen K-rate <= .250 + market availability filter.',
    'v0.1',
    true,
    now()
)
on conflict (system_id)
do update set
    system_name = excluded.system_name,
    market_group = excluded.market_group,
    description = excluded.description,
    version = excluded.version,
    active = excluded.active,
    updated_at = now();


create or replace view prohits.daily_hit_candidates_view as
select
    hc.evaluation_date,
    hc.book_key,
    hc.system_id,
    hc.market_type,

    hc.player_id,
    hc.player_name,
    hc.team_id,
    team.team_name as team_name,
    hc.opponent_team_id,
    opp.team_name as opponent_team_name,

    hc.game_pk,
    g.game_datetime,

    hc.activation_status,
    hc.market_status,
    hc.market_filter_status,

    hc.has_o05,
    hc.o05_over_price,
    hc.has_o15,
    hc.o15_over_price,

    hc.hit_score,
    hc.filters_passed,
    hc.filters_failed,
    hc.actual_1plus_hit,
    hc.success,
    hc.data_quality_status,
    hc.calculation_version,
    hc.created_at,
    hc.updated_at
from prohits.hit_candidates hc
left join core.games g
    on g.game_pk = hc.game_pk
left join core.teams team
    on team.team_id = hc.team_id
left join core.teams opp
    on opp.team_id = hc.opponent_team_id;
