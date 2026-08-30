import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import {
  Activity, ArrowRight, Ban, BarChart3, BookMarked, ChevronDown, ChevronRight,
  Database, Edit2, Filter, GitCompare, Globe, Home, LayoutDashboard, Layers, Plus,
  RefreshCw, Search, Settings2, Shield, TableProperties, Tag,
  Trash2, TrendingUp, User, Users, X
} from 'lucide-react'
import MasterSubmodule, { SectorsPage, TickersPage, WatchlistsPage, UsersPage, AlternativeNamesPage, ExcludedTickersPage } from './master/index.jsx'
import './styles.css'

// ─── Constants ───────────────────────────────────────────────────────────────
const groupIcon = {
  Calls: Activity, Scanners: TrendingUp, 'Technical Scanners': TrendingUp,
  'Fundamental Analysis': BarChart3, 'Shared cache': Database, 'Raw data': Database,
  Sectors: BarChart3, 'Sectorial Views': BarChart3, 'Delivery spikes': Activity,
  Reference: BookMarked, Analysis: BarChart3, 'Data tables': TableProperties,
  Derivative: Layers, DERIVATIVE: Layers,
}

const apps = {
  rawdata: {
    title: 'Raw Data', eyebrow: 'RAW DATA EXPLORER',
    description: 'Inspect source market data, technical indicators, fundamentals and master reference tables.',
    database: 'bsa_db', accent: 'Source tables',
  },
  intelligence: {
    title: 'Market Intelligence', eyebrow: 'BSA MARKET INTELLIGENCE',
    description: 'Explore generated calls, scanner outputs, sector analysis and delivery signals.',
    database: 'bsa_db', accent: 'Analysis sources',
  },
}

const cleanTicker = val => typeof val === 'string' ? val.replace(/\.(NS|BO)$/i, '') : val

const format = (value, key = '') => {
  if (value === null || value === undefined) return '—'
  if (key === 'ticker' || key === 'symbol') return cleanTicker(value)
  if (Array.isArray(value)) return value.map(cleanTicker).join(', ') || '—'
  if (typeof value === 'boolean') return value ? '✓ Yes' : '✗ No'
  if (typeof value === 'number') {
    if (key.includes('market_cap')) return `₹${new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(value)} Cr`
    return key.includes('ratio') || key.includes('confidence') || key.includes('change') || key.includes('deviation')
      ? `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
      : value.toLocaleString('en-IN')
  }
  return String(value)
}

const getSignalClass = (val) => {
  if (!val) return 'neutral'
  const v = String(val).toUpperCase()
  if (v.includes('BUY') || v === 'BULLISH' || v === 'POSITIVE' || v === 'ACCUMULATION') return 'buy'
  if (v.includes('SELL') || v === 'BEARISH' || v === 'NEGATIVE' || v === 'DISTRIBUTION') return 'sell'
  return 'neutral'
}

const signalTone = value => {
  if (typeof value !== 'string') return 'neutral'
  const v = value.trim().toUpperCase()
  if (v.includes('STRONG BUY') || v.includes('STRONG_BULLISH') || v === 'BETTER') return 'strong-buy'
  if (v.includes('STRONG SELL') || v.includes('STRONG_BEARISH') || v === 'BAD') return 'strong-sell'
  if (v.includes('BUY') || v === 'BULLISH' || v === 'POSITIVE' || v === 'ACCUMULATION' || v === 'GOOD') return 'buy'
  if (v.includes('SELL') || v === 'BEARISH' || v === 'NEGATIVE' || v === 'DISTRIBUTION') return 'sell'
  return 'neutral'
}

// Master page identifiers
const MASTER_PAGES = ['master:sectors', 'master:tickers', 'master:watchlists', 'master:users', 'master:aliases', 'master:excluded']

const parseResp = async (r) => {
  const ct = r.headers.get('content-type') || ''
  if (!ct.includes('application/json')) {
    const text = await r.text()
    throw new Error(r.ok ? 'Invalid response format received from server.' : `HTTP ${r.status}: ${text.slice(0, 100)}`)
  }
  return r.json()
}
const api = {
  get: async (url) => { const r = await fetch(url); if (!r.ok) { const e = await parseResp(r); throw new Error(e.detail || r.statusText) } return parseResp(r) },
  post: async (url, body) => { const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); if (!r.ok) { const e = await parseResp(r); throw new Error(e.detail || r.statusText) } return parseResp(r) },
  put: async (url, body) => { const r = await fetch(url, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }); if (!r.ok) { const e = await parseResp(r); throw new Error(e.detail || r.statusText) } return parseResp(r) },
  del: async (url) => { const r = await fetch(url, { method: 'DELETE' }); if (!r.ok && r.status !== 204) { const e = await parseResp(r); throw new Error(e.detail || r.statusText) } return true },
}


// ─── Shared UI components ─────────────────────────────────────────────────────
function Modal({ title, onClose, children }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <h3>{title}</h3>
          <button className="icon-btn" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

function Toast({ message, type = 'success', onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t) }, [])
  return <div className={`toast toast-${type}`}>{message}</div>
}

function useToast() {
  const [toast, setToast] = useState(null)
  const show = (message, type = 'success') => setToast({ message, type, key: Date.now() })
  const hide = () => setToast(null)
  const ToastEl = toast ? <Toast key={toast.key} message={toast.message} type={toast.type} onClose={hide} /> : null
  return { show, ToastEl }
}

// ─── Theme Selector Component ─────────────────────────────────────────
function ThemeSelector({ currentTheme, onSelectTheme }) {
  const themes = [
    { id: 'blue', label: 'Classic Blue', color: '#4e8bff', bg: '#09111f' },
    { id: 'green', label: 'Forest Green', color: '#3eb47a', bg: '#081710' },
    { id: 'warm', label: 'Warm Earth', color: '#d48e46', bg: '#18130e' },
    { id: 'hacker', label: 'Hacker Terminal', color: '#00ff66', bg: '#020c05' },
  ]

  return (
    <div className="theme-selector">
      <span className="theme-selector-label">Theme:</span>
      <div className="theme-selector-options">
        {themes.map(t => (
          <button
            key={t.id}
            onClick={() => onSelectTheme(t.id)}
            className={`theme-btn ${currentTheme === t.id ? 'active' : ''}`}
            style={{
              '--btn-color': t.color,
              '--btn-bg': t.bg,
            }}
          >
            <span className="theme-dot" style={{ background: t.color }} />
            <span>{t.label}</span>
          </button>
        ))}
      </div>
    </div>
  )
}

// ─── Landing page ─────────────────────────────────────────────────────────────
function Landing({ theme, setTheme }) {
  return (
    <div className="landing">
      <header className="landing-header">
        <div className="brand" style={{ gap: 12 }}>
          <img src="/BSA.png" alt="BSA Logo" style={{ height: 38, width: 'auto', borderRadius: 6 }} />
          <div><b>BSA Data Portal</b><small>POSTGRESQL APPLICATIONS</small></div>
        </div>
        <ThemeSelector currentTheme={theme} onSelectTheme={setTheme} />
      </header>
      <main className="landing-main">
        <div className="landing-logo-wrap">
          <img src="/BSA.png" alt="BSA Logo" className="landing-logo" />
        </div>
        <p className="eyebrow portal-title-highlight">BSA MARKET INTELLIGENCE PORTAL</p>
        <h1>Indian Stock Market Screener & Analysis</h1>
        <p className="landing-copy">Access institutional trade calls, technical scanners, delivery volume spikes, and cash flow fundamental metrics across Nifty tickers.</p>
        <div className="app-cards">
          {Object.entries(apps).filter(([key]) => key === 'intelligence').map(([key, item]) => (
            <a className={`app-card ${key}`} href={`/${key}`} key={key}>
              <h2>{item.title}</h2>
              <p>Explore real-time trade signals, historical calls, multi-factor technical scanners, and cash flow fundamentals.</p>
              <b>Launch Intelligence Portal <ArrowRight size={16} /></b>
            </a>
          ))}
        </div>

      </main>
    </div>
  )
}



// ─── Main App Component ───────────────────────────────────────────────────────
function App() {
  const [path, setPath] = useState(() => window.location.pathname.replace(/^\/|\/$/g, ''))
  const [theme, setTheme] = useState(() => localStorage.getItem('bsa_theme') || 'blue')

  useEffect(() => {
    document.body.setAttribute('data-theme', theme)
    localStorage.setItem('bsa_theme', theme)
  }, [theme])

  useEffect(() => {
    const handlePopState = () => setPath(window.location.pathname.replace(/^\/|\/$/g, ''))
    window.addEventListener('popstate', handlePopState)
    return () => window.removeEventListener('popstate', handlePopState)
  }, [])

  if (path === '') {
    return <Landing theme={theme} setTheme={setTheme} />
  }


  const dataset = path === 'intelligence' ? 'intelligence' : 'rawdata'
  const appInfo = apps[dataset]

  const apiBase = `/api/${dataset}`

  const [catalog, setCatalog] = useState([])
  const [overview, setOverview] = useState(null)
  const [dbInfo, setDbInfo] = useState(null)
  const [active, setActive] = useState('dashboard')
  const [data, setData] = useState(null)
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [sectorSummary, setSectorSummary] = useState([])
  const [activeSector, setActiveSector] = useState(null)
  const [sectorScanTable, setSectorScanTable] = useState('operatorfootprint')
  const [sectorData, setSectorData] = useState(null)
  const [expandedSection, setExpandedSection] = useState(null)

  const load = async (tableName = active, search = query) => {
    setLoading(true)
    setError('')
    try {
      const q = search ? `&search=${encodeURIComponent(search)}` : ''
      const res = await api.get(`${apiBase}/tables/${tableName}?limit=100${q}`)
      setData(res)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }


  const refreshDashboard = async () => {
    setError('')
    try {
      const [c, o, d] = await Promise.all([
        fetch(`${apiBase}/catalog`), fetch(`${apiBase}/overview`), fetch(`${apiBase}/database-info`),
      ])
      const cat = await c.json(), details = await d.json()
      if (!c.ok) throw new Error(cat.detail)
      if (!d.ok) throw new Error(details.detail)
      setCatalog(cat); setOverview(await o.json()); setDbInfo(details)
    } catch (e) { setError(e.message) }

    // Load sector summary for intelligence
    if (dataset === 'intelligence') {
      try { const s = await api.get('/api/master/sectors-summary'); setSectorSummary(s) } catch (_) {}
    }
  }

  const loadSectorData = async (sectorName, scanTable) => {
    try {
      const res = await api.get(`/api/intelligence/sector/${encodeURIComponent(sectorName)}/scans?scan_table=${scanTable}`)
      setSectorData(res)
    } catch (e) { setError(e.message) }
  }

  useEffect(() => { refreshDashboard() }, [dataset])
  useEffect(() => {
    if (active !== 'dashboard' && !MASTER_PAGES.includes(active) && !active.startsWith('sector:')) {
      load(active, '')
    }
    if (active.startsWith('sector:')) {
      const sName = active.replace('sector:', '')
      setActiveSector(sName)
      loadSectorData(sName, sectorScanTable)
    }
  }, [active])

  const grouped = useMemo(() =>
    catalog.reduce((acc, item) => ({ ...acc, [item.group]: [...(acc[item.group] || []), item] }), {}),
    [catalog]
  )
  const current = catalog.find(item => item.name === active)

  // Synchronize expanded section with active route / selection
  useEffect(() => {
    if (active.startsWith('master:')) {
      setExpandedSection('Master Data')
    } else if (active.startsWith('sector:')) {
      setExpandedSection('By Sector')
    } else {
      const match = catalog.find(c => c.name === active)
      if (match) {
        setExpandedSection(match.group)
      } else if (catalog.length > 0 && !expandedSection) {
        setExpandedSection(grouped['Raw data'] ? 'Raw data' : (grouped['Calls'] ? 'Calls' : 'Master Data'))
      }
    }
  }, [active, catalog, grouped])

  const toggleSection = (groupName) => {
    setExpandedSection(prev => prev === groupName ? null : groupName)
  }

  const handleSectorScanChange = (t) => { setSectorScanTable(t); if (activeSector) loadSectorData(activeSector, t) }

  const handleMasterNav = (sub) => setActive(`master:${sub}`)

  return (
    <div className="app-shell">
      <aside>
        <div className="brand">
          <span className="brand-mark">B</span>
          <div><b>{appInfo.title}</b><small>{appInfo.database.toUpperCase()}</small></div>
        </div>
        <nav>
          <a className="nav-item" href="/"><Home /> Portal home</a>
          <button className={`nav-item ${active === 'dashboard' ? 'selected' : ''}`} onClick={() => setActive('dashboard')}>
            <LayoutDashboard /> Overview
          </button>

          {/* Navigation sections ordered: RAW DATA -> MASTER DATA -> CALLS -> DERIVATIVE -> Other catalog sections */}
          {(() => {
            const orderedGroups = []
            if (grouped['Raw data']) orderedGroups.push('Raw data')
            orderedGroups.push('Master Data')
            if (grouped['Calls']) orderedGroups.push('Calls')
            if (grouped['Derivative']) orderedGroups.push('Derivative')
            Object.keys(grouped).forEach(g => {
              if (g !== 'Raw data' && g !== 'Calls' && g !== 'Derivative') {
                orderedGroups.push(g)
              }
            })

            return orderedGroups.map(group => {
              const isExpanded = expandedSection === group
              if (group === 'Master Data') {
                return (
                  <section key="Master Data" className={`nav-section ${isExpanded ? 'expanded' : 'collapsed'}`}>
                    <div className="nav-label" onClick={() => toggleSection('Master Data')} role="button" tabIndex={0}>
                      <Settings2 />
                      <span style={{ flex: 1 }}>Master Data</span>
                      {isExpanded ? <ChevronDown size={14} className="chevron" /> : <ChevronRight size={14} className="chevron" />}
                    </div>
                    {isExpanded && (
                      <div className="nav-section-items">
                        <button className={`nav-item ${active === 'master:sectors' ? 'selected' : ''}`} onClick={() => setActive('master:sectors')}><Tag /> Sectors</button>
                        <button className={`nav-item ${active === 'master:tickers' ? 'selected' : ''}`} onClick={() => setActive('master:tickers')}><Globe /> Ticker Master</button>
                        <button className={`nav-item ${active === 'master:watchlists' ? 'selected' : ''}`} onClick={() => setActive('master:watchlists')}><BookMarked /> Watchlists</button>
                        <button className={`nav-item ${active === 'master:users' ? 'selected' : ''}`} onClick={() => setActive('master:users')}><Users /> Users</button>
                        <button className={`nav-item ${active === 'master:aliases' ? 'selected' : ''}`} onClick={() => setActive('master:aliases')}><GitCompare /> Alternative Names</button>
                        <button className={`nav-item ${active === 'master:excluded' ? 'selected' : ''}`} onClick={() => setActive('master:excluded')}><Ban /> Excluded Tickers</button>
                      </div>
                    )}
                  </section>
                )
              }

              const items = grouped[group]
              if (!items || items.length === 0) return null
              const Icon = groupIcon[group] || TableProperties
              return (
                <section key={group} className={`nav-section ${isExpanded ? 'expanded' : 'collapsed'}`}>
                  <div className="nav-label" onClick={() => toggleSection(group)} role="button" tabIndex={0}>
                    <Icon />
                    <span style={{ flex: 1 }}>{group}</span>
                    {isExpanded ? <ChevronDown size={14} className="chevron" /> : <ChevronRight size={14} className="chevron" />}
                  </div>
                  {isExpanded && (
                    <div className="nav-section-items">
                      {items.map(item => (
                        <button key={item.name} className={`nav-item ${active === item.name ? 'selected' : ''}`} onClick={() => { setQuery(''); setActive(item.name); }}>
                          {item.label}
                        </button>
                      ))}
                    </div>
                  )}
                </section>
              )
            })
          })()}
        </nav>
        <div className="connection">
          <i className={error ? 'offline' : ''} />
          {error ? 'Database unavailable' : 'PostgreSQL connected'}
        </div>
      </aside>

      <main>
        {!MASTER_PAGES.includes(active) && (
          <header>
            <div>
              <p className="eyebrow">{appInfo.eyebrow}</p>
              <h1>
                {active === 'dashboard' ? `${appInfo.title} overview`
                  : active.startsWith('sector:') ? `Sector: ${activeSector}`
                  : current?.label || active}
              </h1>
              <p className="subhead">
                {active === 'dashboard' ? appInfo.description
                  : active.startsWith('sector:') ? `Intelligence data filtered to ${activeSector} tickers`
                  : `${data?.total ?? '—'} records · Latest rows first`}
              </p>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <ThemeSelector currentTheme={theme} onSelectTheme={setTheme} />
              <button className="refresh" onClick={() => active === 'dashboard' ? refreshDashboard() : load()}>
                <RefreshCw size={16} /> Refresh
              </button>
            </div>
          </header>

        )}


        {active === 'dashboard' && <Dashboard apiBase={apiBase} setActive={setActive} />}
        {active.startsWith('master:') && (
          <MasterSubmodule subView={active.replace('master:', '')} onNavigate={handleMasterNav} />
        )}
        {active.startsWith('sector:') && (
          <SectorIntelligencePage
            sectorName={activeSector}
            data={sectorData}
            scanTable={sectorScanTable}
            onScanTableChange={handleSectorScanChange}
          />
        )}
        {!MASTER_PAGES.includes(active) && !active.startsWith('sector:') && active !== 'dashboard' && (
          <TableView data={data} loading={loading} error={error} query={query} setQuery={setQuery} onSearch={() => load()} />
        )}
      </main>
    </div>
  )
}

// ─── Dashboard ────────────────────────────────────────────────────────────────
function Dashboard({ apiBase, setActive }) {
  const [trades, setTrades] = useState([])
  const [loading, setLoading] = useState(true)
  const [sortKey, setSortKey] = useState('rank')
  const [sortAsc, setSortAsc] = useState(true)

  useEffect(() => {
    fetch(`${apiBase}/top-trades`)
      .then(r => r.json())
      .then(d => { setTrades(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [apiBase])

  const handleSort = key => {
    setSortAsc(k => sortKey === key ? !sortAsc : true)
    setSortKey(key)
  }

  const sortedTrades = useMemo(() => {
    if (!sortKey) return trades
    return [...trades].sort((a, b) => {
      const valA = a[sortKey] ?? ''
      const valB = b[sortKey] ?? ''
      if (typeof valA === 'number' && typeof valB === 'number') {
        return (valA - valB) * (sortAsc ? 1 : -1)
      }
      return String(valA).localeCompare(String(valB), undefined, { numeric: true }) * (sortAsc ? 1 : -1)
    })
  }, [trades, sortKey, sortAsc])

  return (
    <div className="top-trades-dashboard">
      <section className="panel data-panel">
        <div className="panel-heading" style={{ padding: '12px 18px', borderBottom: '1px solid rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <span style={{ background: 'rgba(126,200,240,0.15)', color: '#7ec8f0', padding: '3px 8px', borderRadius: 4, fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>
              MARKET INTELLIGENCE
            </span>
            <h2 style={{ fontSize: 16, margin: 0, color: '#fff', fontWeight: 700 }}>
              Top 15 Best Trade Opportunities
            </h2>
          </div>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th onClick={() => handleSort('rank')} style={{ cursor: 'pointer', width: 60 }}># Rank</th>
                <th onClick={() => handleSort('ticker')} style={{ cursor: 'pointer' }}>Ticker & Stock Name</th>
                <th onClick={() => handleSort('sector')} style={{ cursor: 'pointer' }}>Sector</th>
                <th onClick={() => handleSort('current_price')} style={{ cursor: 'pointer' }}>Current Price (LTP)</th>
                <th>Best Buy Zone</th>
                <th onClick={() => handleSort('stop_loss')} style={{ cursor: 'pointer' }}>Stop Loss (SL)</th>
                <th onClick={() => handleSort('target_price')} style={{ cursor: 'pointer' }}>Target (T1 / T2)</th>
                <th onClick={() => handleSort('risk_reward')} style={{ cursor: 'pointer' }}>Risk : Reward</th>
                <th onClick={() => handleSort('setup_signal')} style={{ cursor: 'pointer' }}>Setup Signal</th>
                <th>Trade Insight & Technical Rationale</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={10}><div className="state">Analyzing market intelligence & generating top 15 trades…</div></td></tr>}
              {!loading && sortedTrades.map(t => (
                <tr key={t.ticker} className="data-row">
                  <td style={{ fontWeight: 700, color: '#7ec8f0' }}>#{t.rank}</td>
                  <td>
                    <div>
                      <b style={{ color: '#fff', fontSize: 14, fontFamily: "'DM Mono'" }}>{t.ticker}</b>
                      <div style={{ fontSize: 12, color: '#94a3b8' }}>{t.stock_name}</div>
                    </div>
                  </td>
                  <td><span style={{ fontSize: 12, color: '#cbd5e1' }}>{t.sector}</span></td>
                  <td><b style={{ color: '#e2e8f0' }}>₹{t.current_price.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</b></td>
                  <td>
                    <span style={{ background: 'rgba(82, 196, 26, 0.15)', color: '#52c41a', padding: '3px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600 }}>
                      ₹{t.best_buy_zone}
                    </span>
                  </td>
                  <td>
                    <span style={{ background: 'rgba(255, 77, 79, 0.15)', color: '#ff4d4f', padding: '3px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600 }}>
                      ₹{t.stop_loss.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                    </span>
                  </td>
                  <td>
                    <div>
                      <b style={{ color: '#52c41a' }}>₹{t.target_price.toLocaleString('en-IN')}</b>
                      {t.target_price2 && <span style={{ fontSize: 11, color: '#94a3b8', marginLeft: 4 }}>(T2: ₹{t.target_price2.toLocaleString('en-IN')})</span>}
                    </div>
                  </td>
                  <td><span className="status-badge buy" style={{ fontSize: 11 }}>{t.risk_reward}</span></td>
                  <td><span className="badge buy">{t.setup_signal}</span></td>
                  <td style={{ color: '#cbd5e1', fontSize: 12, maxWidth: 320, lineHeight: 1.4 }}>{t.insight}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}


// Helper to identify internal timestamp / audit date fields to omit from display
const isInternalTimestamp = key =>
  /timestamp|run_time|runtime|created_at|updated_at|analysed_at|fetched_date|review_date/i.test(key)

// Helper to reorder table columns: Ticker -> Signal/Call -> Record Id -> remaining cols,
// positioning fundamental score immediately after AVG PAT / PAT column.
const reorderColumns = (cols) => {
  const tickerCol = cols.find(c => c === 'ticker' || c === 'symbol')
  const signalCol = cols.find(c => /signal|call|recommended_call|status|phase/i.test(c) && c !== 'record_id')
  const dateCol = cols.find(c => c === 'record_id')

  const ordered = []
  if (tickerCol) ordered.push(tickerCol)
  if (signalCol) ordered.push(signalCol)
  if (dateCol) ordered.push(dateCol)

  cols.forEach(c => {
    if (!ordered.includes(c)) ordered.push(c)
  })

  // Move fundamental score right after AVG PAT column if both exist
  const patIndex = ordered.findIndex(c => /^pat$|avg_pat|pat_/i.test(c))
  const scoreIndex = ordered.findIndex(c => /^score$|fundamental_score|scorecard/i.test(c) && c !== 'record_id')

  if (patIndex !== -1 && scoreIndex !== -1 && patIndex !== scoreIndex) {
    const scoreCol = ordered[scoreIndex]
    ordered.splice(scoreIndex, 1)
    const newPatIndex = ordered.findIndex(c => /^pat$|avg_pat|pat_/i.test(c))
    ordered.splice(newPatIndex + 1, 0, scoreCol)
  }

  return ordered
}

// ─── Generic table view ───────────────────────────────────────────────────────
function TableView({ data, loading, error, query, setQuery, onSearch }) {
  const [sort, setSort] = useState({ key: '', asc: true })
  const [selectedSignal, setSelectedSignal] = useState('ALL')
  const [selectedSector, setSelectedSector] = useState('ALL')

  const displayColumns = useMemo(() => {
    if (!data?.columns) return []
    // Keep id/run_time/uniqueid for transformation into "record_id"
    let cols = data.columns.filter(col => {
      if (col === 'id' || col === 'run_time' || col.toLowerCase() === 'uniqueid') return true
      return !isInternalTimestamp(col)
    })

    // Map id, run_time, or uniqueid to "record_id"
    cols = cols.map(c => (c === 'id' || c === 'run_time' || c.toLowerCase() === 'uniqueid') ? 'record_id' : c)

    // Ensure unique column names
    cols = Array.from(new Set(cols))

    return reorderColumns(cols)
  }, [data])

  // Extract distinct sectors available in dataset
  const availableSectors = useMemo(() => {
    if (!data?.rows) return []
    const sectors = new Set()
    data.rows.forEach(r => {
      if (r.sector && typeof r.sector === 'string' && r.sector.trim()) {
        sectors.add(r.sector.trim())
      }
    })
    return Array.from(sectors).sort()
  }, [data?.rows])

  // Reset filters on table view / dataset switch
  useEffect(() => {
    setSelectedSignal('ALL')
    setSelectedSector('ALL')
  }, [data?.table])

  const isCashFlowTable = data?.table === 'cash_flow_summary'

  const sortBy = key => {
    const origKey = (key === 'record_id') ? (data?.columns?.includes('uniqueid') ? 'uniqueid' : data?.columns?.includes('run_time') ? 'run_time' : 'id') : key
    setSort(prev => ({
      key: origKey,
      asc: prev.key === origKey ? !prev.asc : true,
    }))
  }

  const rows = useMemo(() => {
    if (!data) return []
    let list = [...data.rows]
    if (selectedSignal && selectedSignal !== 'ALL') {
      list = list.filter(row => {
        const sigCol = displayColumns.find(c => /signal|call|recommended_call|status|phase/i.test(c) && c !== 'record_id')
        if (!sigCol) return true
        const val = String(row[sigCol] ?? '').trim().toLowerCase()
        const target = selectedSignal.toLowerCase()
        return val === target || (target === 'buy' && val === 'bullish') || (target === 'sell' && val === 'bearish') || (target === 'strong buy' && val === 'strong_bullish') || (target === 'strong sell' && val === 'strong_bearish')
      })
    }
    if (selectedSector && selectedSector !== 'ALL') {
      list = list.filter(row => String(row.sector ?? '').trim().toLowerCase() === selectedSector.toLowerCase())
    }
    if (sort.key) {
      list.sort((a, b) => {
        const valA = a[sort.key] ?? ''
        const valB = b[sort.key] ?? ''
        if (typeof valA === 'number' && typeof valB === 'number') {
          return (valA - valB) * (sort.asc ? 1 : -1)
        }
        return String(valA).localeCompare(String(valB), undefined, { numeric: true }) * (sort.asc ? 1 : -1)
      })
    }
    return list
  }, [data, sort, selectedSignal, selectedSector, displayColumns])

  const hasSignalCol = useMemo(() => {
    return displayColumns.some(c => /signal|call|recommended_call|status|phase/i.test(c) && c !== 'record_id')
  }, [displayColumns])

  const handleFilterClick = filterVal => {
    if (selectedSignal === filterVal) {
      setSelectedSignal('ALL')
    } else {
      setSelectedSignal(filterVal)
    }
  }

  const formatRecordIdDate = val => {
    if (!val) return '—'
    let s = String(val).trim()
    if (/^\d{12}$/.test(s) || /^\d{6}$/.test(s)) {
      const yy = s.slice(0, 2), mm = s.slice(2, 4), dd = s.slice(4, 6)
      return `${dd}-${mm}-${yy}`
    }
    if (/^\d{10,}$/.test(s)) {
      const d = new Date(Number(s) * (s.length === 10 ? 1000 : 1))
      if (!isNaN(d.getTime())) {
        const dd = String(d.getDate()).padStart(2, '0')
        const mm = String(d.getMonth() + 1).padStart(2, '0')
        const yy = String(d.getFullYear()).slice(-2)
        return `${dd}-${mm}-${yy}`
      }
    }
    const d = new Date(s)
    if (!isNaN(d.getTime())) {
      const dd = String(d.getDate()).padStart(2, '0')
      const mm = String(d.getMonth() + 1).padStart(2, '0')
      const yy = String(d.getFullYear()).slice(-2)
      return `${dd}-${mm}-${yy}`
    }
    return s
  }

  return (
    <section className="panel data-panel">
      <div className="toolbar" style={{ flexWrap: 'wrap', gap: 12 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', flex: 1 }}>
          <div className="search">
            <Search size={17} />
            <input value={query} onChange={e => setQuery(e.target.value)} onKeyDown={e => e.key === 'Enter' && onSearch()} placeholder="Search ticker, sector, signal…" />
            <button onClick={onSearch}>Search</button>
          </div>

          {availableSectors.length > 0 && (
            <div className="sector-filter-wrap" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <Filter size={15} style={{ color: '#7ec8f0' }} />
              <select
                className="sector-select"
                value={selectedSector}
                onChange={e => setSelectedSector(e.target.value)}
                style={{
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.15)',
                  color: '#e1e6ed',
                  borderRadius: 6,
                  padding: '6px 12px',
                  fontSize: 13,
                  fontWeight: 500,
                  outline: 'none',
                  cursor: 'pointer',
                }}
              >
                <option value="ALL" style={{ background: '#1a202c', color: '#fff' }}>All Sectors ({availableSectors.length})</option>
                {availableSectors.map(sec => (
                  <option key={sec} value={sec} style={{ background: '#1a202c', color: '#fff' }}>
                    {sec}
                  </option>
                ))}
              </select>
            </div>
          )}

          {hasSignalCol && (
            <div className="filter-bar">
              <button className={`filter-btn ${selectedSignal === 'ALL' ? 'active' : ''}`} onClick={() => setSelectedSignal('ALL')}>All</button>
              {isCashFlowTable ? (
                <>
                  <button className={`filter-btn sell ${selectedSignal === 'Bad' ? 'active' : ''}`} onClick={() => handleFilterClick('Bad')}>Bad</button>
                  <button className={`filter-btn buy ${selectedSignal === 'Good' ? 'active' : ''}`} onClick={() => handleFilterClick('Good')}>Good</button>
                  <button className={`filter-btn strong-buy ${selectedSignal === 'Better' ? 'active' : ''}`} onClick={() => handleFilterClick('Better')}>Better</button>
                </>
              ) : (
                <>
                  <button className={`filter-btn strong-buy ${selectedSignal === 'Strong Buy' ? 'active' : ''}`} onClick={() => handleFilterClick('Strong Buy')}>Strong Buy</button>
                  <button className={`filter-btn buy ${selectedSignal === 'Buy' ? 'active' : ''}`} onClick={() => handleFilterClick('Buy')}>Buy</button>
                  <button className={`filter-btn neutral ${selectedSignal === 'Neutral' ? 'active' : ''}`} onClick={() => handleFilterClick('Neutral')}>Neutral</button>
                  <button className={`filter-btn sell ${selectedSignal === 'Sell' ? 'active' : ''}`} onClick={() => handleFilterClick('Sell')}>Sell</button>
                  <button className={`filter-btn strong-sell ${selectedSignal === 'Strong Sell' ? 'active' : ''}`} onClick={() => handleFilterClick('Strong Sell')}>Strong Sell</button>
                </>
              )}
            </div>
          )}

        </div>
        <span>{displayColumns.length} columns</span>
      </div>

      {loading && <div className="state">Loading data…</div>}
      {error && <div className="state error">{error}</div>}
      {!loading && !error && data && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {displayColumns.map(key => {
                  const origKey = (key === 'record_id') ? (data?.columns?.includes('uniqueid') ? 'uniqueid' : data?.columns?.includes('run_time') ? 'run_time' : 'id') : key
                  return (
                    <th key={key} onClick={() => sortBy(key)} style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}>
                      {key.replaceAll('_', ' ')} {sort.key === origKey && (sort.asc ? '↑' : '↓')}
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={index}>
                  {displayColumns.map(key => {
                    const origKey = (key === 'record_id') ? (row.uniqueid ? 'uniqueid' : row.run_time ? 'run_time' : 'id') : key
                    const value = row[origKey] ?? row[key]

                    const badge = typeof value === 'string' && /signal|call|status|phase|spike|bet/.test(key) && key !== 'record_id'
                    if (key === 'ticker') {
                      return <td key={key}><b style={{ color: '#7ec8f0', fontFamily: "'DM Mono'" }}>{cleanTicker(value)}</b></td>
                    }
                    if (key === 'record_id') {
                      return <td key={key}>{formatRecordIdDate(value)}</td>
                    }
                    return <td key={key}>{badge ? <span className={`badge ${signalTone(value)}`}>{format(value, key)}</span> : format(value, key)}</td>
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          {!rows.length && <div className="state">No matching rows.</div>}
        </div>
      )}
    </section>
  )
}

// ─── Sector Intelligence Page ─────────────────────────────────────────────────
const SCAN_TABLES = ['operatorfootprint', 'breakout', 'trend_trading', 'reversal_trading', 'swinger', 'support_resistance', 'quicktrade_timestamp', 'screener_timestamp']

function SectorIntelligencePage({ sectorName, data, scanTable, onScanTableChange }) {
  const [sort, setSort] = useState({ key: '', asc: true })

  if (!data) return <div className="state">Loading sector data…</div>

  const rawColumns = data.rows.length > 0 ? Object.keys(data.rows[0]) : []
  let displayCols = rawColumns.filter(col => {
    if (col === 'id' || col === 'run_time' || col.toLowerCase() === 'uniqueid') return true
    return !isInternalTimestamp(col)
  }).map(c => (c === 'id' || c === 'run_time' || c.toLowerCase() === 'uniqueid') ? 'record_id' : c)

  displayCols = Array.from(new Set(displayCols))
  const orderedCols = reorderColumns(displayCols)

  const sortBy = key => {
    const origKey = (key === 'record_id') ? (data.rows.length > 0 && 'run_time' in data.rows[0] ? 'run_time' : 'id') : key
    setSort(prev => ({
      key: origKey,
      asc: prev.key === origKey ? !prev.asc : true,
    }))
  }

  const sortedRows = (() => {
    if (!data?.rows) return []
    let list = [...data.rows]
    if (sort.key) {
      list.sort((a, b) => {
        const valA = a[sort.key] ?? ''
        const valB = b[sort.key] ?? ''
        if (typeof valA === 'number' && typeof valB === 'number') {
          return (valA - valB) * (sort.asc ? 1 : -1)
        }
        return String(valA).localeCompare(String(valB), undefined, { numeric: true }) * (sort.asc ? 1 : -1)
      })
    }
    return list
  })()

  const formatRecordIdDate = val => {
    if (!val) return '—'
    let s = String(val).trim()
    if (/^\d{12}$/.test(s) || /^\d{6}$/.test(s)) {
      const yy = s.slice(0, 2), mm = s.slice(2, 4), dd = s.slice(4, 6)
      return `${dd}-${mm}-${yy}`
    }
    if (/^\d{10,}$/.test(s)) {
      const d = new Date(Number(s) * (s.length === 10 ? 1000 : 1))
      if (!isNaN(d.getTime())) {
        return `${String(d.getDate()).padStart(2, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getFullYear()).slice(-2)}`
      }
    }
    const d = new Date(s)
    if (!isNaN(d.getTime())) {
      return `${String(d.getDate()).padStart(2, '0')}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getFullYear()).slice(-2)}`
    }
    return s
  }

  return (
    <div>
      <div className="master-toolbar" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span className="eyebrow">SCAN TABLE</span>
          <select className="select-input" value={scanTable} onChange={e => onScanTableChange(e.target.value)}>
            {SCAN_TABLES.map(t => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {data.tickers.map(t => <span key={t} className="ticker-chip">{t}</span>)}
        </div>
      </div>
      {data.rows.length === 0 ? (
        <div className="state">{data.tickers.length === 0 ? 'No tickers mapped to this sector yet. Add them in Raw Data → Ticker Master.' : 'No scan data for these tickers yet.'}</div>
      ) : (
        <section className="panel data-panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {orderedCols.map(k => {
                    const origKey = (k === 'record_id') ? (data.rows.length > 0 && 'run_time' in data.rows[0] ? 'run_time' : 'id') : k
                    return (
                      <th key={k} onClick={() => sortBy(k)} style={{ cursor: 'pointer', whiteSpace: 'nowrap' }}>
                        {k.replaceAll('_', ' ')} {sort.key === origKey && (sort.asc ? '↑' : '↓')}
                      </th>
                    )
                  })}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row, i) => (
                  <tr key={i}>
                    {orderedCols.map(k => {
                      const origKey = (k === 'record_id') ? (row.run_time ? 'run_time' : 'id') : k
                      const v = row[origKey] ?? row[k]
                      const badge = typeof v === 'string' && /signal|call|status|phase/.test(k) && k !== 'record_id'
                      if (k === 'ticker') {
                        return <td key={k}><b style={{ color: '#7ec8f0', fontFamily: "'DM Mono'" }}>{cleanTicker(v)}</b></td>
                      }
                      if (k === 'record_id') {
                        return <td key={k}>{formatRecordIdDate(v)}</td>
                      }
                      return <td key={k}>{badge ? <span className={`badge ${signalTone(v)}`}>{format(v, k)}</span> : format(v, k)}</td>
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}



createRoot(document.getElementById('root')).render(<App />)
