# mlb-predictive-systems

Sistema base para construir dos productos MLB separados:

- **ProPicksMLB**: moneyline, run line/spread, full game totals, F5 totals, team runs.
- **ProHitsMLB**: únicamente jugadores Over 0.5 hits.

Stack definido:

- **GitHub** = fuente de verdad del código.
- **Supabase PostgreSQL** = base madre online.
- **Railway** = FastAPI, workers diarios y bots Telegram.
- **Vercel** = dashboards web separados.

## Separación anti-choque

Una sola base Supabase, pero con schemas aislados:

- `core`: datos MLB crudos y compartidos.
- `propicks`: métricas, filtros, resultados y backtesting de ProPicksMLB.
- `prohits`: métricas, filtros, candidatos y backtesting de ProHitsMLB.
- `ops`: logs, auditoría y control de errores.

## Orden de instalación

1. Crear proyecto Supabase.
2. Ejecutar SQL en este orden:
   - `database/01_core.sql`
   - `database/02_propicks.sql`
   - `database/03_prohits.sql`
   - `database/04_ops.sql`
   - `database/05_seed.sql`
3. Subir repo a GitHub como `mlb-predictive-systems`.
4. Conectar Railway a GitHub.
5. Conectar Vercel a GitHub.
6. Configurar variables de entorno según `.env.example`.

## Servicios Railway sugeridos

- `mlb-api`: root `/backend`, start `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- `mlb-daily-worker`: root `/backend`, start/cron `python -m jobs.daily_mlb_update`
- `propicks-bot`: root `/bots/propicks-bot`, start `python bot.py`
- `prohits-bot`: root `/bots/prohits-bot`, start `python bot.py`

## Dashboards Vercel

- ProPicksMLB: root `/dashboards/propicks-dashboard`
- ProHitsMLB: root `/dashboards/prohits-dashboard`
