import { useEffect, useMemo, useState, useCallback } from 'react'
import './App.css'

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  'https://mlb-predictive-systems-production.up.railway.app'

const INTERNAL_TOKEN = import.meta.env.VITE_INTERNAL_TOKEN || 'change_me'

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
  const res = await fetch(API_BASE + path, { cache: 'no-store' })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function postJson(path) {
  const res = await fetch(API_BASE + path, {
    method: 'POST',
    headers: { 'x-internal-token': INTERNAL_TOKEN },
    cache: 'no-store'
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

/* ============================================================
   Deduplicación defensiva
   ============================================================ */

function uniqueBy(items, getKey) {
  const seen = new Set()
  return (items || []).filter((item) => {
    const key = getKey(item)
    if (key === null || key === undefined) {
      const fallback = JSON.stringify(item)
      if (seen.has(fallback)) return false
      seen.add(fallback)
      return true
    }
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function moneylineKey(s) {
  if (s.analysis_snapshot_id) return `ml:${s.analysis_snapshot_id}`
  if (s.id) return `ml:id:${s.id}`
  return `ml:${s.game_pk ?? '?'}:${s.team_id ?? s.team_abbr ?? '?'}:${s.moneyline_tier ?? '?'}`
}

function teamRunsKey(s) {
  if (s.analysis_snapshot_id) return `tr:${s.analysis_snapshot_id}`
  if (s.id) return `tr:id:${s.id}`
  return `tr:${s.game_pk ?? '?'}:${s.team_id ?? s.team_abbr ?? '?'}:${s.team_runs_tier ?? '?'}`
}

function totalsOverKey(s) {
  if (s.first_analysis_snapshot_id) return `ov:${s.first_analysis_snapshot_id}`
  if (s.id) return `ov:id:${s.id}`
  return `ov:${s.game_pk ?? '?'}:${s.totals_over_tier ?? '?'}`
}

function totalsUnderKey(s) {
  if (s.first_analysis_snapshot_id) return `un:${s.first_analysis_snapshot_id}`
  if (s.id) return `un:id:${s.id}`
  return `un:${s.game_pk ?? '?'}:${s.totals_under_tier ?? '?'}`
}

function savedRowKey(r) {
  if (r.id) return `sv:id:${r.id}`
  return `sv:${r.analysis_date ?? '?'}:${r.signal_type ?? '?'}:${r.game_pk ?? '?'}:${
    r.team_id ?? r.team_abbr ?? '?'
  }:${r.tier ?? '?'}`
}

/* ============================================================
   Pick interpretation (Live)
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
    status: deriveUnderStatus(signal)
  }
}

function deriveUnderStatus(signal) {
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
   Saved row interpretation
   ============================================================ */

function savedRowVariant(row) {
  const t = (row.signal_type || '').toString().toLowerCase()
  if (t.includes('moneyline')) return 'moneyline'
  if (t.includes('team') && t.includes('run')) return 'team_runs'
  if (t.includes('over')) return 'totals_over'
  if (t.includes('under')) return 'totals_under'
  return 'team_runs'
}

function savedStatus(row) {
  const raw = (row.result_status || '').toString().toUpperCase()
  if (raw === 'WIN' || raw === 'WON' || raw === 'HIT') return { kind: 'win', label: 'Win' }
  if (raw === 'LOSS' || raw === 'LOST' || raw === 'MISS') return { kind: 'loss', label: 'Loss' }
  if (raw === 'PENDING') return { kind: 'pending', label: 'Pending' }
  if (raw === 'FINAL' || row.is_final === true) return { kind: 'final', label: 'Final' }
  return { kind: 'pending', label: 'Pending' }
}

function interpretSavedRow(row) {
  const variant = savedRowVariant(row)
  const status = savedStatus(row)
  const techCode = row.tier || row.system_id || ''
  const objectives = []
  if (row.primary_target) {
    objectives.push({ label: 'Objetivo principal', value: row.primary_target })
  }
  if (row.secondary_target) {
    objectives.push({ label: 'Objetivo secundario', value: row.secondary_target })
  }

  // Title preferido: display_label viene del backend ya formateado
  const title = row.display_label || row.title || techCode || 'Señal guardada'
  const subtitle = row.system_id ? `Sistema: ${row.system_id}` : ''

  // Métricas: pueden venir como objeto plano dentro de row.metrics
  const metricsObj = row.metrics || {}
  const metrics = Object.entries(metricsObj)
    .slice(0, 6)
    .map(([k, v]) => ({ label: k, value: v }))

  return {
    variant,
    badge: variantBadge(variant),
    title,
    subtitle,
    objectives,
    techCode,
    metrics,
    status
  }
}

function variantBadge(v) {
  if (v === 'moneyline') return 'Moneyline'
  if (v === 'team_runs') return 'Team Runs'
  if (v === 'totals_over') return 'Totals Over'
  if (v === 'totals_under') return 'Totals Under'
  return 'Signal'
}

function variantColorClass(v) {
  if (v === 'moneyline') return 'sys-blue'
  if (v === 'team_runs') return 'sys-green'
  if (v === 'totals_over') return 'sys-orange'
  if (v === 'totals_under') return 'sys-purple'
  return 'sys-cyan'
}

/* ============================================================
   Static fallback for backtest
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
  const dot =
    status.kind === 'pending'
      ? '●'
      : status.kind === 'win'
      ? '✓'
      : status.kind === 'loss'
      ? '✗'
      : '◼'
  return (
    <span className={cls}>
      <span className="status-dot">{dot}</span>
      {status.label}
    </span>
  )
}

/* ============================================================
   Pick Card (Live)
   ============================================================ */

function LivePickCard({ variant, signal }) {
  const data = interpret(variant, signal)
  if (!data) return null

  const colorClass = variantColorClass(variant)

  return (
    <article className={`pick-card ${colorClass}`}>
      <div className="pick-top-bar">
        <span className={`market-badge ${colorClass}`}>{data.badge}</span>
        <StatusChip status={data.status} />
      </div>

      <div className="pick-title-block">
        <h3 className="pick-title">{data.title}</h3>
        <p className="pick-subtitle">{data.subtitle}</p>
        {data.fullLine && <p className="pick-fullline">{data.fullLine}</p>}
      </div>

      <div className="strength-row">
        <span className={`strength-tag ${data.strengthCls}`}>
          <span className="strength-dot" />
          {data.strengthLabel}
        </span>
        <span className="tech-code" title="Código técnico de la señal">
          {data.techCode}
        </span>
      </div>

      <div className="pick-metrics">
        {data.metrics.map((m) => (
          <div key={m.label} className="metric-cell">
            <span className="metric-cell-label">{m.label}</span>
            <span className="metric-cell-value">{num(m.value, m.decimals ?? 2)}</span>
          </div>
        ))}
      </div>

      {data.objectives.length > 0 && (
        <div className="objectives">
          {data.objectives.map((o) => (
            <div key={o.label} className="objective-row">
              <span className="objective-label">{o.label}</span>
              <span className="objective-value">{o.value}</span>
            </div>
          ))}
        </div>
      )}
    </article>
  )
}

/* ============================================================
   Saved Pick Card (Official)
   ============================================================ */

function SavedPickCard({ row }) {
  const data = interpretSavedRow(row)
  const colorClass = variantColorClass(data.variant)

  return (
    <article className={`pick-card saved-card ${colorClass}`}>
      <div className="pick-top-bar">
        <div className="saved-badge-row">
          <span className={`market-badge ${colorClass}`}>{data.badge}</span>
          <span className="locked-pill" title="Señal congelada para auditoría">
            <span className="lock-icon">🔒</span> OFFICIAL
          </span>
        </div>
        <StatusChip status={data.status} />
      </div>

      <div className="pick-title-block">
        <h3 className="pick-title">{data.title}</h3>
        {data.subtitle && <p className="pick-subtitle">{data.subtitle}</p>}
      </div>

      {data.techCode && (
        <div className="strength-row">
          <span className="tech-code" title="Código técnico">
            {data.techCode}
          </span>
        </div>
      )}

      {data.metrics.length > 0 && (
        <div className="pick-metrics">
          {data.metrics.map((m) => (
            <div key={m.label} className="metric-cell">
              <span className="metric-cell-label">{m.label}</span>
              <span className="metric-cell-value">{num(m.value, 2)}</span>
            </div>
          ))}
        </div>
      )}

      {data.objectives.length > 0 && (
        <div className="objectives">
          {data.objectives.map((o) => (
            <div key={o.label} className="objective-row">
              <span className="objective-label">{o.label}</span>
              <span className="objective-value">{o.value}</span>
            </div>
          ))}
        </div>
      )}
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

function EmptyState({ variant, kind }) {
  const tab = TABS.find((t) => t.id === variant)
  const msg =
    kind === 'saved'
      ? 'No hay señales oficiales guardadas en esta categoría.'
      : 'El sistema no detectó oportunidades para esta categoría en la fecha seleccionada.'
  return (
    <div className="empty-state">
      <div className={`empty-icon ${tab?.color || ''}`}>
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
          <circle cx="12" cy="12" r="9" />
          <path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01" />
        </svg>
      </div>
      <div className="empty-title">No hay señales {tab?.label}</div>
      <div className="empty-msg">{msg}</div>
    </div>
  )
}

/* ============================================================
   Main App
   ============================================================ */

export default function App() {
  const [date, setDate] = useState(todayISO())

  // Live signals state
  const [signalsData, setSignalsData] = useState(null)

  // Saved signals state
  const [savedData, setSavedData] = useState(null)

  // Aux
  const [performance, setPerformance] = useState([])
  const [summaries, setSummaries] = useState([])

  // Loading flags
  const [loadingLive, setLoadingLive] = useState(false)
  const [loadingSaved, setLoadingSaved] = useState(false)
  const [running, setRunning] = useState(false)
  const [saving, setSaving] = useState(false)

  // Banners
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Tabs
  const [savedTab, setSavedTab] = useState('team_runs')
  const [liveTab, setLiveTab] = useState('team_runs')

  const [lastRunCounts, setLastRunCounts] = useState(null)

  /* ----------------------------------------------------------
     Carga LIVE — siempre reemplaza el estado completo.
     ---------------------------------------------------------- */
  const loadLiveSignals = useCallback(async (d) => {
    setLoadingLive(true)
    setError('')
    setSignalsData(null) // reset total
    try {
      const data = await getJson(`/propicks/signals/today?analysis_date=${d}`)
      setSignalsData(data)
    } catch (err) {
      setError(err.message || 'Error cargando live signals')
      setSignalsData(null)
    } finally {
      setLoadingLive(false)
    }
  }, [])

  /* ----------------------------------------------------------
     Carga SAVED — siempre reemplaza el estado completo.
     Si el endpoint 404 o falla, savedData queda en null
     (UI muestra estado "no hay análisis oficial").
     ---------------------------------------------------------- */
  const loadSavedSignals = useCallback(async (d) => {
    setLoadingSaved(true)
    setSavedData(null) // reset total
    try {
      const data = await getJson(`/propicks/saved-signals?analysis_date=${d}`)
      setSavedData(data)
    } catch (err) {
      // No marcamos error global porque el endpoint puede no existir aún
      // o simplemente no haber análisis guardado para esa fecha
      setSavedData(null)
    } finally {
      setLoadingSaved(false)
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
    } else {
      setPerformance([])
    }
    if (summ.status === 'fulfilled') {
      const rows = summ.value?.rows || summ.value || []
      setSummaries(Array.isArray(rows) ? rows : [])
    } else {
      setSummaries([])
    }
  }, [])

  /* ----------------------------------------------------------
     Run Daily — recalcula live signals.
     Si ya hay análisis oficial guardado, requiere force.
     ---------------------------------------------------------- */
  async function runDailyAnalysis(force = false) {
    const totalSaved = savedData?.counts?.total_saved ?? 0
    if (totalSaved > 0 && !force) {
      // Botón normal está disabled, pero por seguridad
      return
    }
    if (totalSaved > 0 && force) {
      const ok = window.confirm(
        'This will recalculate live signals and may differ from the saved official analysis. Continue?'
      )
      if (!ok) return
    }

    setRunning(true)
    setError('')
    setSuccess('')
    try {
      const data = await postJson(`/propicks/run-daily?analysis_date=${date}`)
      const c = data?.counts || {}
      setLastRunCounts(c)
      const total =
        (c.moneyline_signals ?? 0) +
        (c.team_runs_signals ?? 0) +
        (c.totals_over_signals ?? 0) +
        (c.totals_under_signals ?? 0)
      setSuccess(
        `Run Daily ejecutado · ${c.games ?? 0} juegos · ${total} señales recalculadas (live)`
      )
      await loadLiveSignals(date)
      await loadAuxiliary()
    } catch (err) {
      setError(err.message || 'Error ejecutando run-daily')
    } finally {
      setRunning(false)
    }
  }

  /* ----------------------------------------------------------
     Save Analysis — congela el análisis oficial.
     Refresca SOLO saved-signals (no toca live).
     ---------------------------------------------------------- */
  async function saveAnalysis() {
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const data = await postJson(`/propicks/save-daily-analysis?analysis_date=${date}`)
      const totalSaved =
        data?.counts?.total_saved ??
        data?.total_saved ??
        data?.saved ??
        0
      setSuccess(`Official analysis saved: ${totalSaved} signals`)
      // Refrescamos saved-signals; live queda intacto
      await loadSavedSignals(date)
    } catch (err) {
      setError(err.message || 'Error guardando análisis oficial')
    } finally {
      setSaving(false)
    }
  }

  /* Carga inicial */
  useEffect(() => {
    loadLiveSignals(date)
    loadSavedSignals(date)
    loadAuxiliary()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /* Auto-clear de mensajes de éxito */
  useEffect(() => {
    if (!success) return
    const t = setTimeout(() => setSuccess(''), 6000)
    return () => clearTimeout(t)
  }, [success])

  /* ----------------------------------------------------------
     LIVE: listas deduplicadas (única fuente de verdad).
     ---------------------------------------------------------- */
  const liveMoneyline = useMemo(
    () => uniqueBy(signalsData?.signals?.moneyline, moneylineKey),
    [signalsData]
  )
  const liveTeamRuns = useMemo(
    () => uniqueBy(signalsData?.signals?.team_runs, teamRunsKey),
    [signalsData]
  )
  const liveTotalsOver = useMemo(
    () => uniqueBy(signalsData?.signals?.totals_over, totalsOverKey),
    [signalsData]
  )
  const liveTotalsUnder = useMemo(
    () => uniqueBy(signalsData?.signals?.totals_under, totalsUnderKey),
    [signalsData]
  )

  const apiLiveCounts = signalsData?.counts || {}
  const liveCounts = {
    moneyline: liveMoneyline.length > 0 ? liveMoneyline.length : (apiLiveCounts.moneyline ?? 0),
    team_runs: liveTeamRuns.length > 0 ? liveTeamRuns.length : (apiLiveCounts.team_runs ?? 0),
    totals_over: liveTotalsOver.length > 0 ? liveTotalsOver.length : (apiLiveCounts.totals_over ?? 0),
    totals_under: liveTotalsUnder.length > 0 ? liveTotalsUnder.length : (apiLiveCounts.totals_under ?? 0)
  }
  const liveTotal =
    liveCounts.moneyline + liveCounts.team_runs + liveCounts.totals_over + liveCounts.totals_under

  /* ----------------------------------------------------------
     SAVED: rows + counts del backend, deduplicados y agrupados.
     Acepta tanto savedData.rows como savedData.signals.* .
     ---------------------------------------------------------- */
  const savedRowsAll = useMemo(() => {
    if (!savedData) return []
    let all = []
    if (Array.isArray(savedData.rows)) {
      all = savedData.rows
    } else if (savedData.signals && typeof savedData.signals === 'object') {
      // shape alternativo: { signals: { moneyline: [], team_runs: [], ... } }
      for (const key of ['moneyline', 'team_runs', 'totals_over', 'totals_under']) {
        const arr = savedData.signals[key]
        if (Array.isArray(arr)) {
          all = all.concat(
            arr.map((r) => ({ ...r, signal_type: r.signal_type || key }))
          )
        }
      }
    }
    return uniqueBy(all, savedRowKey)
  }, [savedData])

  const savedByMarket = useMemo(() => {
    const buckets = { moneyline: [], team_runs: [], totals_over: [], totals_under: [] }
    for (const r of savedRowsAll) {
      const v = savedRowVariant(r)
      if (buckets[v]) buckets[v].push(r)
    }
    return buckets
  }, [savedRowsAll])

  const savedCounts = savedData?.counts || {}
  const totalSaved =
    savedCounts.total_saved ??
    savedRowsAll.length ??
    0
  const officialMode = totalSaved > 0

  const savedAggregates = {
    pending: savedCounts.pending ?? savedRowsAll.filter((r) => savedStatus(r).kind === 'pending').length,
    wins: savedCounts.wins ?? savedRowsAll.filter((r) => savedStatus(r).kind === 'win').length,
    losses: savedCounts.losses ?? savedRowsAll.filter((r) => savedStatus(r).kind === 'loss').length,
    success_rate: savedCounts.success_rate ?? null,
    by_market: savedCounts.by_market || null,
    by_system: savedCounts.by_system || null
  }
  // Calcular success_rate si no viene
  if (savedAggregates.success_rate === null) {
    const decided = savedAggregates.wins + savedAggregates.losses
    if (decided > 0) {
      savedAggregates.success_rate = savedAggregates.wins / decided
    }
  }

  /* Auto-seleccionar tab con más señales en cada sección */
  useEffect(() => {
    if (!signalsData) return
    const tabCounts = {
      moneyline: liveMoneyline.length,
      team_runs: liveTeamRuns.length,
      totals_over: liveTotalsOver.length,
      totals_under: liveTotalsUnder.length
    }
    const best = TABS.reduce(
      (acc, t) => (tabCounts[t.id] > tabCounts[acc.id] ? t : acc),
      TABS[0]
    )
    if (tabCounts[best.id] > 0) setLiveTab(best.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [signalsData])

  useEffect(() => {
    if (!savedData) return
    const tabCounts = {
      moneyline: savedByMarket.moneyline.length,
      team_runs: savedByMarket.team_runs.length,
      totals_over: savedByMarket.totals_over.length,
      totals_under: savedByMarket.totals_under.length
    }
    const best = TABS.reduce(
      (acc, t) => (tabCounts[t.id] > tabCounts[acc.id] ? t : acc),
      TABS[0]
    )
    if (tabCounts[best.id] > 0) setSavedTab(best.id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [savedData])

  /* Backtest desde el endpoint principal; fallback estático si vacío */
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
    !signalsData?.backtest ||
    (Array.isArray(signalsData.backtest) && signalsData.backtest.length === 0)

  /* Listas activas según tabs */
  const activeLiveSignals =
    liveTab === 'moneyline'
      ? liveMoneyline
      : liveTab === 'team_runs'
      ? liveTeamRuns
      : liveTab === 'totals_over'
      ? liveTotalsOver
      : liveTotalsUnder

  const activeSavedRows = savedByMarket[savedTab] || []

  const anyBusy = loadingLive || loadingSaved || running || saving
  const showGamesTile = lastRunCounts && typeof lastRunCounts.games === 'number'

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
              {officialMode && (
                <span className="mode-tag mode-official">
                  <span className="lock-icon">🔒</span> OFFICIAL MODE
                </span>
              )}
            </div>
            <h1 className="hero-title">
              Predictive <span className="hero-title-accent">Signals</span>
            </h1>
            <p className="hero-sub">
              {signalsData?.system || 'ProPicksMLB'} · 6 sistemas estadísticos
              {officialMode
                ? ` · ${totalSaved} señal${totalSaved === 1 ? '' : 'es'} oficial${totalSaved === 1 ? '' : 'es'} guardada${totalSaved === 1 ? '' : 's'}`
                : ` · ${liveTotal} señal${liveTotal === 1 ? '' : 'es'} live`}
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
                  loadLiveSignals(v)
                  loadSavedSignals(v)
                  setLastRunCounts(null)
                }}
              />
            </div>
            <div className="action-row">
              <button
                className="btn btn-secondary"
                onClick={() => {
                  loadLiveSignals(date)
                  loadSavedSignals(date)
                }}
                disabled={anyBusy}
                title="Refresh live + saved signals"
              >
                {loadingLive || loadingSaved ? <Spinner /> : <span className="btn-icon">↻</span>}
                <span>{loadingLive || loadingSaved ? 'Loading...' : 'Refresh'}</span>
              </button>
              {officialMode ? (
                <button
                  className="btn btn-locked"
                  disabled
                  title="Run Daily bloqueado: hay análisis oficial guardado"
                >
                  <span className="btn-icon">🔒</span>
                  <span>Run Daily Locked</span>
                </button>
              ) : (
                <button
                  className="btn btn-primary"
                  onClick={() => runDailyAnalysis(false)}
                  disabled={anyBusy}
                  title="Ejecutar análisis diario (solo recalcula live signals)"
                >
                  {running ? <Spinner /> : <span className="btn-icon">▶</span>}
                  <span>{running ? 'Running...' : 'Run Daily'}</span>
                </button>
              )}
              <button
                className="btn btn-tertiary"
                onClick={saveAnalysis}
                disabled={anyBusy}
                title="Congelar el análisis oficial para auditoría"
              >
                {saving ? <Spinner /> : <span className="btn-icon">⬇</span>}
                <span>{saving ? 'Saving...' : 'Save Analysis'}</span>
              </button>
            </div>
            {officialMode && (
              <button
                className="btn-force-link"
                onClick={() => runDailyAnalysis(true)}
                disabled={anyBusy}
              >
                Force Run Daily (override)
              </button>
            )}
          </div>
        </div>
      </header>

      {/* OFFICIAL MODE BANNER */}
      {officialMode && (
        <div className="banner banner-official">
          <span className="banner-icon">🔒</span>
          <div className="banner-text">
            <strong>Official analysis saved: {totalSaved} signal{totalSaved === 1 ? '' : 's'}.</strong>{' '}
            Use Saved Analysis for audit. Live signals below may differ if Run Daily is forced again.
          </div>
        </div>
      )}

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
        {officialMode ? (
          <>
            <StatTile
              label="OFFICIAL TOTAL"
              value={totalSaved}
              accent="sys-cyan"
              sub="signals saved"
              icon="🔒"
            />
            <StatTile
              label="PENDING"
              value={savedAggregates.pending}
              accent="sys-amber"
              sub="awaiting result"
              icon="●"
            />
            <StatTile
              label="WINS"
              value={savedAggregates.wins}
              accent="sys-green"
              sub="hits"
              icon="✓"
            />
            <StatTile
              label="LOSSES"
              value={savedAggregates.losses}
              accent="sys-red"
              sub="misses"
              icon="✗"
            />
            <StatTile
              label="SUCCESS RATE"
              value={savedAggregates.success_rate !== null ? pct(savedAggregates.success_rate) : '–'}
              accent="sys-blue"
              sub="of decided"
              icon="%"
            />
            {showGamesTile && (
              <StatTile
                label="GAMES PROCESSED"
                value={lastRunCounts.games}
                accent="sys-amber"
                sub="last run-daily"
                icon="G"
              />
            )}
          </>
        ) : (
          <>
            <StatTile
              label="MONEYLINE"
              value={liveCounts.moneyline}
              accent="sys-blue"
              sub="live signals"
              icon="ML"
            />
            <StatTile
              label="TEAM RUNS"
              value={liveCounts.team_runs}
              accent="sys-green"
              sub="live signals"
              icon="TR"
            />
            <StatTile
              label="TOTALS OVER"
              value={liveCounts.totals_over}
              accent="sys-orange"
              sub="live signals"
              icon="OV"
            />
            <StatTile
              label="TOTALS UNDER"
              value={liveCounts.totals_under}
              accent="sys-purple"
              sub="live signals"
              icon="UN"
            />
            <StatTile
              label="LIVE TOTAL"
              value={liveTotal}
              accent="sys-cyan"
              sub={signalsData?.analysis_date || date}
              icon="Σ"
            />
            {showGamesTile && (
              <StatTile
                label="GAMES PROCESSED"
                value={lastRunCounts.games}
                accent="sys-amber"
                sub="last run-daily"
                icon="G"
              />
            )}
          </>
        )}
      </section>

      {/* OFFICIAL SAVED ANALYSIS — primero si existe */}
      {officialMode && (
        <section className="panel panel-official">
          <div className="panel-head">
            <div className="panel-head-left">
              <div className="panel-head-icon-box icon-box-official">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <rect x="3" y="11" width="18" height="11" rx="2" />
                  <path d="M7 11V7a5 5 0 0110 0v4" />
                </svg>
              </div>
              <div>
                <h2 className="panel-title">Official Saved Analysis</h2>
                <p className="panel-sub">
                  Señales congeladas para auditoría · {savedData?.analysis_date || date}
                </p>
              </div>
            </div>
            {loadingSaved && (
              <span className="loading-tag">
                <Spinner />
                Cargando
              </span>
            )}
          </div>

          {/* Aggregates row */}
          <div className="saved-aggregates">
            <div className="agg-cell">
              <span className="agg-label">Total saved</span>
              <span className="agg-value">{totalSaved}</span>
            </div>
            <div className="agg-cell agg-pending">
              <span className="agg-label">Pending</span>
              <span className="agg-value">{savedAggregates.pending}</span>
            </div>
            <div className="agg-cell agg-win">
              <span className="agg-label">Wins</span>
              <span className="agg-value">{savedAggregates.wins}</span>
            </div>
            <div className="agg-cell agg-loss">
              <span className="agg-label">Losses</span>
              <span className="agg-value">{savedAggregates.losses}</span>
            </div>
            <div className="agg-cell">
              <span className="agg-label">Success rate</span>
              <span className="agg-value">
                {savedAggregates.success_rate !== null ? pct(savedAggregates.success_rate) : '–'}
              </span>
            </div>
          </div>

          {/* By market / by system breakdowns if available */}
          {(savedAggregates.by_market || savedAggregates.by_system) && (
            <div className="breakdowns">
              {savedAggregates.by_market && (
                <div className="breakdown">
                  <h4 className="breakdown-title">By market</h4>
                  <div className="breakdown-rows">
                    {Object.entries(savedAggregates.by_market).map(([k, v]) => (
                      <div className="breakdown-row" key={`bm-${k}`}>
                        <span className="breakdown-label">{k}</span>
                        <span className="breakdown-value">{typeof v === 'object' ? JSON.stringify(v) : v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {savedAggregates.by_system && (
                <div className="breakdown">
                  <h4 className="breakdown-title">By system</h4>
                  <div className="breakdown-rows">
                    {Object.entries(savedAggregates.by_system).map(([k, v]) => (
                      <div className="breakdown-row" key={`bs-${k}`}>
                        <span className="breakdown-label">{k}</span>
                        <span className="breakdown-value">{typeof v === 'object' ? JSON.stringify(v) : v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="tabs">
            {TABS.map((t) => (
              <button
                key={`saved-${t.id}`}
                className={`tab ${savedTab === t.id ? 'active' : ''} ${t.color}`}
                onClick={() => setSavedTab(t.id)}
              >
                <span className="tab-short">{t.short}</span>
                <span className="tab-label">{t.label}</span>
                <span className="tab-count">{savedByMarket[t.id]?.length ?? 0}</span>
              </button>
            ))}
          </div>

          <div className="signals-grid">
            {loadingSaved ? (
              <>
                <SkeletonCard />
                <SkeletonCard />
                <SkeletonCard />
              </>
            ) : activeSavedRows.length === 0 ? (
              <EmptyState variant={savedTab} kind="saved" />
            ) : (
              activeSavedRows.map((r) => (
                <SavedPickCard key={savedRowKey(r)} row={r} />
              ))
            )}
          </div>
        </section>
      )}

      {/* LIVE SIGNALS */}
      <section className={`panel ${officialMode ? 'panel-live-secondary' : ''}`}>
        <div className="panel-head">
          <div className="panel-head-left">
            <div className="panel-head-icon-box">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12h4l3-9 4 18 3-9h4" />
              </svg>
            </div>
            <div>
              <h2 className="panel-title">
                Live Signals
                {officialMode && <span className="panel-title-tag">non-official</span>}
              </h2>
              <p className="panel-sub">
                Señales calculadas actuales · {signalsData?.analysis_date || date}
              </p>
            </div>
          </div>
          {loadingLive && (
            <span className="loading-tag">
              <Spinner />
              Actualizando
            </span>
          )}
        </div>

        <div className="live-warning">
          <span className="warn-icon">⚠</span>
          <span>Live signals can change if Run Daily is executed again.</span>
        </div>

        <div className="tabs">
          {TABS.map((t) => (
            <button
              key={`live-${t.id}`}
              className={`tab ${liveTab === t.id ? 'active' : ''} ${t.color}`}
              onClick={() => setLiveTab(t.id)}
            >
              <span className="tab-short">{t.short}</span>
              <span className="tab-label">{t.label}</span>
              <span className="tab-count">{liveCounts[t.id] ?? 0}</span>
            </button>
          ))}
        </div>

        <div className="signals-grid">
          {loadingLive ? (
            <>
              <SkeletonCard />
              <SkeletonCard />
              <SkeletonCard />
            </>
          ) : activeLiveSignals.length === 0 ? (
            <EmptyState variant={liveTab} kind="live" />
          ) : (
            activeLiveSignals.map((s) => {
              const key =
                liveTab === 'moneyline'
                  ? moneylineKey(s)
                  : liveTab === 'team_runs'
                  ? teamRunsKey(s)
                  : liveTab === 'totals_over'
                  ? totalsOverKey(s)
                  : totalsUnderKey(s)
              return <LivePickCard key={key} variant={liveTab} signal={s} />
            })
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
                  <div key={`${group.system_id}-${r.target_metric ?? i}`} className="bt-row">
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
              <div className="perf-row" key={`perf-${row.target_metric ?? i}`}>
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
              <div className="summary-tile" key={`summ-${s.summary_date ?? i}`}>
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
          ProPicksMLB · Señales estadísticas · Saved Analysis = oficial · Live Signals = recalculables
        </span>
      </footer>
    </div>
  )
}
