from datetime import date
from fastapi import APIRouter, Query
from shared.db import fetch_all
from shared.time_utils import today_local
router = APIRouter()

@router.get('/profiles/today')
def profiles_today(profile_date: date | None = Query(default=None), stat_window: str = 'L5'):
    d = profile_date or today_local()
    rows = fetch_all('''select p.*, t.abbreviation as team, o.abbreviation as opponent from propicks.daily_team_profile p left join core.teams t on t.team_id=p.team_id left join core.teams o on o.team_id=p.opponent_team_id where p.profile_date=%s and p.stat_window=%s order by p.game_pk,p.home_away''', (d, stat_window))
    return {'date': d, 'stat_window': stat_window, 'count': len(rows), 'rows': rows}

@router.get('/edges/today')
def edges_today(evaluation_date: date | None = Query(default=None)):
    d = evaluation_date or today_local()
    rows = fetch_all('''select r.*, t.abbreviation as team, o.abbreviation as opponent from propicks.market_results r left join core.teams t on t.team_id=r.team_id left join core.teams o on o.team_id=r.opponent_team_id where r.evaluation_date=%s and r.target_metric='pre_game_offensive_edge' order by r.score desc nulls last''', (d,))
    return {'date': d, 'count': len(rows), 'rows': rows}

