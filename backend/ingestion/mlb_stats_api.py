import httpx
from datetime import date
from typing import Any
from tenacity import retry, stop_after_attempt, wait_exponential
from shared.settings import get_settings

class MLBStatsAPI:
    def __init__(self):
        self.base = get_settings().mlb_stats_api_base.rstrip('/')

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=0.5, max=4))
    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.get(f'{self.base}{path}', params=params)
            r.raise_for_status()
            return r.json()

    async def schedule(self, game_date: date) -> dict:
        return await self._get('/schedule', {'sportId': 1, 'date': game_date.isoformat(), 'hydrate': 'probablePitcher,team,venue'})

    async def linescore(self, game_pk: int) -> dict:
        return await self._get(f'/game/{game_pk}/linescore')

    async def boxscore(self, game_pk: int) -> dict:
        return await self._get(f'/game/{game_pk}/boxscore')
