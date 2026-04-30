import re
from shared.db import fetch_all, execute_many

import sys
MARKET_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-04-30"
MAX_DIFF_SECONDS = 300

def norm_team(name):
    if not name:
        return ""
    s = name.lower().strip()
    s = s.replace("&", "and")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()

    aliases = {
        "az": "arizona diamondbacks",
        "athletics": "athletics",
        "oakland athletics": "athletics",
        "a s": "athletics",
    }

    return aliases.get(s, s)

market_events = fetch_all("""
    select distinct
        event_id,
        market_date,
        commence_time,
        away_team,
        home_team
    from prohits.market_batter_hits_availability
    where market_date = %s
    order by commence_time, away_team, home_team;
""", [MARKET_DATE])

core_games = fetch_all("""
    select
        g.game_pk,
        g.game_date,
        g.game_datetime,
        g.away_team_id,
        away.team_name as away_team_name,
        g.home_team_id,
        home.team_name as home_team_name
    from core.games g
    join core.teams away on away.team_id = g.away_team_id
    join core.teams home on home.team_id = g.home_team_id
    where g.game_date = %s
    order by g.game_datetime, g.game_pk;
""", [MARKET_DATE])

rows = []
used_game_pks = set()

print("=" * 100)
print("BUILDING SAFE MARKET EVENT ↔ CORE GAME MAP")
print("=" * 100)

for e in market_events:
    e_away = norm_team(e["away_team"])
    e_home = norm_team(e["home_team"])

    matches = []

    for g in core_games:
        if g["game_pk"] in used_game_pks:
            continue

        g_away = norm_team(g["away_team_name"])
        g_home = norm_team(g["home_team_name"])

        teams_match = (e_away == g_away and e_home == g_home)

        if not teams_match:
            continue

        diff = abs((e["commence_time"] - g["game_datetime"]).total_seconds())

        if diff <= MAX_DIFF_SECONDS:
            matches.append((diff, g))

    if not matches:
        print(
            f"NO MATCH | {e['away_team']} @ {e['home_team']} | "
            f"event={e['event_id']} | commence={e['commence_time']}"
        )
        continue

    matches.sort(key=lambda x: x[0])
    best_diff, best = matches[0]

    used_game_pks.add(best["game_pk"])

    rows.append({
        "market_date": e["market_date"],
        "event_id": e["event_id"],
        "game_pk": best["game_pk"],
        "away_team": e["away_team"],
        "home_team": e["home_team"],
        "commence_time": e["commence_time"],
        "game_datetime": best["game_datetime"],
        "match_method": "team_name_plus_time_window_5min",
    })

    print(
        f"MATCH | game_pk={best['game_pk']} | "
        f"{e['away_team']} @ {e['home_team']} | "
        f"core={best['away_team_name']} @ {best['home_team_name']} | "
        f"diff_seconds={best_diff:.0f}"
    )

execute_many("""
    insert into prohits.market_event_game_map
    (
        market_date,
        event_id,
        game_pk,
        away_team,
        home_team,
        commence_time,
        game_datetime,
        match_method,
        updated_at
    )
    values
    (
        %(market_date)s,
        %(event_id)s,
        %(game_pk)s,
        %(away_team)s,
        %(home_team)s,
        %(commence_time)s,
        %(game_datetime)s,
        %(match_method)s,
        now()
    )
    on conflict (market_date, event_id, game_pk)
    do update set
        away_team = excluded.away_team,
        home_team = excluded.home_team,
        commence_time = excluded.commence_time,
        game_datetime = excluded.game_datetime,
        match_method = excluded.match_method,
        updated_at = now()
""", rows)

print("=" * 100)
print(f"mapped_rows={len(rows)}")
print(f"market_events={len(market_events)}")
print(f"core_games={len(core_games)}")


