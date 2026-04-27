from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    environment: str = 'development'
    timezone: str = 'America/New_York'
    database_url: str = ''
    mlb_stats_api_base: str = 'https://statsapi.mlb.com/api/v1'
    weather_api_key: str = ''
    weather_api_base: str = ''
    api_internal_token: str = 'change_me'

@lru_cache
def get_settings() -> Settings:
    return Settings()

