import { useEffect, useMemo, useState } from 'react'
import './App.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://mlb-predictive-systems-production.up.railway.app'

function pct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '0.0%'
  return `${(Number(v) * 100).toFixed(1)}%`
}

function record(w, l) {
  return `${w ?? 0}-${l ?? 0}`
}

function label(metric) {
  if (metric === 'team_3plus_runs') return 'Team Runs 3+'
  if (metric === 'team_5plus_runs') return 'Team Runs 5+'
  if (metric === 'pre_game_offensive_edge') return 'Offensive Edge'
  return metric
}

async function getJson(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

function StatCard({ title, value, sub }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{title}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-sub">{sub}</div>
    </div>
  )
}

export default function App() {
  const [date, setDate] = useState('2026-04-26')
  const [performance, setPerformance] = useState([])
  const [audit, setAudit] = useState(null)
  const [summaries, setSummaries] = useState([])
  const [teamRuns, setTeamRuns] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function load(d = date) {
    try {
      setLoading(true)
      setError('')

      const [p, a, s, tr] = await Promise.all([
        getJson('/propicks/performance'),
        getJson('/propicks/audit/team-runs/global'),
        getJson('/propicks/postgame/summaries?limit=30'),
        getJson(`/propicks/team-runs/today?analysis_date=${d}`)
      ])

      setPerformance(p.rows || [])
      setAudit(a)
      setSummaries(s.rows || [])
      setTeamRuns(tr.rows || [])
    } catch (err) {
      setError(err.message || 'Error cargando API')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load(date)
  }, [])

  const total = audit?.total || {}
  const tr3 = audit?.by_target_metric?.find(x => x.target_metric === 'team_3plus_runs') || {}
  const tr5 = audit?.by_target_metric?.find(x => x.target_metric === 'team_5plus_runs') || {}
  const last = summaries?.[0]

  const grouped = useMemo(() => {
    const map = new Map()

    for (const row of teamRuns) {
      const key = `${row.game_pk}-${row.team_id}`
      if (!map.has(key)) {
        map.set(key, {
          key,
          game_pk: row.game_pk,
          team: row.team,
          opponent: row.opponent,
          away_team: row.away_team,
          home_team: row.home_team,
          away_runs: row.away_runs,
          home_runs: row.home_runs,
          rows: []
        })
      }
      map.get(key).rows.push(row)
    }

    return Array.from(map.values())
  }, [teamRuns])

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <div className="eyebrow">MLB Predictive Systems</div>
          <h1>ProPicksMLB Dashboard</h1>
          <p>Team Runs Pressure Filter v1 · Auditoría, resultados y rendimiento histórico.</p>
        </div>

        <div className="top-actions">
          <input
            type="date"
            value={date}
            onChange={(e) => {
              setDate(e.target.value)
              load(e.target.value)
            }}
          />
          <button onClick={() => load(date)} disabled={loading}>
            {loading ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>
      </header>

      {error && <div className="error-box">Error API: {error}</div>}

      <section className="grid stats-grid">
        <StatCard
          title="Acierto global"
          value={pct(total.success_rate)}
          sub={`${record(total.wins, total.losses)} · muestra ${total.sample_size ?? 0}`}
        />
        <StatCard
          title="Team Runs 3+"
          value={pct(tr3.success_rate)}
          sub={`${record(tr3.wins, tr3.losses)} · muestra ${tr3.sample_size ?? 0}`}
        />
        <StatCard
          title="Team Runs 5+"
          value={pct(tr5.success_rate)}
          sub={`${record(tr5.wins, tr5.losses)} · muestra ${tr5.sample_size ?? 0}`}
        />
        <StatCard
          title="Último resumen"
          value={last ? pct(last.success_rate) : 'Sin datos'}
          sub={last ? `${last.summary_date} · ${record(last.wins, last.losses)}` : 'No disponible'}
        />
      </section>

      <main className="layout">
        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Performance global</h2>
              <p>Rendimiento guardado en Supabase.</p>
            </div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Métrica</th>
                  <th>Muestra</th>
                  <th>Récord</th>
                  <th>Acierto</th>
                  <th>Filtro</th>
                </tr>
              </thead>
              <tbody>
                {performance.map((row) => (
                  <tr key={row.target_metric}>
                    <td>{label(row.target_metric)}</td>
                    <td>{row.sample_size}</td>
                    <td>{record(row.wins, row.losses)}</td>
                    <td>
                      <span className={Number(row.success_rate) >= 0.65 ? 'pill good' : 'pill weak'}>
                        {pct(row.success_rate)}
                      </span>
                    </td>
                    <td className="filters">
                      {(row.best_filters || []).length
                        ? row.best_filters.join(' + ')
                        : 'No usar como filtro final'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="panel">
          <div className="panel-header">
            <div>
              <h2>Resumen postgame</h2>
              <p>Histórico diario de ganados/perdidos.</p>
            </div>
          </div>

          <div className="summary-list">
            {summaries.map((s) => (
              <div className="summary-row" key={s.summary_date}>
                <div>
                  <strong>{s.summary_date}</strong>
                  <span>{s.total_records} análisis</span>
                </div>
                <div className="summary-record">
                  <span>{record(s.wins, s.losses)}</span>
                  <span className={Number(s.success_rate) >= 0.65 ? 'pill good' : 'pill weak'}>
                    {pct(s.success_rate)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      </main>

      <section className="panel wide">
        <div className="panel-header">
          <div>
            <h2>Análisis Team Runs por fecha</h2>
            <p>Fecha seleccionada: {date}. Equipos que activaron Pressure Filter v1.</p>
          </div>
          <span className="count-badge">{teamRuns.length} registros</span>
        </div>

        {grouped.length === 0 ? (
          <div className="empty">No hay candidatos Team Runs para esta fecha.</div>
        ) : (
          <div className="cards-grid">
            {grouped.map((game) => (
              <div className="pick-card" key={game.key}>
                <div className="pick-title">
                  <div>
                    <span className="game-line">{game.away_team} @ {game.home_team}</span>
                    <h3>{game.team} vs {game.opponent}</h3>
                  </div>
                  <div className="score-box">
                    {game.away_runs ?? '-'} - {game.home_runs ?? '-'}
                  </div>
                </div>

                <div className="pick-markets">
                  {game.rows.map((row) => (
                    <div className="market-row" key={row.id}>
                      <div>
                        <strong>{label(row.target_metric)}</strong>
                        <span>Score {Number(row.score).toFixed(1)} · Tier {row.confidence_tier}</span>
                      </div>
                      <span className={`result-pill ${row.success === true ? 'win' : row.success === false ? 'loss' : 'pending'}`}>
                        {row.success === true ? 'WIN' : row.success === false ? 'LOSS' : 'PENDING'}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="metric-box">
                  <div>
                    <span>Opp WHIP L5</span>
                    <strong>{game.rows?.[0]?.metrics_snapshot?.opponent_whip_l5 ?? 'NA'}</strong>
                  </div>
                  <div>
                    <span>Opp RA Avg L5</span>
                    <strong>{game.rows?.[0]?.metrics_snapshot?.opponent_runs_allowed_avg_l5 ?? 'NA'}</strong>
                  </div>
                  <div>
                    <span>Team wRC+ L5</span>
                    <strong>{game.rows?.[0]?.metrics_snapshot?.team_wrc_plus_l5 ?? 'NA'}</strong>
                  </div>
                </div>

                <div className="filter-text">
                  {(game.rows?.[0]?.filters_passed || []).join(' + ')}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
