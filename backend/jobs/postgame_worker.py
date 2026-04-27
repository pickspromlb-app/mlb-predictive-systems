from datetime import timedelta
import subprocess
import sys

from shared.db import fetch_one
from shared.time_utils import today_local


def run_step(label: str, command: list[str]) -> None:
    print("=" * 40)
    print(label)
    print("=" * 40)
    subprocess.run(command, check=True)


def main():
    # Si pasas fecha manual: python -m jobs.postgame_worker 2026-04-26
    # Si no pasas fecha, procesa ayer.
    if len(sys.argv) > 1:
        d = sys.argv[1]
    else:
        d = (today_local() - timedelta(days=1)).isoformat()

    print({
        "worker": "postgame_worker",
        "target_date": d,
        "status": "STARTED"
    })

    run_step(
        "1. Refrescar resultados MLB",
        [sys.executable, "-m", "jobs.run_date", d],
    )

    status = fetch_one(
        """
        select
          count(*)::int as games,
          count(*) filter (
            where away_score is not null
              and home_score is not null
          )::int as games_with_score,
          count(*) filter (
            where lower(coalesce(status, '')) = 'final'
               or lower(coalesce(detailed_state, '')) like '%%final%%'
               or lower(coalesce(detailed_state, '')) like '%%completed%%'
          )::int as final_like_games
        from core.games
        where game_date = %s::date
        """,
        (d,)
    )

    print({
        "target_date": d,
        "game_status": status
    })

    if not status or status["games"] == 0:
        print({
            "worker": "postgame_worker",
            "target_date": d,
            "status": "NO_GAMES_FOUND"
        })
        return

    if status["games_with_score"] < status["games"]:
        print({
            "worker": "postgame_worker",
            "target_date": d,
            "status": "WAITING_FOR_FINAL_SCORES"
        })
        return

    run_step(
        "2. Calificar Team Runs",
        [sys.executable, "-m", "propicks.grade_team_runs_snapshots", d],
    )

    run_step(
        "3. Generar resumen postgame",
        [sys.executable, "-m", "propicks.postgame_daily_summary", d],
    )

    print({
        "worker": "postgame_worker",
        "target_date": d,
        "status": "COMPLETED"
    })


if __name__ == "__main__":
    main()
