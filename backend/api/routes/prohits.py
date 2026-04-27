from datetime import date
from fastapi import APIRouter, Query
from shared.db import fetch_all
from shared.time_utils import today_local
router = APIRouter()

@router.get('/players/profiles')
def player_profiles(stat_date: date | None = Query(default=None), stat_window: str = 'L10', limit: int = 100):
    d = stat_date or today_local()
    rows = fetch_all('''select p.*, t.abbreviation as team from prohits.player_derived_stats p left join core.teams t on t.team_id=p.team_id where p.stat_date=%s and p.stat_window=%s order by p.hit_rate desc nulls last, p.avg_plate_appearances desc nulls last limit %s''', (d, stat_window, limit))
    return {'date': d, 'stat_window': stat_window, 'count': len(rows), 'rows': rows}

