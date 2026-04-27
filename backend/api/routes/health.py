from fastapi import APIRouter
from shared.db import fetch_one
router = APIRouter()

@router.get('/health')
def health():
    return {'status': 'ok'}

@router.get('/health-db')
def health_db():
    row = fetch_one('select now() as db_time')
    return {'status': 'ok', 'db_time': row['db_time'] if row else None}
