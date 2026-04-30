import csv
import sys
from datetime import datetime
from shared.db import execute_many

CSV_FILE = sys.argv[1] if len(sys.argv) > 1 else "odds_batter_hits_availability_2026-04-30.csv"

def parse_bool(v):
    return str(v).lower() in ("true", "1", "yes")

def parse_int(v):
    if v is None or v == "":
        return None
    return int(float(v))

def parse_market_date(commence_time):
    if not commence_time:
        return None
    return datetime.fromisoformat(commence_time.replace("Z", "+00:00")).date()

rows = []

with open(CSV_FILE, newline="", encoding="utf-8") as f:
    reader = csv.DictReader(f)

    for r in reader:
        rows.append({
            "market_date": parse_market_date(r["commence_time"]),
            "event_id": r["event_id"],
            "commence_time": r["commence_time"],
            "away_team": r["away_team"],
            "home_team": r["home_team"],
            "book_key": r["book_key"],
            "book_title": r["book_title"],
            "player_name": r["player_name"],
            "market_status": r["market_status"],
            "has_o05": parse_bool(r["has_o05"]),
            "o05_over_price": parse_int(r["o05_over_price"]),
            "has_o15": parse_bool(r["has_o15"]),
            "o15_over_price": parse_int(r["o15_over_price"]),
            "all_over_points": r["all_over_points"],
        })

market_dates = sorted({r["market_date"] for r in rows if r["market_date"]})

execute_many("""
    delete from prohits.market_batter_hits_availability
    where market_date = %(market_date)s
""", [{"market_date": d} for d in market_dates])

execute_many("""
    insert into prohits.market_batter_hits_availability
    (
        market_date,
        event_id,
        commence_time,
        away_team,
        home_team,
        book_key,
        book_title,
        player_name,
        market_status,
        has_o05,
        o05_over_price,
        has_o15,
        o15_over_price,
        all_over_points,
        updated_at
    )
    values
    (
        %(market_date)s,
        %(event_id)s,
        %(commence_time)s,
        %(away_team)s,
        %(home_team)s,
        %(book_key)s,
        %(book_title)s,
        %(player_name)s,
        %(market_status)s,
        %(has_o05)s,
        %(o05_over_price)s,
        %(has_o15)s,
        %(o15_over_price)s,
        %(all_over_points)s,
        now()
    )
    on conflict (market_date, event_id, book_key, player_name)
    do update set
        commence_time = excluded.commence_time,
        away_team = excluded.away_team,
        home_team = excluded.home_team,
        book_title = excluded.book_title,
        market_status = excluded.market_status,
        has_o05 = excluded.has_o05,
        o05_over_price = excluded.o05_over_price,
        has_o15 = excluded.has_o15,
        o15_over_price = excluded.o15_over_price,
        all_over_points = excluded.all_over_points,
        updated_at = now()
""", rows)

print("=" * 90)
print("LOADED MARKET BATTER HITS AVAILABILITY DAILY")
print("=" * 90)
print(f"csv_file={CSV_FILE}")
print(f"market_dates={market_dates}")
print(f"rows_loaded={len(rows)}")
