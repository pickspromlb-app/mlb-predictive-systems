import os
import csv
import sys
import requests
from collections import defaultdict

API_KEY = os.getenv("ODDS_API_KEY")
if not API_KEY:
    raise SystemExit("Falta ODDS_API_KEY en variable de entorno.")

SPORT = "baseball_mlb"
BASE = "https://api.the-odds-api.com/v4"
TARGET_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-04-30"
OUTFILE = f"odds_batter_hits_availability_{TARGET_DATE}.csv"

def get_events():
    url = f"{BASE}/sports/{SPORT}/events"
    res = requests.get(url, params={"apiKey": API_KEY}, timeout=30)
    print("events status:", res.status_code)
    print("remaining:", res.headers.get("x-requests-remaining"))
    if res.status_code != 200:
        print(res.text[:2000])
        raise SystemExit()
    return res.json()

def get_batter_hits(event_id):
    url = f"{BASE}/sports/{SPORT}/events/{event_id}/odds"
    params = {
        "apiKey": API_KEY,
        "regions": "us",
        "markets": "batter_hits",
        "oddsFormat": "american",
    }
    res = requests.get(url, params=params, timeout=30)
    print(f"event {event_id} status:", res.status_code, "| remaining:", res.headers.get("x-requests-remaining"))

    if res.status_code != 200:
        return None, res.text[:500]

    return res.json(), None

events = get_events()
rows = []

for e in events:
    event_id = e.get("id")
    away_team = e.get("away_team")
    home_team = e.get("home_team")
    commence_time = e.get("commence_time")

    data, err = get_batter_hits(event_id)
    if err:
        print("ERROR:", away_team, "@", home_team, err)
        continue

    for book in data.get("bookmakers", []):
        book_key = book.get("key")
        book_title = book.get("title")

        player_lines = defaultdict(lambda: {
            "has_o05": False,
            "has_o15": False,
            "o05_over_price": "",
            "o15_over_price": "",
            "all_over_points": set(),
        })

        for market in book.get("markets", []):
            if market.get("key") != "batter_hits":
                continue

            for o in market.get("outcomes", []):
                player = o.get("description")
                side = o.get("name")
                point = o.get("point")
                price = o.get("price")

                if not player or side != "Over":
                    continue

                player_lines[player]["all_over_points"].add(str(point))

                if point == 0.5:
                    player_lines[player]["has_o05"] = True
                    player_lines[player]["o05_over_price"] = price

                if point == 1.5:
                    player_lines[player]["has_o15"] = True
                    player_lines[player]["o15_over_price"] = price

        for player, info in player_lines.items():
            if info["has_o05"]:
                status = "AVAILABLE_O05"
            elif info["has_o15"]:
                status = "ONLY_O15"
            else:
                status = "OTHER_LINE_ONLY"

            rows.append({
                "event_id": event_id,
                "commence_time": commence_time,
                "away_team": away_team,
                "home_team": home_team,
                "book_key": book_key,
                "book_title": book_title,
                "player_name": player,
                "market_status": status,
                "has_o05": info["has_o05"],
                "o05_over_price": info["o05_over_price"],
                "has_o15": info["has_o15"],
                "o15_over_price": info["o15_over_price"],
                "all_over_points": ",".join(sorted(info["all_over_points"])),
            })

with open(OUTFILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=[
        "event_id",
        "commence_time",
        "away_team",
        "home_team",
        "book_key",
        "book_title",
        "player_name",
        "market_status",
        "has_o05",
        "o05_over_price",
        "has_o15",
        "o15_over_price",
        "all_over_points",
    ])
    writer.writeheader()
    writer.writerows(rows)

print("=" * 90)
print("BATTER HITS MARKET AVAILABILITY SUMMARY")
print("=" * 90)
print("events:", len(events))
print("rows:", len(rows))
print("output:", OUTFILE)

status_counts = defaultdict(int)
book_counts = defaultdict(int)

for r in rows:
    status_counts[r["market_status"]] += 1
    book_counts[r["book_key"]] += 1

print("\nBy status:")
for k, v in sorted(status_counts.items()):
    print(k, v)

print("\nBy book:")
for k, v in sorted(book_counts.items(), key=lambda x: x[1], reverse=True):
    print(k, v)

print("\nSample ONLY_O15:")
count = 0
for r in rows:
    if r["market_status"] == "ONLY_O15":
        print(f"{r['book_key']} | {r['away_team']} @ {r['home_team']} | {r['player_name']} | O1.5={r['o15_over_price']}")
        count += 1
        if count >= 20:
            break

