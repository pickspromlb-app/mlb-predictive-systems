from datetime import date
import os
import subprocess
import sys

from fastapi import APIRouter, Header, HTTPException, Query

from shared.db import fetch_one

router = APIRouter()


@router.post('/team-runs/save-analysis')
def save_team_runs_analysis(
    analysis_date: date = Query(...),
    x_internal_token: str | None = Header(default=None),
):
    expected_token = os.getenv('API_INTERNAL_TOKEN', 'change_me')

    if x_internal_token != expected_token:
        raise HTTPException(status_code=401, detail='Invalid internal token')

    d = analysis_date.isoformat()

    subprocess.run(
        [sys.executable, "-m", "propicks.create_analysis_snapshots"],
        check=True,
    )

    subprocess.run(
        [sys.executable, "-m", "propicks.create_team_runs_snapshots", d],
        check=True,
    )

    counts = fetch_one(
        """
        select
          count(*) filter (
            where target_metric = 'pre_game_offensive_edge'
          )::int as offensive_snapshots,

          count(*) filter (
            where target_metric = 'team_3plus_runs'
          )::int as team_3plus_snapshots,

          count(*) filter (
            where target_metric = 'team_5plus_runs'
          )::int as team_5plus_snapshots

        from propicks.analysis_snapshots
        where analysis_date = %s::date
          and target_metric in (
            'pre_game_offensive_edge',
            'team_3plus_runs',
            'team_5plus_runs'
          )
        """,
        (d,),
    )

    return {
        "status": "saved",
        "analysis_date": d,
        "offensive_snapshots": counts["offensive_snapshots"],
        "team_3plus_snapshots": counts["team_3plus_snapshots"],
        "team_5plus_snapshots": counts["team_5plus_snapshots"],
    }


@router.post('/run-daily')
def run_daily_propicks(
    analysis_date: date = Query(...),
    x_internal_token: str | None = Header(default=None),
):
    expected_token = os.getenv('API_INTERNAL_TOKEN', 'change_me')

    if x_internal_token != expected_token:
        raise HTTPException(status_code=401, detail='Invalid internal token')

    d = analysis_date.isoformat()

    commands = [
        [sys.executable, "-m", "jobs.run_date", d],
        [sys.executable, "-m", "propicks.build_team_pitching_profiles"],
        [sys.executable, "-m", "propicks.create_analysis_snapshots"],
        [sys.executable, "-m", "propicks.create_team_runs_snapshots", d],
    ]

    command_logs = []

    for cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
            command_logs.append({
                "command": " ".join(cmd),
                "status": "ok",
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
            })
        except subprocess.CalledProcessError as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "status": "failed",
                    "analysis_date": d,
                    "command": " ".join(cmd),
                    "stdout": exc.stdout,
                    "stderr": exc.stderr,
                },
            )

    counts = fetch_one(
        """
        select
          (
            select count(*)::int
            from core.games
            where game_date = %s::date
          ) as games,

          (
            select count(*)::int
            from propicks.daily_team_profile
            where profile_date = %s::date
          ) as team_profiles,

          (
            select count(*)::int
            from propicks.analysis_snapshots
            where analysis_date = %s::date
              and target_metric = 'pre_game_offensive_edge'
          ) as offensive_snapshots,

          (
            select count(*)::int
            from propicks.analysis_snapshots
            where analysis_date = %s::date
              and target_metric = 'team_3plus_runs'
          ) as team_3plus_snapshots,

          (
            select count(*)::int
            from propicks.analysis_snapshots
            where analysis_date = %s::date
              and target_metric = 'team_5plus_runs'
          ) as team_5plus_snapshots,

          (
            select count(*)::int
            from propicks.moneyline_core_v1_signals
            where analysis_date = %s::date
          ) as moneyline_signals,

          (
            select count(*)::int
            from propicks.team_runs_core_v1_signals
            where analysis_date = %s::date
          ) as team_runs_signals,

          (
            select count(*)::int
            from propicks.totals_over_core_v1_signals
            where analysis_date = %s::date
          ) as totals_over_signals,

          (
            select count(*)::int
            from propicks.totals_under_core_v1_signals
            where analysis_date = %s::date
          ) as totals_under_signals
        """,
        (d, d, d, d, d, d, d, d, d),
    )

    return {
        "status": "completed",
        "analysis_date": d,
        "counts": counts,
        "commands": command_logs,
    }
