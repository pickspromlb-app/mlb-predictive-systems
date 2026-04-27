import { useEffect, useMemo, useState, useCallback } from 'react'
import './App.css'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'https://mlb-predictive-systems-production.up.railway.app'

const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN || 'change_me'

/* ----------------------------- Helpers ----------------------------- */

function todayISO() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function pct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '–'
  const n = Number(v)
  // Soporta tanto 0.918 como 91.8
  const value = n <= 1 ? n * 100 : n
  return `${value.toFixed(2)}%`
}

function num(v, decimals = 2) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '–'
  return Number(v).toFixed(decimals)
}

function record(w, l) {
  return `${w ?? 0}-${l ?? 0}`
}

function rateClass(rate) {
  if (rate === null || rate === undefined) return 'neutral'
  const n = Number(rate)
  const value = n <= 1 ? n * 100 : n
  if (value >= 80) return 'excellent'
  if (value >= 70) return 'good'
  if (value >= 60) return 'medium'
  return 'low'
}

async function getJson(path) {
  const res = await fetch(API_BASE + path)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} – ${path}`)
  return res.json()
}

/* ----------------------------- Static backtest ----------------------------- */
/* Datos de respaldo si /propicks/performance no devuelve nada útil */

const STATIC_BACKTEST = [
  {
    system_id: 'MONEYLINE_CORE_V1',
    rows: [
      { target_metric: 'Total', sample_size: 49, wins: 45, losses: 4, success_rate: 0.9184 },
      { target_metric: 'First half', sample_size: 27, wins: 24, losses: 3, success_rate: 0.8889 },
      { target_metric: 'Second half', sample_size: 22, wins: 21, losses: 1, success_rate: 0.9545 }
    ]
  },
  {
    system_id: 'TEAM_RUNS_CORE_V1',
    rows: [
      { target_metric: '3+ carreras', sample_size: 187, wins: 164, losses: 23, success_rate: 0.8770 },
      { target_metric: '5+ carreras', sample_size: 187, wins: 129, losses: 58, success_rate: 0.6898 }
    ]
  },
  {
    system_id: 'TEAM_RUNS_POWER_V1',
    rows: [
      { target_metric: '3+ carreras', sample_size: 107, wins: 95, losses: 12, success_rate: 0.8879 },
      { target_metric: '5+ carreras', sample_size: 107, wins: 75, losses: 32, success_rate: 0.7009 }
    ]
  },
  {
    system_id: 'TOTALS_OVER_CORE_V1',
    rows: [
      { target_metric: '8+ carreras', sample_size: 83, wins: 73, losses: 10, success_rate: 0.8795 },
      { target_metric: '9+ carreras', sample_size: 83, wins: 67, losses: 16, success_rate: 0.8072 },
      { target_metric: '10+ carreras', sample_size: 83, wins: 60, losses: 23, success_rate: 0.7229 }
    ]
  },
  {
    system_id: 'TOTALS_UNDER_CORE_V1',
    rows: [
      { target_metric: 'Under 8', sample_size: 80, wins: 59, losses: 21, success_rate: 0.7375 },
      { target_metric: 'Under 7', sample_size: 80, wins: 47, losses: 33, success_rate: 0.5875 },
      { target_metric: 'Under 6', sample_size: 80, wins: 37, losses: 43, success_rate: 0.4625 }
    ]
  },
  {
    system_id: 'TOTALS_UNDER_ELITE_V1',
    rows: [
      { target_metric: 'Under 8', sample_size: 40, wins: 34, losses: 6, success_rate: 0.8500 },
      { target_metric: 'Under 7', sample_size: 40, wins: 29, losses: 11, success_rate: 0.7250 },
      { target_metric: 'Under 6', sample_size: 40, wins: 25, losses: 15, success_rate: 0.6250 }
    ]
  }
]

const SYSTEM_COLOR = {
  MONEYLINE_CORE_V1: 'sys-blue',
  TEAM_RUNS_CORE_V1: 'sys-green',
  TEAM_RUNS_POWER_V1: 'sys-green',
  TOTALS_OVER_CORE_V1: 'sys-orange',
  TOTALS_UNDER_CORE_V1: 'sys-purple',
  TOTALS_UNDER_ELITE_V1: 'sys-purple'
}

/* ----------------------------- UI Atoms ----------------------------- */

function Spinner() {
  return <span className="spinner" aria-hidden="true" />
}

function StatusPill({ status }) {
  const s = (status || 'PENDING').toUpperCase()
  const cls = s === 'WIN' ? 'win' : s === 'LOSS' ? 'loss' : 'pending'
  return <span className={`status-pill ${cls}`}>{s}</span>
}

function TierBadge({ tier, color }) {
  if (!tier) return null
  return <span className={`tier-badge ${color}`}>{tier}</span>
}

function MetricRow({ label, value, decimals = 2 }) {
  return (
    <div className="metric-row">
      <span className="metric-label">{label}</span>
      <span className="metric-value">{num(value, decimals)}</span>
    </div>
  )
}

function StatTile({ label, value, accent, sub }) {
  return (
    <div className={`stat-tile ${accent || ''}`}>
      <div className="stat-tile-label">{label}</div>
      <div className="stat-tile-value">{value}</div>
      {sub && <div className="stat-tile-sub">{sub}</div>}
    </div>
  )
}

function EmptyState({ title, message }) {
  return (
    <div className="empty-state">
      <div className="empty-icon">∅</div>
      <div className="empty-title">{title}</div>
      <div className="empty-msg">{message}</div>
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="sk-bar w-40" />
      <div className="sk-bar w-70" />
      <div className="sk-row">
        <div className="sk-bar w-30" />
        <div className="sk-bar w-30" />
        <div className="sk-bar w-30" />
      </div>
    </div>
  )
}

/* ----------------------------- Signal Cards ----------------------------- */

function MoneylineCard({ signal }) {
  const team = signal.team_abbr || signal.team || '?'
  const opp = signal.opponent_abbr || signal.opponent || '?'
  return (
    <div className="signal-card sys-blue">
      <div className="signal-card-header">
        <div className="matchup">
          <span className="team-abbr">{team}</span>
          <span className="vs">vs</span>
          <span className="team-abbr opp">{opp}</span>
        </div>
        <TierBadge tier={signal.moneyline_tier} color="sys-blue" />
      </div>

      <div className="signal-metrics">
        <MetricRow label="Log5 Home Prob" value={signal.log5_home_prob} decimals={3} />
        <MetricRow label="WHIP Edge" value={signal.whip_edge} />
        <MetricRow label="RA Edge" value={signal.ra_edge} />
        <MetricRow label="ERA Edge" value={signal.era_edge} />
      </div>

      <div className="signal-footer">
        <StatusPill status={signal.status} />
      </div>
    </div>
  )
}

function TeamRunsCard({ signal }) {
  const team = signal.team_abbr || signal.team || '?'
  const opp = signal.opponent_abbr || signal.opponent || '?'
  return (
    <div className="signal-card sys-green">
      <div className="signal-card-header">
        <div className="matchup">
          <span className="team-abbr">{team}</span>
          <span className="vs">vs</span>
          <span className="team-abbr opp">{opp}</span>
        </div>
        <TierBadge tier={signal.team_runs_tier} color="sys-green" />
      </div>

      <div className="signal-metrics">
        <MetricRow label="Team RS L5" value={signal.team_rs_l5} />
        <MetricRow label="Opp RA L5" value={signal.opp_ra_l5} />
        <MetricRow label="Opp WHIP L5" value={signal.opp_whip_l5} />
        <MetricRow label="Opp ERA L5" value={signal.opp_era_l5} />
      </div>

      {(signal.hit_3plus !== undefined || signal.hit_5plus !== undefined) && (
        <div className="hit-row">
          {signal.hit_3plus !== undefined && (
            <span className={`hit-pill ${signal.hit_3plus ? 'hit' : 'miss'}`}>
              3+ {signal.hit_3plus ? '✓' : '✗'}
            </span>
          )}
          {signal.hit_5plus !== undefined && (
            <span className={`hit-pill ${signal.hit_5plus ? 'hit' : 'miss'}`}>
              5+ {signal.hit_5plus ? '✓' : '✗'}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function TotalsOverCard({ signal }) {
  const away = signal.away_team_abbr || signal.away_team || '?'
  const home = signal.home_team_abbr || signal.home_team || '?'
  return (
    <div className="signal-card sys-orange">
      <div className="signal-card-header">
        <div className="matchup">
          <span className="team-abbr">{away}</span>
          <span className="vs">@</span>
          <span className="team-abbr">{home}</span>
        </div>
        <TierBadge tier={signal.totals_over_tier} color="sys-orange" />
      </div>

      <div className="signal-metrics">
        <MetricRow label="Combined ERA L5" value={signal.combined_era_l5} />
        <MetricRow label="Combined WHIP L5" value={signal.combined_whip_l5} />
        <MetricRow label="Combined RA L5" value={signal.combined_ra_l5} />
        <MetricRow label="Combined RS L5" value={signal.combined_rs_l5} />
      </div>

      {(signal.hit_8plus !== undefined ||
        signal.hit_9plus !== undefined ||
        signal.hit_10plus !== undefined) && (
        <div className="hit-row">
          {signal.hit_8plus !== undefined && (
            <span className={`hit-pill ${signal.hit_8plus ? 'hit' : 'miss'}`}>
              8+ {signal.hit_8plus ? '✓' : '✗'}
            </span>
          )}
          {signal.hit_9plus !== undefined && (
            <span className={`hit-pill ${signal.hit_9plus ? 'hit' : 'miss'}`}>
              9+ {signal.hit_9plus ? '✓' : '✗'}
            </span>
          )}
          {signal.hit_10plus !== undefined && (
            <span className={`hit-pill ${signal.hit_10plus ? 'hit' : 'miss'}`}>
              10+ {signal.hit_10plus ? '✓' : '✗'}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

function TotalsUnderCard({ signal }) {
  const away = signal.away_team_abbr || signal.away_team || '?'
  const home = signal.home_team_abbr || signal.home_team || '?'
  return (
    <div className="signal-card sys-purple">
      <div className="signal-card-header">
        <div className="matchup">
          <span className="team-abbr">{away}</span>
          <span className="vs">@</span>
          <span className="team-abbr">{home}</span>
        </div>
        <TierBadge tier={signal.totals_under_tier} color="sys-purple" />
      </div>

      <div className="signal-metrics">
        <MetricRow label="Combined RA L5" value={signal.combined_ra_l5} />
        <MetricRow label="Combined WHIP L5" value={signal.combined_whip_l5} />
        <MetricRow label="Combined ERA L5" value={signal.combined_era_l5} />
        <MetricRow label="Combined RS L5" value={signal.combined_rs_l5} />
      </div>

      {(signal.hit_under8 !== undefined ||
        signal.hit_under7 !== undefined ||
        signal.hit_under6 !== undefined) && (
        <div className="hit-row">
          {signal.hit_under8 !== undefined && (
            <span className={`hit-pill ${signal.hit_under8 ? 'hit' : 'miss'}`}>
              U8 {signal.hit_under8 ? '✓' : '✗'}
            </span>
          )}
          {signal.hit_under7 !== undefined && (
            <span className={`hit-pill ${signal.hit_under7 ? 'hit' : 'miss'}`}>
              U7 {signal.hit_under7 ? '✓' : '✗'}
            </span>
          )}
          {signal.hit_under6 !== undefined && (
            <span className={`hit-pill ${signal.hit_under6 ? 'hit' : 'miss'}`}>
              U6 {signal.hit_under6 ? '✓' : '✗'}
            </span>
          )}
        </div>
      )}
    </div>
  )
}

/* ----------------------------- Main App ----------------------------- */

const TABS = [
  { id: 'moneyline', label: 'Moneyline', color: 'sys-blue' },
  { id: 'team_runs', label: 'Team Runs', color: 'sys-green' },
  { id: 'totals_over', label: 'Totals Over', color: 'sys-orange' },
  { id: 'totals_under', label: 'Totals Under', color: 'sys-purple' }
]

export default function App() {
  const [date, setDate] = useState(todayISO())
  const [signalsData, setSignalsData] = useState(null)
  const [performance, setPerformance] = useState([])
  const [summaries, setSummaries] = useState([])
  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [activeTab, setActiveTab] = useState('team_runs')

  const loadSignals = useCallback(async (d) => {
    setLoading(true)
    setError('')
    try {
      const data = await getJson(`/propicks/signals/today?analysis_date=${d}`)
      setSignalsData(data)
      // Auto-select the tab with the most signals
      const counts = data?.counts || {}
      const tabWithMost = TABS.reduce((best, t) =>
        (counts[t.id] || 0) > (counts[best.id] || 0) ? t : best
      , TABS[0])
      if ((counts[tabWithMost.id] || 0) > 0) {
        setActiveTab(tabWithMost.id)
      }
    } catch (err) {
      setError(err.message || 'Error cargando señales')
      setSignalsData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadAuxiliary = useCallback(async () => {
    try {
      const [perf, summ] = await Promise.allSettled([
        getJson('/propicks/performance'),
        getJson('/propicks/postgame/summaries?limit=30')
      ])
      if (perf.status === 'fulfilled') {
        const rows = perf.value?.rows || perf.value || []
        setPerformance(Array.isArray(rows) ? rows : [])
      }
      if (summ.status === 'fulfilled') {
        const rows = summ.value?.rows || summ.value || []
        setSummaries(Array.isArray(rows) ? rows : [])
      }
    } catch {
      /* silencioso, son auxiliares */
    }
  }, [])

  async function runDailyAnalysis() {
    setRunning(true)
    setError('')
    setSuccess('')
    try {
      const url = `${API_BASE}/propicks/run-daily?analysis_date=${date}`
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'x-internal-token': INTERNAL_TOKEN }
      })
      if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
      const data = await res.json()
      const c = data?.counts || {}
      setSuccess(
        `✓ Análisis completado · ${c.games ?? 0} juegos · ${
          (c.moneyline_signals ?? 0) +
          (c.team_runs_signals ?? 0) +
          (c.totals_over_signals ?? 0) +
          (c.totals_under_signals ?? 0)
        } señales`
      )
      await loadSignals(date)
      await loadAuxiliary()
    } catch (err) {
      setError(err.message || 'Error ejecutando run-daily')
    } finally {
      setRunning(false)
    }
  }

  useEffect(() => {
    loadSignals(date)
    loadAuxiliary()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Auto-clear success messages
  useEffect(() => {
    if (!success) return
    const t = setTimeout(() => setSuccess(''), 5000)
    return () => clearTimeout(t)
  }, [success])

  const counts = signalsData?.counts || {
    moneyline: 0,
    team_runs: 0,
    totals_over: 0,
    totals_under: 0
  }
  const signals = signalsData?.signals || {
    moneyline: [],
    team_runs: [],
    totals_over: [],
    totals_under: []
  }

  const totalSignals =
    (counts.moneyline || 0) +
    (counts.team_runs || 0) +
    (counts.totals_over || 0) +
    (counts.totals_under || 0)

  // Use API performance if non-empty, otherwise static backtest
  const backtestGroups = useMemo(() => {
    if (performance && performance.length > 0) {
      // Group by system_id if API returns flat rows
      const map = new Map()
      for (const r of performance) {
        const sid = r.system_id || 'PERFORMANCE'
        if (!map.has(sid)) map.set(sid, { system_id: sid, rows: [] })
        map.get(sid).rows.push(r)
      }
      return Array.from(map.values())
    }
    return STATIC_BACKTEST
  }, [performance])

  const activeSignals = signals[activeTab] || []
  const renderSignal = (s, i) => {
    const key = s.id || `${activeTab}-${i}`
    if (activeTab === 'moneyline') return <MoneylineCard key={key} signal={s} />
    if (activeTab === 'team_runs') return <TeamRunsCard key={key} signal={s} />
    if (activeTab === 'totals_over') return <TotalsOverCard key={key} signal={s} />
    if (activeTab === 'totals_under') return <TotalsUnderCard key={key} signal={s} />
    return null
  }

  return (
    <div className="app">
      {/* Header */}
      <header className="hero">
        <div className="hero-left">
          <div className="brand-mark">
            <span className="brand-dot" />
            <span className="brand-text">PROPICKS · MLB</span>
          </div>
          <h1 className="hero-title">Predictive Signals Dashboard</h1>
          <p className="hero-sub">
            {signalsData?.system || 'ProPicksMLB'} · {signalsData?.version || 'v1.0'} · 6 sistemas estadísticos activos
          </p>
        </div>

        <div className="hero-right">
          <div className="control-group">
            <label className="control-label">Analysis Date</label>
            <input
              className="date-input"
              type="date"
              value={date}
              onChange={(e) => {
                const newDate = e.target.value
                setDate(newDate)
                loadSignals(newDate)
              }}
            />
          </div>

          <div className="button-row">
            <button
              className="btn btn-secondary"
              onClick={() => loadSignals(date)}
              disabled={loading || running}
            >
              {loading ? <Spinner /> : '↻'} Refresh
            </button>
            <button
              className="btn btn-primary"
              onClick={runDailyAnalysis}
              disabled={running || loading}
            >
              {running ? <Spinner /> : '▶'} Run Daily
            </button>
          </div>
        </div>
      </header>

      {/* Status banners */}
      {error && (
        <div className="banner banner-error">
          <strong>Error:</strong> {error}
        </div>
      )}
      {success && (
        <div className="banner banner-success">{success}</div>
      )}

      {/* Top stat tiles */}
      <section className="stats-row">
        <StatTile
          label="Moneyline"
          value={counts.moneyline ?? 0}
          accent="sys-blue"
          sub="signals"
        />
        <StatTile
          label="Team Runs"
          value={counts.team_runs ?? 0}
          accent="sys-green"
          sub="signals"
        />
        <StatTile
          label="Totals Over"
          value={counts.totals_over ?? 0}
          accent="sys-orange"
          sub="signals"
        />
        <StatTile
          label="Totals Under"
          value={counts.totals_under ?? 0}
          accent="sys-purple"
          sub="signals"
        />
        <StatTile
          label="Total Signals"
          value={totalSignals}
          accent="sys-cyan"
          sub={signalsData?.analysis_date || date}
        />
      </section>

      {/* Daily Signals */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">Daily Signals</h2>
            <p className="panel-sub">
              Señales estadísticas activas para el {signalsData?.analysis_date || date}
            </p>
          </div>
          {loading && <span className="loading-tag"><Spinner /> Cargando...</span>}
        </div>

        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${activeTab === t.id ? 'active' : ''} ${t.color}`}
              onClick={() => setActiveTab(t.id)}
            >
              <span className="tab-label">{t.label}</span>
              <span className="tab-count">{counts[t.id] ?? 0}</span>
            </button>
          ))}
        </div>

        <div className="signals-grid">
          {loading ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : activeSignals.length === 0 ? (
            <EmptyState
              title="Sin señales"
              message={`No hay señales activas en ${TABS.find(t => t.id === activeTab)?.label} para esta fecha.`}
            />
          ) : (
            activeSignals.map(renderSignal)
          )}
        </div>
      </section>

      {/* System Backtest */}
      <section className="panel">
        <div className="panel-head">
          <div>
            <h2 className="panel-title">System Backtest</h2>
            <p className="panel-sub">Rendimiento histórico por sistema y target metric</p>
          </div>
        </div>

        <div className="backtest-grid">
          {backtestGroups.map((group) => (
            <div key={group.system_id} className={`backtest-card ${SYSTEM_COLOR[group.system_id] || 'sys-cyan'}`}>
              <div className="backtest-system">
                <span className="system-dot" />
                <span className="system-id">{group.system_id}</span>
              </div>
              <table className="backtest-table">
                <thead>
                  <tr>
                    <th>Target</th>
                    <th>Sample</th>
                    <th>W-L</th>
                    <th>Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {group.rows.map((r, i) => (
                    <tr key={i}>
                      <td className="target-cell">{r.target_metric}</td>
                      <td>{r.sample_size}</td>
                      <td>{record(r.wins, r.losses)}</td>
                      <td>
                        <span className={`rate-pill rate-${rateClass(r.success_rate)}`}>
                          {pct(r.success_rate)}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ))}
        </div>
      </section>

      {/* Postgame Summaries */}
      {summaries.length > 0 && (
        <section className="panel">
          <div className="panel-head">
            <div>
              <h2 className="panel-title">Postgame Summaries</h2>
              <p className="panel-sub">Últimos {summaries.length} resúmenes diarios</p>
            </div>
          </div>

          <div className="summaries-grid">
            {summaries.map((s, i) => (
              <div className="summary-tile" key={s.summary_date || i}>
                <div className="summary-date">{s.summary_date || '—'}</div>
                <div className="summary-record-line">
                  <span className="summary-wl">{record(s.wins, s.losses)}</span>
                  <span className={`rate-pill rate-${rateClass(s.success_rate)}`}>
                    {pct(s.success_rate)}
                  </span>
                </div>
                <div className="summary-meta">
                  {s.total_records ?? 0} análisis
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      <footer className="foot">
        <span>ProPicksMLB · Statistical signals only · No odds, no picks, no betting advice</span>
      </footer>
    </div>
  )
}

