from datetime import date
from ingestion.mlb_stats_api import MLBStatsAPI
from ingestion.store_core import store_schedule, store_linescore, store_boxscore, games_for_date

async def update_core_for_date(target_date: date, include_boxscores: bool = True) -> dict:
    api = MLBStatsAPI()
    schedule = await api.schedule(target_date)
    games_found = store_schedule(schedule, target_date)
    games_processed = 0
    for g in games_for_date(target_date):
        game_pk = int(g['game_pk'])
        try:
            store_linescore(game_pk, await api.linescore(game_pk))
            if include_boxscores and g.get('detailed_state') in ('Final','Game Over','Completed Early'):
                store_boxscore(game_pk, target_date, int(g['away_team_id']), int(g['home_team_id']), await api.boxscore(game_pk))
            games_processed += 1
        except Exception as exc:
            print(f'[WARN] game {game_pk} failed: {exc}')
    return {'games_found': games_found, 'games_processed': games_processed}

