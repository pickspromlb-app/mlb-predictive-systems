from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import health, propicks, prohits, ops

app = FastAPI(title='MLB Predictive Systems API', version='0.1.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(propicks.router, prefix='/propicks', tags=['ProPicksMLB'])
app.include_router(prohits.router, prefix='/prohits', tags=['ProHitsMLB'])
app.include_router(ops.router, prefix='/ops', tags=['Operations'])

@app.get('/')
def root():
    return {'status': 'ok', 'project': 'mlb-predictive-systems'}
