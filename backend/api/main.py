from fastapi import FastAPI
from api.routes import health, propicks, prohits, ops

app = FastAPI(title='MLB Predictive Systems API', version='0.1.0')
app.include_router(health.router)
app.include_router(propicks.router, prefix='/propicks', tags=['ProPicksMLB'])
app.include_router(prohits.router, prefix='/prohits', tags=['ProHitsMLB'])
app.include_router(ops.router, prefix='/ops', tags=['Operations'])

@app.get('/')
def root():
    return {'status': 'ok', 'project': 'mlb-predictive-systems'}
