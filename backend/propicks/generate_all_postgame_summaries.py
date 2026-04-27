import subprocess
import sys
from shared.db import fetch_all

def main():
    rows = fetch_all("""
        select distinct analysis_date
        from propicks.analysis_snapshots
        where target_metric in ('team_3plus_runs', 'team_5plus_runs')
          and grade_status = 'GRADED'
        order by analysis_date
    """)

    print({"dates_found": len(rows)})

    for row in rows:
        d = str(row["analysis_date"])
        print("=" * 30)
        print("Generando resumen:", d)
        print("=" * 30)
        subprocess.run(
            [sys.executable, "-m", "propicks.postgame_daily_summary", d],
            check=True
        )

if __name__ == "__main__":
    main()
