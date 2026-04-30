import sys
import subprocess

PYTHON = sys.executable
import asyncio
from datetime import date
from shared.db import fetch_all, execute_many
from ingestion.core_update import update_core_for_date

EVAL_DATE = sys.argv[1] if len(sys.argv) > 1 else "2026-04-30"

BOOKS = [
    "draftkings",
    "betmgm",
    "betrivers",
    "betonlineag",
    "fanatics",
]

def run(cmd):
    print("\n" + "=" * 100)
    print("RUN:", " ".join(cmd))
    print("=" * 100)
    subprocess.run(cmd, check=True)

async def update_core():
    print("\n" + "=" * 100)
    print(f"UPDATING CORE FOR {EVAL_DATE}")
    print("=" * 100)

    y, m, d = [int(x) for x in EVAL_DATE.split("-")]
    result = await update_core_for_date(
        date(y, m, d),
        include_boxscores=False
    )

    print(result)

def clear_market_map():
    execute_many("""
        delete from prohits.market_event_game_map
        where market_date = %(market_date)s
    """, [{"market_date": EVAL_DATE}])

    print(f"cleared market_event_game_map for {EVAL_DATE}")

def show_summary():
    print("\n" + "=" * 100)
    print("PROHITS DAILY SUMMARY")
    print("=" * 100)

    rows = fetch_all("""
        select
            evaluation_date,
            book_key,
            player_name,
            team_name,
            opponent_team_name,
            activation_status,
            market_status,
            o05_over_price,
            o15_over_price,
            market_filter_status
        from prohits.daily_hit_candidates_view
        where evaluation_date = %s
        order by
            case when activation_status = 'ACTIVE_O05' then 0 else 1 end,
            player_name,
            book_key;
    """, [EVAL_DATE])

    if not rows:
        print("No candidates saved.")
        return

    active = [r for r in rows if r["activation_status"] == "ACTIVE_O05"]
    excluded = [r for r in rows if r["activation_status"] != "ACTIVE_O05"]

    print(f"ACTIVE_O05: {len(active)}")
    for r in active:
        print(
            f"ACTIVE | {r['book_key']} | {r['player_name']} | "
            f"{r['team_name']} vs {r['opponent_team_name']} | "
            f"O0.5={r['o05_over_price']}"
        )

    print(f"\nMARKET_EXCLUDED / OTHER: {len(excluded)}")
    for r in excluded:
        print(
            f"EXCLUDED | {r['book_key']} | {r['player_name']} | "
            f"market={r['market_status']} | "
            f"O0.5={r['o05_over_price']} | O1.5={r['o15_over_price']} | "
            f"{r['market_filter_status']}"
        )

def main():
    asyncio.run(update_core())

    run([PYTHON, "scan_odds_api_batter_hits_availability_daily.py", EVAL_DATE])

    csv_file = f"odds_batter_hits_availability_{EVAL_DATE}.csv"
    run([PYTHON, "load_market_batter_hits_availability_daily.py", csv_file])

    clear_market_map()
    run([PYTHON, "build_safe_market_event_game_map.py", EVAL_DATE])

    run([PYTHON, "load_lineup_validation.py", EVAL_DATE])

    for book in BOOKS:
        run([PYTHON, "save_prohits_daily_candidates.py", EVAL_DATE, book])

    show_summary()

if __name__ == "__main__":
    main()

