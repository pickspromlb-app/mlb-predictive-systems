import requests
from shared.db import fetch_all, execute_many

import sys
GAME_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-04-30"

def parse_lineup_spot(batting_order):
    if not batting_order:
        return None

    try:
        return int(str(batting_order)) // 100
    except Exception:
        return None

games = fetch_all("""
    select
        game_pk,
        game_date,
        game_datetime
    from core.games
    where game_date = %s
    order by game_datetime, game_pk;
""", [GAME_DATE])

rows = []

print("=" * 90)
print(f"LOADING MLB BOXSCORE LINEUPS FOR {GAME_DATE}")
print("=" * 90)

for g in games:
    game_pk = g["game_pk"]
    url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"

    print(f"Requesting game_pk={game_pk}...")

    res = requests.get(url, timeout=30)
    print("status:", res.status_code)

    if res.status_code != 200:
        print(res.text[:500])
        continue

    box = res.json()
    teams = box.get("teams", {})

    game_count = 0

    for side in ["away", "home"]:
        team = teams.get(side, {})
        team_info = team.get("team", {})
        team_id = team_info.get("id")
        players = team.get("players", {})

        for key, p in players.items():
            person = p.get("person", {})
            player_id = person.get("id")
            player_name = person.get("fullName")
            batting_order = p.get("battingOrder")
            position = p.get("position", {}).get("abbreviation")
            lineup_spot = parse_lineup_spot(batting_order)

            if not player_id or not lineup_spot:
                continue

            rows.append({
                "game_pk": game_pk,
                "team_id": team_id,
                "player_id": player_id,
                "player_name": player_name,
                "lineup_spot": lineup_spot,
                "position": position,
                "confirmed_status": "CONFIRMED_LINEUP",
                "source": "mlb_statsapi_boxscore",
            })

            game_count += 1

    print(f"lineup_rows_found={game_count}")

execute_many("""
    insert into prohits.lineup_validation
    (
        game_pk,
        team_id,
        player_id,
        player_name,
        lineup_spot,
        position,
        confirmed_status,
        source,
        source_timestamp,
        updated_at
    )
    values
    (
        %(game_pk)s,
        %(team_id)s,
        %(player_id)s,
        %(player_name)s,
        %(lineup_spot)s,
        %(position)s,
        %(confirmed_status)s,
        %(source)s,
        now(),
        now()
    )
    on conflict (game_pk, player_id)
    do update set
        team_id = excluded.team_id,
        player_name = excluded.player_name,
        lineup_spot = excluded.lineup_spot,
        position = excluded.position,
        confirmed_status = excluded.confirmed_status,
        source = excluded.source,
        source_timestamp = now(),
        updated_at = now()
""", rows)

print("=" * 90)
print("LINEUP LOAD COMPLETE")
print("=" * 90)
print(f"games={len(games)}")
print(f"rows_loaded={len(rows)}")

