from datetime import timedelta
import subprocess
import sys

from shared.time_utils import today_local


def run_step(label: str, command: list[str]) -> None:
    print("=" * 40)
    print(label)
    print("=" * 40)
    subprocess.run(command, check=True)


def main():
    # El worker de 7 AM procesa el día anterior.
    target_date = today_local() - timedelta(days=1)
    d = target_date.isoformat()

    print({
        "worker": "daily_7am_update",
        "target_date": d,
        "status": "STARTED"
    })

    run_step(
        "1. Cargar datos MLB del día anterior",
        [sys.executable, "-m", "jobs.run_date", d],
    )

    run_step(
        "2. Recalcular perfiles de pitcheo",
        [sys.executable, "-m", "propicks.build_team_pitching_profiles"],
    )

    run_step(
        "3. Crear snapshots ProPicks offensive edge",
        [sys.executable, "-m", "propicks.create_analysis_snapshots"],
    )

    run_step(
        "4. Crear snapshots Team Runs 3+ / 5+",
        [sys.executable, "-m", "propicks.create_team_runs_snapshots", d],
    )

    run_step(
        "5. Calificar Team Runs del día anterior",
        [sys.executable, "-m", "propicks.grade_team_runs_snapshots", d],
    )

    run_step(
        "6. Generar resumen postgame del día anterior",
        [sys.executable, "-m", "propicks.postgame_daily_summary", d],
    )

    print({
        "worker": "daily_7am_update",
        "target_date": d,
        "status": "COMPLETED"
    })


if __name__ == "__main__":
    main()
