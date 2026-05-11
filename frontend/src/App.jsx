import { useState } from 'react'

const API = 'http://localhost:8000'

function severityClass(n) {
  if (n <= 2) return 'sev-low'
  if (n === 3) return 'sev-mid'
  return 'sev-high'
}

function Ticket({ ticket }) {
  return (
    <details className="ticket">
      <summary>
        <span className={`sev-badge ${severityClass(ticket.severity)}`}>SEV {ticket.severity}</span>
        <span className="ticket-id">{ticket.ticket_id}</span>
        <span className="ticket-issue">{ticket.issue}</span>
      </summary>
      <div className="ticket-body">
        <div className="ticket-row">
          <span className="ticket-label">Cluster</span>
          <span>{ticket.cluster}</span>
        </div>
        <div className="ticket-row">
          <span className="ticket-label">Affected Servers</span>
          <span>{ticket.affected_servers.join(', ')}</span>
        </div>
        <div className="ticket-row col">
          <span className="ticket-label">Description</span>
          <p className="ticket-text">{ticket.description}</p>
        </div>
        <div className="ticket-row col">
          <span className="ticket-label">Remediation</span>
          <pre className="remediation">{ticket.remediation}</pre>
        </div>
      </div>
    </details>
  )
}

function ClusterSelect({ value, onChange, disabled }) {
  return (
    <select value={value} onChange={e => onChange(e.target.value)} disabled={disabled}>
      <option value="A">Cluster A</option>
      <option value="B">Cluster B</option>
      <option value="C">Cluster C</option>
      <option value="D">Cluster D</option>
    </select>
  )
}

function streamSSE(res, onEvent) {
  return (async () => {
    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() ?? ''
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const raw = line.slice(6).trim()
          if (!raw) continue
          try { onEvent(JSON.parse(raw)) } catch {}
        }
      }
    }
  })()
}

function TicketGeneratorTab() {
  const [cluster, setCluster] = useState('A')
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [aggregatedCount, setAggregatedCount] = useState(null)
  const [postLLMCount, setPostLLMCount] = useState(null)
  const [tickets, setTickets] = useState([])
  const [lastRunCount, setLastRunCount] = useState(null)
  const [complete, setComplete] = useState(false)
  const [error, setError] = useState(null)

  const handleEvent = (event) => {
    switch (event.type) {
      case 'started':
        setStatus(`Starting run for Cluster ${event.cluster_id}…`)
        break
      case 'update':
        if (event.status !== undefined) setStatus(event.status)
        if (event.aggregated_issues_count !== undefined) setAggregatedCount(event.aggregated_issues_count)
        if (event.post_llm_filter_issues_count !== undefined) setPostLLMCount(event.post_llm_filter_issues_count)
        break
      case 'complete':
        setStatus(event.status ?? 'Run complete.')
        setAggregatedCount(event.aggregated_issues_count)
        setPostLLMCount(event.post_llm_filter_issues_count)
        setTickets(event.tickets_created ?? [])
        setLastRunCount(event.last_run_count ?? 0)
        setComplete(true)
        break
      case 'error':
        setError(event.message)
        break
    }
  }

  const run = async () => {
    setRunning(true)
    setError(null)
    setComplete(false)
    setStatus(null)
    setAggregatedCount(null)
    setPostLLMCount(null)
    setTickets([])
    setLastRunCount(null)

    try {
      const res = await fetch(`${API}/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cluster_id: cluster }),
      })
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`)
      await streamSSE(res, handleEvent)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const hasActivity = status !== null || aggregatedCount !== null

  return (
    <>
      <section className="controls">
        <ClusterSelect value={cluster} onChange={setCluster} disabled={running} />
        <button onClick={run} disabled={running} className={running ? 'btn-running' : ''}>
          {running && <span className="spinner" />}
          {running ? 'Running…' : 'Run Ticket Generator'}
        </button>
      </section>

      {hasActivity && (
        <section className="metrics">
          <div className="metric-card">
            <div className="metric-label">Status</div>
            <div className="metric-value status-text">{status ?? '—'}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Aggregated Issues</div>
            <div className={`metric-value num ${aggregatedCount > 0 ? 'amber' : ''}`}>
              {aggregatedCount ?? '—'}
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Post-LLM Filter Issues</div>
            <div className={`metric-value num ${postLLMCount > 0 ? 'amber' : ''}`}>
              {postLLMCount ?? '—'}
            </div>
          </div>
        </section>
      )}

      {complete && (
        <section className="stats-bar">
          <div className="stat">
            <span className="stat-label">Tickets Last Run</span>
            <span className="stat-value green">{lastRunCount ?? 0}</span>
          </div>
        </section>
      )}

      {tickets.length > 0 && (
        <section className="tickets-section">
          <h2>Tickets Created <span className="ticket-count">{tickets.length}</span></h2>
          {tickets.map(t => <Ticket key={t.ticket_id} ticket={t} />)}
        </section>
      )}

      {error && (
        <div className="error-banner">
          <strong>Error</strong> — {error}
        </div>
      )}
    </>
  )
}

function ClusterAuditTab() {
  const [cluster, setCluster] = useState('A')
  const [query, setQuery] = useState('')
  const [running, setRunning] = useState(false)
  const [status, setStatus] = useState(null)
  const [issuesCount, setIssuesCount] = useState(null)
  const [tickets, setTickets] = useState([])
  const [complete, setComplete] = useState(false)
  const [error, setError] = useState(null)
  const [queryExplanation, setQueryExplanation] = useState(null)
  const [deduplicateResults, setDeduplicateResults] = useState(false)

  const handleEvent = (event) => {
    switch (event.type) {
      case 'started':
        setStatus(`Starting audit for Cluster ${event.cluster_id}…`)
        break
      case 'update':
        if (event.status !== undefined) setStatus(event.status)
        if (event.issues_count !== undefined) setIssuesCount(event.issues_count)
        break
      case 'complete':
        setStatus(event.status ?? 'Audit complete.')
        if (event.issues_count !== undefined) setIssuesCount(event.issues_count)
        setTickets(event.tickets_created ?? [])
        if (event.query_explanation != null) setQueryExplanation(event.query_explanation)
        setComplete(true)
        break
      case 'error':
        setError(event.message)
        break
    }
  }

  const run = async () => {
    setRunning(true)
    setError(null)
    setStatus(null)
    setIssuesCount(null)
    setTickets([])
    setComplete(false)
    setQueryExplanation(null)

    try {
      const res = await fetch(`${API}/audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cluster_id: cluster, query: query.trim(), perform_deduplication: deduplicateResults }),
      })
      if (!res.ok) throw new Error(`Server returned HTTP ${res.status}`)
      await streamSSE(res, handleEvent)
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
    }
  }

  const hasActivity = status !== null || issuesCount !== null

  return (
    <>
      <section className="controls">
        <ClusterSelect value={cluster} onChange={setCluster} disabled={running} />
        <button onClick={run} disabled={running} className={running ? 'btn-running' : ''}>
          {running && <span className="spinner" />}
          {running ? 'Auditing…' : 'Run Audit'}
        </button>
      </section>

      <div className="audit-query">
        <label className="audit-query-label">Audit Focus</label>
        <textarea
          className="audit-query-input"
          placeholder="Describe what to look for — or leave blank for a general audit."
          value={query}
          onChange={e => setQuery(e.target.value)}
          disabled={running}
          rows={3}
        />
      </div>

      <label className="audit-option">
        <input
          type="checkbox"
          checked={deduplicateResults}
          onChange={e => setDeduplicateResults(e.target.checked)}
          disabled={running}
        />
        Deduplicate audit results against active helpdesk tickets
      </label>

      {queryExplanation && (
        <div className="query-assessment">
          <span className="query-assessment-label">Query Assessment</span>
          <p className="query-assessment-text">{queryExplanation}</p>
        </div>
      )}

      {hasActivity && (
        <section className="metrics">
          <div className="metric-card metric-card--full">
            <div className="metric-label">Status</div>
            <div className="metric-value status-text">{status ?? '—'}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Issues Found</div>
            <div className={`metric-value num ${issuesCount > 0 ? 'amber' : ''}`}>
              {issuesCount ?? '—'}
            </div>
          </div>
        </section>
      )}

      {complete && (
        <section className="stats-bar">
          <div className="stat">
            <span className="stat-label">Tickets Created</span>
            <span className="stat-value green">{tickets.length}</span>
          </div>
        </section>
      )}

      {tickets.length > 0 && (
        <section className="tickets-section">
          <h2>Audit Tickets <span className="ticket-count">{tickets.length}</span></h2>
          {tickets.map(t => <Ticket key={t.ticket_id} ticket={t} />)}
        </section>
      )}

      {error && (
        <div className="error-banner">
          <strong>Error</strong> — {error}
        </div>
      )}
    </>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('tickets')

  return (
    <div className="app">
      <header>
        <h1>Server Ticket Debugger</h1>
      </header>

      <nav className="tabs">
        <button
          className={`tab-btn ${activeTab === 'tickets' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('tickets')}
        >
          Ticket Generator
        </button>
        <button
          className={`tab-btn ${activeTab === 'audit' ? 'tab-active' : ''}`}
          onClick={() => setActiveTab('audit')}
        >
          Cluster Audit
        </button>
      </nav>

      {activeTab === 'tickets' ? <TicketGeneratorTab /> : <ClusterAuditTab />}
    </div>
  )
}
