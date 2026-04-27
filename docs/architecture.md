# Arquitectura

GitHub → Railway API/Workers/Bots → Supabase PostgreSQL → Vercel Dashboards.

Schemas:
- core: datos crudos MLB.
- propicks: ProPicksMLB.
- prohits: ProHitsMLB.
- ops: control y logs.

La separación por schema evita choque entre mercados.
