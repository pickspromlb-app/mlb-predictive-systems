import { useEffect, useMemo, useState, useCallback } from 'react'
import './App.css'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'https://mlb-predictive-systems-production.up.railway.app'

const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN || 'change_me'

/* Endpoint para Save Analysis. Cambiar aquí cuando esté listo el genérico. */
const SAVE_ANALYSIS_ENDPOINT = '/propicks/save-daily-analysis'
// Cuando esté disponible, cambiar a: '/propicks/save-daily-analysis'

/* ============================================================
   Helpers
   ============================================================ */

function todayISO() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(
    d.getDate()
  ).padStart(2, '0')}`
}

function pct(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return '–'
  const n = Number(v)
  const value = n <= 1 ? n * 100 : n
  return `${value.toFixed(1)}%`
}

function num(v, decimals = 2) {
  if (v === null || v === undefined || v === '' || Number.isNaN(Number(v))) return '–'
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
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function postJson(path) {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'x-internal-token': INTERNAL_TOKEN }
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

/* ============================================================
   Pick interpretation per market
   ============================================================ */

function interpretTeamRuns(signal) {
  const tier = (signal.team_runs_tier || '').toString().toUpperCase()
  const team = signal.team_abbr || signal.team || '?'
  const opp = signal.opponent_abbr || signal.opponent || '?'
  const teamFull = signal.team_name || ''
  const oppFull = signal.opponent_name || ''

  const is5plus = tier.includes('5PLUS')
  const isPower = tier.includes('POWER')

  const target = is5plus ? '5' : '3'
  const strengthLabel = isPower ? 'Fuerte' : 'Core'
  const strengthCls = isPower ? 'strength-strong' : 'strength-core'

  const fullLine = teamFull && oppFull ? `${teamFull} vs ${oppFull}` : null

  return {
    badge: 'Team Runs',
    title: `${team} más de ${target} carreras`,
    subtitle: `Rival: ${opp} · Señal ${strengthLabel.toLowerCase()}`,
    fullLine,
    objectives: is5plus
      ? [
          { label: 'Objetivo principal', value: '5+ carreras del equipo' },
          { label: 'Objetivo secundario', value: '3+ carreras del equipo' }
        ]
      : [{ label: 'Objetivo principal', value: '3+ carreras del equipo' }],
    techCode: tier,
    strengthLabel,
    strengthCls,
    metrics: [
      { label: 'Team RS L5', value: signal.team_rs_l5 },
      { label: 'Opp RA L5', value: signal.opp_ra_l5 },
      { label: 'Opp WHIP L5', value: signal.opp_whip_l5 },
      { label: 'Opp ERA L5', value: signal.opp_era_l5 }
    ],
    status: deriveTeamRunsStatus(signal, is5plus)
  }
}

function deriveTeamRunsStatus(signal, is5plus) {
  const isFinal = signal.is_final === true
  const primary = is5plus ? signal.hit_5plus : signal.hit_3plus
  if (primary === true) return { kind: 'win', label: 'Win' }
  if (primary === false) return { kind: 'loss', label: 'Loss' }
  if (isFinal) return { kind: 'final', label: 'Final' }
  return { kind: 'pending', label: 'Pending' }
}

function interpretTotalsOver(signal) {
  const tier = (signal.totals_over_tier || '').toString().toUpperCase()
  const away = signal.away_team_abbr || signal.away_team || '?'
  const home = signal.home_team_abbr || signal.home_team || '?'

  let target = '8'
  if (tier.includes('10PLUS')) target = '10'
  else if (tier.includes('9PLUS')) target = '9'
  else if (tier.includes('8PLUS')) target = '8'

  const objectives = []
  if (target === '8') {
    objectives.push({ label: 'Objetivo principal', value: '8+ carreras del juego' })
    objectives.push({ label: 'Objetivo secundario', value: '9+ carreras del juego' })
  } else if (target === '9') {
    objectives.push({ label: 'Objetivo principal', value: '9+ carreras del juego' })
    objectives.push({ label: 'Objetivo secundario', value: '10+ carreras del juego' })
  } else if (target === '10') {
    objectives.push({ label: 'Objetivo principal', value: '10+ carreras del juego' })
  }

  return {
    badge: 'Totals Over',
    title: `${away} @ ${home} más de ${target} carreras`,
    subtitle: 'Total del juego · ambiente alto de carreras',
    fullLine: null,
    objectives,
    techCode: tier,
    strengthLabel: 'Core',
    strengthCls: 'strength-core',
    metrics: [
      { label: 'Combined ERA L5', value: signal.combined_era_l5 },
      { label: 'Combined WHIP L5', value: signal.combined_whip_l5 },
      { label: 'Combined RA L5', value: signal.combined_ra_l5 },
      { label: 'Combined RS L5', value: signal.combined_rs_l5 }
    ],
    status: deriveOverStatus(signal, target)
  }
}

function deriveOverStatus(signal, target) {
  const isFinal = signal.is_final === true
  let primary
  if (target === '8') primary = signal.hit_8plus
  else if (target === '9') primary = signal.hit_9plus
  else if (target === '10') primary = signal.hit_10plus
  if (primary === true) return { kind: 'win', label: 'Win' }
  if (primary === false) return { kind: 'loss', label: 'Loss' }
  if (isFinal) return { kind: 'final', label: 'Final' }
  return { kind: 'pending', label: 'Pending' }
}

function interpretTotalsUnder(signal) {
  const tier = (signal.totals_under_tier || '').toString().toUpperCase()
  const away = signal.away_team_abbr || signal.away_team || '?'
  const home = signal.home_team_abbr || signal.home_team || '?'

  const isElite = tier.includes('ELITE')

  // ELITE: el rango sugerido es 7/8
  const titleSuffix = isElite ? 'menos de 7/8 carreras' : 'menos de 8 carreras'
  const subtitle = isElite
    ? 'Señal elite · ambiente muy bajo'
    : 'Total del juego · ambiente bajo de carreras'

  const objectives = isElite
    ? [
        { label: 'Objetivo principal', value: 'Under 8' },
        { label: 'Objetivo secundario', value: 'Under 7' }
      ]
    : [{ label: 'Objetivo principal', value: 'Under 8' }]

  return {
    badge: 'Totals Under',
    title: `${away} @ ${home} ${titleSuffix}`,
    subtitle,
    fullLine: null,
    objectives,
    techCode: tier,
    strengthLabel: isElite ? 'Elite' : 'Core',
    strengthCls: isElite ? 'strength-elite' : 'strength-core',
    metrics: [
      { label: 'Combined RA L5', value: signal.combined_ra_l5 },
      { label: 'Combined WHIP L5', value: signal.combined_whip_l5 },
      { label: 'Combined ERA L5', value: signal.combined_era_l5 },
      { label: 'Combined RS L5', value: signal.combined_rs_l5 }
    ],
    status: deriveUnderStatus(signal, isElite)
  }
}

function deriveUnderStatus(signal, isElite) {
  const isFinal = signal.is_final === true
  const primary = signal.hit_under8
  if (primary === true) return { kind: 'win', label: 'Win' }
  if (primary === false) return { kind: 'loss', label: 'Loss' }
  if (isFinal) return { kind: 'final', label: 'Final' }
  return { kind: 'pending', label: 'Pending' }
}

function interpretMoneyline(signal) {
  const tier = (signal.moneyline_tier || '').toString().toUpperCase()
  const team = signal.team_abbr || signal.team || '?'
  const isHome = tier.includes('HOME')
  const sideLabel = isHome ? 'Local' : 'Visitante'

  return {
    badge: 'Moneyline',
    title: `${team} Moneyline`,
    subtitle: `${sideLabel} · señal core`,
    fullLine: null,
    objectives: [{ label: 'Objetivo principal', value: `Victoria de ${team}` }],
    techCode: tier,
    strengthLabel: 'Core',
    strengthCls: 'strength-core',
    metrics: [
      { label: 'Log5 Home Prob', value: signal.log5_home_prob, decimals: 3 },
      { label: 'WHIP Edge', value: signal.whip_edge },
      { label: 'RA Edge', value: signal.ra_edge },
      { label: 'ERA Edge', value: signal.era_edge }
    ],
    status: deriveMlStatus(signal)
  }
}

function deriveMlStatus(signal) {
  const isFinal = signal.is_final === true
  const won = signal.won_moneyline
  if (won === true) return { kind: 'win', label: 'Win' }
  if (won === false) return { kind: 'loss', label: 'Loss' }
  if (isFinal) return { kind: 'final', label: 'Final' }
  return { kind: 'pending', label: 'Pending' }
}

function interpret(variant, signal) {
  if (variant === 'team_runs') return interpretTeamRuns(signal)
  if (variant === 'totals_over') return interpretTotalsOver(signal)
  if (variant === 'totals_under') return interpretTotalsUnder(signal)
  if (variant === 'moneyline') return interpretMoneyline(signal)
  return null
}

/* ============================================================
   Static fallback for backtest (only if endpoint returns empty)
   ============================================================ */

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
      { target_metric: '3+ carreras', sample_size: 187, wins: 164, losses: 23, success_rate: 0.877 },
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
      { target_metric: 'Under 8', sample_size: 40, wins: 34, losses: 6, success_rate: 0.85 },
      { target_metric: 'Under 7', sample_size: 40, wins: 29, losses: 11, success_rate: 0.725 },
      { target_metric: 'Under 6', sample_size: 40, wins: 25, losses: 15, success_rate: 0.625 }
    ]
  }
]

const SYSTEM_COLOR = {
  MONEYLINE_CORE_V1: 'sys-blue',
  TEAM_RUNS_CORE_V1: 'sys-green',
  TEAM_RUNS_POWER_V1: 'sys-emerald',
  TOTALS_OVER_CORE_V1: 'sys-orange',
  TOTALS_UNDER_CORE_V1: 'sys-purple',
  TOTALS_UNDER_ELITE_V1: 'sys-violet'
}

const TABS = [
  { id: 'moneyline', label: 'Moneyline', short: 'ML', color: 'sys-blue' },
  { id: 'team_runs', label: 'Team Runs', short: 'TR', color: 'sys-green' },
  { id: 'totals_over', label: 'Totals Over', short: 'OV', color: 'sys-orange' },
  { id: 'totals_under', label: 'Totals Under', short: 'UN', color: 'sys-purple' }
]

/* ============================================================
   Atoms
   ============================================================ */

function Spinner() {
  return <span className="spinner" aria-hidden="true" />
}

function StatTile({ label, value, accent, sub, icon }) {
  return (
    <div className={`stat-tile ${accent || ''}`}>
      <div className="stat-tile-top">
        <span className="stat-tile-label">{label}</span>
        {icon && <span className="stat-tile-icon">{icon}</span>}
      </div>
      <div className="stat-tile-value">{value}</div>
      {sub && <div className="stat-tile-sub">{sub}</div>}
    </div>
  )
}

function StatusChip({ status }) {
  if (!status) return null
  const cls = `status-chip s-${status.kind}`
  const dot = status.kind === 'pending' ? '●' : status.kind === 'win' ? '✓' : status.kind === 'loss' ? '✗' : '◼'
  return (
    <span className={cls}>
      <span className="status-dot">{dot}</span>
      {status.label}
    </span>
  )
}

/* ============================================================
   Pick Card (autocontained, market-aware)
   ============================================================ */

function PickCard({ variant, signal }) {
  const data = interpret(variant, signal)
  if (!data) return null

  const colorClass = `sys-${
    variant === 'team_runs'
      ? 'green'
      : variant === 'moneyline'
      ? 'blue'
      : variant === 'totals_over'
      ? 'orange'
      : 'purple'
  }`

  return (
    <article className={`pick-card ${colorClass}`}>
      {/* Top bar: badge market + status */}
      <div className="pick-top-bar">
        <span className={`market-badge ${colorClass}`}>{data.badge}</span>
        <StatusChip status={data.status} />
      </div>

      {/* Title — protagonista */}
      <div className="pick-title-block">
        <h3 className="pick-title">{data.title}</h3>
        <p className="pick-subtitle">{data.subtitle}</p>
        {data.fullLine && <p className="pick-fullline">{data.fullLine}</p>}
      </div>

      {/* Strength tag */}
      <div className="strength-row">
        <span className={`strength-tag ${data.strengthCls}`}>
          <span className="strength-dot" />
          {data.strengthLabel}
        </span>
        <span className="tech-code" title="Código técnico de la señal">{data.techCode}</span>
      </div>

      {/* Metrics */}
      <div className="pick-metrics">
        {data.metrics.map((m) => (
          <div key={m.label} className="metric-cell">
            <span className="metric-cell-label">{m.label}</span>
            <span className="metric-cell-value">{num(m.value, m.decimals ?? 2)}</span>
          </div>
        ))}
      </div>

      {/* Objectives footer */}
      <div className="objectives">
        {data.objectives.map((o) => (
          <div key={o.label} className="objective-row">
            <span className="objective-label">{o.label}</span>
            <span className="objective-value">{o.value}</span>
          </div>
        ))}
      </div>
    </article>
  )
}

/* ============================================================
   Skeleton & Empty
   ============================================================ */

function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="sk-bar" style={{ width: '30%' }} />
      <div className="sk-bar" style={{ width: '85%', height: '24px' }} />
      <div className="sk-bar" style={{ width: '60%', height: '14px' }} />
      <div className="sk-grid">
        <div className="sk-bar" />
        <div className="sk-bar" />
        <div className="sk-bar" />
        <div className="sk-bar" />
      </div>
    </div>
  )
}

function EmptyState({ variant }) {
  const tab = TABS.find((t) => t.id === variant)
  return (
    <div className="empty-state">
      <div className={`empty-icon ${tab?.color || ''}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="9" />
          <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" />
        </svg>
      </div>
      <div className="empty-title">No hay señales {tab?.label}</div>
      <div className="empty-msg">
        El sistema no detectó oportunidades para esta categoría en la fecha seleccionada.
      </div>
    </div>
  )
}

/* ============================================================
   Main App
   ============================================================ */

export default function App() {
  const [date, setDate] = useState(todayISO())
  const [signalsData, setSignalsData] = useState(null)
  const [performance, setPerformance] = useState([])
  const [summaries, setSummaries] = useState([])

  const [loading, setLoading] = useState(false)
  const [running, setRunning] = useState(false)
  const [saving, setSaving] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [activeTab, setActiveTab] = useState('team_runs')
  const [gamesProcessed, setGamesProcessed] = useState(null)

  const loadSignals = useCallback(async (d) => {
    setLoading(true)
    setError('')
    try {
      const data = await getJson(`/propicks/signals/today?analysis_date=${d}`)
      setSignalsData(data)
      const counts = data?.counts || {}
      const tabWithMost = TABS.reduce(
        (best, t) => ((counts[t.id] || 0) > (counts[best.id] || 0) ? t : best),
        TABS[0]
      )
      if ((counts[tabWithMost.id] || 0) > 0) setActiveTab(tabWithMost.id)
    } catch (err) {
      setError(err.message || 'Error cargando señales')
      setSignalsData(null)
    } finally {
      setLoading(false)
    }
  }, [])

  const loadAuxiliary = useCallback(async () => {
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
  }, [])

  async function runDailyAnalysis() {
    setRunning(true)
    setError('')
    setSuccess('')
    try {
      const data = await postJson(`/propicks/run-daily?analysis_date=${date}`)
      const c = data?.counts || {}
      if (typeof c.games === 'number') setGamesProcessed(c.games)
      const total =
        (c.moneyline_signals ?? 0) +
        (c.team_runs_signals ?? 0) +
        (c.totals_over_signals ?? 0) +
        (c.totals_under_signals ?? 0)
      setSuccess(
        `Análisis ejecutado · ${c.games ?? 0} juegos procesados · ${total} señales generadas`
      )
      await loadSignals(date)
      await loadAuxiliary()
    } catch (err) {
      setError(err.message || 'Error ejecutando run-daily')
    } finally {
      setRunning(false)
    }
  }

  async function saveAnalysis() {
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const data = await postJson(`${SAVE_ANALYSIS_ENDPOINT}?analysis_date=${date}`)
      const off = data?.offensive_snapshots ?? data?.snapshots ?? 0
      const tr3 = data?.team_3plus_snapshots ?? 0
      const tr5 = data?.team_5plus_snapshots ?? 0
      setSuccess(
        `Análisis guardado · ${off} offensive · ${tr3} TR3 · ${tr5} TR5`
      )
    } catch (err) {
      setError(err.message || 'Error guardando análisis')
    } finally {
      setSaving(false)
    }
  }

  useEffect(() => {
    loadSignals(date)
    loadAuxiliary()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (!success) return
    const t = setTimeout(() => setSuccess(''), 6000)
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

  /* Backtest: usar el del endpoint primero. Si está vacío, fallback estático. */
  const backtestGroups = useMemo(() => {
    const apiBacktest = signalsData?.backtest
    if (Array.isArray(apiBacktest) && apiBacktest.length > 0) {
      const map = new Map()
      for (const r of apiBacktest) {
        const sid = r.system_id || 'PERFORMANCE'
        if (!map.has(sid)) map.set(sid, { system_id: sid, rows: [] })
        map.get(sid).rows.push(r)
      }
      return Array.from(map.values())
    }
    return STATIC_BACKTEST
  }, [signalsData])

  const usingFallbackBacktest =
    !signalsData?.backtest || (Array.isArray(signalsData.backtest) && signalsData.backtest.length === 0)

  const activeSignals = signals[activeTab] || []
  const anyBusy = loading || running || saving

  return (
    <div className="app">
      {/* HEADER */}
      <header className="hero">
        <div className="hero-grid">
          <div className="hero-info">
            <div className="brand-row">
              <div className="brand-mark">
                <span className="brand-dot" />
                <span className="brand-text">PROPICKS · MLB</span>
              </div>
              <span className="version-tag">{signalsData?.version || 'v1.0'}</span>
            </div>
            <h1 className="hero-title">
              Predictive <span className="hero-title-accent">Signals</span>
            </h1>
            <p className="hero-sub">
              {signalsData?.system || 'ProPicksMLB'} · 6 sistemas estadísticos · {totalSignals}{' '}
              señal{totalSignals === 1 ? '' : 'es'} activa{totalSignals === 1 ? '' : 's'}
            </p>
          </div>

          <div className="hero-controls">
            <div className="control-block">
              <label className="control-label">ANALYSIS DATE</label>
              <input
                className="date-input"
                type="date"
                value={date}
                onChange={(e) => {
                  const v = e.target.value
                  setDate(v)
                  loadSignals(v)
                }}
              />
            </div>
            <div className="action-row">
              <button
                className="btn btn-secondary"
                onClick={() => loadSignals(date)}
                disabled={anyBusy}
                title="Refresh signals"
              >
                {loading ? <Spinner /> : <span className="btn-icon">↻</span>}
                <span>{loading ? 'Loading...' : 'Refresh'}</span>
              </button>
              <button
                className="btn btn-primary"
                onClick={runDailyAnalysis}
                disabled={anyBusy}
                title="Ejecutar análisis diario completo"
              >
                {running ? <Spinner /> : <span className="btn-icon">▶</span>}
                <span>{running ? 'Running...' : 'Run Daily'}</span>
              </button>
              <button
                className="btn btn-tertiary"
                onClick={saveAnalysis}
                disabled={anyBusy}
                title="Guardar snapshot del análisis actual"
              >
                {saving ? <Spinner /> : <span className="btn-icon">⬇</span>}
                <span>{saving ? 'Saving...' : 'Save'}</span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* BANNERS */}
      {error && (
        <div className="banner banner-error">
          <span className="banner-icon">⚠</span>
          <span>
            <strong>Error:</strong> {error}
          </span>
        </div>
      )}
      {success && (
        <div className="banner banner-success">
          <span className="banner-icon">✓</span>
          <span>{success}</span>
        </div>
      )}

      {/* STAT TILES */}
      <section className="stats-row">
        <StatTile
          label="MONEYLINE"
          value={counts.moneyline ?? 0}
          accent="sys-blue"
          sub="señales activas"
          icon="ML"
        />
        <StatTile
          label="TEAM RUNS"
          value={counts.team_runs ?? 0}
          accent="sys-green"
          sub="señales activas"
          icon="TR"
        />
        <StatTile
          label="TOTALS OVER"
          value={counts.totals_over ?? 0}
          accent="sys-orange"
          sub="señales activas"
          icon="OV"
        />
        <StatTile
          label="TOTALS UNDER"
          value={counts.totals_under ?? 0}
          accent="sys-purple"
          sub="señales activas"
          icon="UN"
        />
        <StatTile
          label="TOTAL"
          value={totalSignals}
          accent="sys-cyan"
          sub={signalsData?.analysis_date || date}
          icon="Σ"
        />
        {gamesProcessed !== null && (
          <StatTile
            label="GAMES"
            value={gamesProcessed}
            accent="sys-amber"
            sub="último run-daily"
            icon="G"
          />
        )}
      </section>

      {/* DAILY SIGNALS */}
      <section className="panel">
        <div className="panel-head">
          <div className="panel-head-left">
            <div className="panel-head-icon-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12h4l3-9 4 18 3-9h4" />
              </svg>
            </div>
            <div>
              <h2 className="panel-title">Today's picks</h2>
              <p className="panel-sub">
                Señales activas · {signalsData?.analysis_date || date}
              </p>
            </div>
          </div>
          {loading && (
            <span className="loading-tag">
              <Spinner />
              Actualizando
            </span>
          )}
        </div>

        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={`tab ${activeTab === t.id ? 'active' : ''} ${t.color}`}
              onClick={() => setActiveTab(t.id)}
            >
              <span className="tab-short">{t.short}</span>
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
            <EmptyState variant={activeTab} />
          ) : (
            activeSignals.map((s, i) => (
              <PickCard
                key={s.id || s.game_pk || `${activeTab}-${i}`}
                variant={activeTab}
                signal={s}
              />
            ))
          )}
        </div>
      </section>

      {/* SYSTEM BACKTEST */}
      <section className="panel">
        <div className="panel-head">
          <div className="panel-head-left">
            <div className="panel-head-icon-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 3v18h18M7 14l4-4 4 4 5-5" />
              </svg>
            </div>
            <div>
              <h2 className="panel-title">System backtest</h2>
              <p className="panel-sub">
                Rendimiento histórico por sistema
                {usingFallbackBacktest && ' · datos estáticos de referencia'}
              </p>
            </div>
          </div>
        </div>

        <div className="backtest-grid">
          {backtestGroups.map((group) => (
            <div
              key={group.system_id}
              className={`backtest-card ${SYSTEM_COLOR[group.system_id] || 'sys-cyan'}`}
            >
              <div className="backtest-head">
                <span className="system-dot" />
                <span className="system-id">{group.system_id}</span>
              </div>
              <div className="backtest-rows">
                {group.rows.map((r, i) => (
                  <div key={i} className="bt-row">
                    <div className="bt-row-left">
                      <div className="bt-target">{r.target_metric}</div>
                      <div className="bt-meta">
                        n={r.sample_size ?? 0} · {record(r.wins, r.losses)}
                      </div>
                    </div>
                    <div className="bt-row-right">
                      <div className={`rate-pill rate-${rateClass(r.success_rate)}`}>
                        {pct(r.success_rate)}
                      </div>
                      <div className="bt-bar-track">
                        <div
                          className={`bt-bar-fill bar-${rateClass(r.success_rate)}`}
                          style={{
                            width: `${Math.max(
                              0,
                              Math.min(
                                100,
                                Number(r.success_rate) <= 1
                                  ? Number(r.success_rate) * 100
                                  : Number(r.success_rate)
                              )
                            )}%`
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* PERFORMANCE */}
      <section className="panel">
        <div className="panel-head">
          <div className="panel-head-left">
            <div className="panel-head-icon-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2v20M2 12h20" />
              </svg>
            </div>
            <div>
              <h2 className="panel-title">Performance</h2>
              <p className="panel-sub">Métricas guardadas en histórico</p>
            </div>
          </div>
        </div>

        {performance.length === 0 ? (
          <div className="mini-empty">Sin datos de performance disponibles.</div>
        ) : (
          <div className="perf-grid">
            {performance.map((row, i) => (
              <div className="perf-row" key={row.target_metric || i}>
                <div className="perf-row-left">
                  <div className="perf-target">{row.target_metric}</div>
                  <div className="perf-meta">
                    n={row.sample_size ?? 0} · {record(row.wins, row.losses)}
                  </div>
                </div>
                <div className={`rate-pill rate-${rateClass(row.success_rate)}`}>
                  {pct(row.success_rate)}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* POSTGAME SUMMARIES */}
      <section className="panel">
        <div className="panel-head">
          <div className="panel-head-left">
            <div className="panel-head-icon-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="18" rx="2" />
                <path d="M16 2v4M8 2v4M3 10h18" />
              </svg>
            </div>
            <div>
              <h2 className="panel-title">Postgame summaries</h2>
              <p className="panel-sub">
                {summaries.length > 0
                  ? `Últimos ${summaries.length} resúmenes diarios`
                  : 'Sin resúmenes disponibles'}
              </p>
            </div>
          </div>
        </div>

        {summaries.length === 0 ? (
          <div className="mini-empty">Aún no hay resúmenes postgame para mostrar.</div>
        ) : (
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
                <div className="summary-meta">{s.total_records ?? 0} análisis</div>
              </div>
            ))}
          </div>
        )}
      </section>

      <footer className="foot">
        <span>
          ProPicksMLB · Señales estadísticas · No incluye odds, cuotas ni recomendaciones de
          apuesta
        </span>
      </footer>
    </div>
  )
}

