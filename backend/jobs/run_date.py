import asyncio
import sys
from datetime import date
from ingestion.core_update import update_core_for_date
from propicks.build_profiles import build_daily_team_profiles
from propicks.filters import evaluate_offensive_edge

async def main():
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python -m jobs.run_date YYYY-MM-DD')
    d = date.fromisoformat(sys.argv[1])
    print(await update_core_for_date(d, include_boxscores=True))
    print('profiles', build_daily_team_profiles(d))
    print('edges', evaluate_offensive_edge(d))

if __name__ == '__main__':
    asyncio.run(main())

