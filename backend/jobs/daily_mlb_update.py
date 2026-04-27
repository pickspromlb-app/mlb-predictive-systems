import asyncio
import json
from uuid import uuid4
from shared.time_utils import today_local, yesterday_local
from shared.db import execute_many
from ingestion.core_update import update_core_for_date
from propicks.build_profiles import build_daily_team_profiles
from propicks.filters import evaluate_offensive_edge
from prohits.build_player_profiles import build_player_profiles

async def run():
    today = today_local()
    yesterday = yesterday_local()
    run_id = f'daily_mlb_update_{today.isoformat()}_{uuid4().hex[:8]}'
    execute_many("insert into ops.job_runs (run_id,job_name,run_date,status) values (%(run_id)s,'daily_mlb_update',%(run_date)s,'RUNNING')", [{'run_id': run_id, 'run_date': today}])
    execute_many("insert into ops.daily_update_log (run_id,run_date,status) values (%(run_id)s,%(run_date)s,'RUNNING')", [{'run_id': run_id, 'run_date': today}])
    try:
        y = await update_core_for_date(yesterday, include_boxscores=True)
        t = await update_core_for_date(today, include_boxscores=False)
        profiles = build_daily_team_profiles(today)
        edges = evaluate_offensive_edge(today)
        prohits = build_player_profiles(today)
        metadata = {'yesterday': y, 'today': t, 'propicks_profiles': profiles, 'edges': edges, 'prohits_profiles': prohits}
        execute_many("update ops.job_runs set status='SUCCESS', finished_at=now(), metadata=%(metadata)s::jsonb where run_id=%(run_id)s", [{'run_id': run_id, 'metadata': json.dumps(metadata)}])
        execute_many("update ops.daily_update_log set status='SUCCESS', finished_at=now(), games_found=%(games_found)s, games_processed=%(games_processed)s, propicks_profiles_created=%(profiles)s, prohits_profiles_created=%(prohits)s, systems_processed=1 where run_id=%(run_id)s", [{'run_id': run_id, 'games_found': t.get('games_found',0), 'games_processed': y.get('games_processed',0)+t.get('games_processed',0), 'profiles': profiles, 'prohits': prohits}])
        return metadata
    except Exception as exc:
        execute_many("update ops.job_runs set status='FAILED', finished_at=now(), errors=%(errors)s::jsonb where run_id=%(run_id)s", [{'run_id': run_id, 'errors': json.dumps([str(exc)])}])
        execute_many("update ops.daily_update_log set status='FAILED', finished_at=now(), errors=%(errors)s::jsonb where run_id=%(run_id)s", [{'run_id': run_id, 'errors': json.dumps([str(exc)])}])
        raise

if __name__ == '__main__':
    print(asyncio.run(run()))
