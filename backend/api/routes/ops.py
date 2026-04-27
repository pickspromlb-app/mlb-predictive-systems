from fastapi import APIRouter
from shared.db import fetch_all, fetch_one
router = APIRouter()

@router.get('/latest-update')
def latest_update():
    return {'latest': fetch_one('select * from ops.daily_update_log order by started_at desc limit 1')}

@router.get('/job-runs')
def job_runs(limit: int = 20):
    rows = fetch_all('select * from ops.job_runs order by started_at desc limit %s', (limit,))
    return {'count': len(rows), 'rows': rows}

