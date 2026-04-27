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
