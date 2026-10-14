import { useCallback, useEffect, useRef, useState } from 'react'
import { API_BASE, api, money } from './api'
import { latestRun } from './agents'
import { ActivityFeed } from './components/ActivityFeed'
import { Approvals } from './components/Approvals'
import { Header } from './components/Header'
import { RunReport } from './components/RunReport'
import { TicketRail } from './components/TicketRail'
import type { AgentEvent, AgentRunResponse, Approval, CashStatus, DeskTicket } from './types'

export interface RunState {
  phase: 'running' | 'done' | 'error'
  startedAt: number
  response?: AgentRunResponse
  error?: string
}

interface Toast {
  id: number
  tone: 'ok' | 'err' | 'info'
  text: string
}

const EVENT_POLL_MS = 1500
const BACKGROUND_POLL_MS = 5000

export default function App() {
  const [online, setOnline] = useState<boolean | null>(null)
  const [tickets, setTickets] = useState<DeskTicket[] | null>(null)
  const [ticketsError, setTicketsError] = useState<string | null>(null)
  const [selected, setSelected] = useState(() => {
    const fromUrl = Number(new URLSearchParams(window.location.search).get('ticket'))
    return [101, 102, 103].includes(fromUrl) ? fromUrl : 101
  })
  const [runs, setRuns] = useState<Record<number, RunState>>({})
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [eventsError, setEventsError] = useState<string | null>(null)
  const [approvals, setApprovals] = useState<Approval[] | null>(null)
  const [approvalsError, setApprovalsError] = useState<string | null>(null)
  const [cash, setCash] = useState<CashStatus | null>(null)
  const [cashError, setCashError] = useState<string | null>(null)
  const [delta, setDelta] = useState<{ amount: number; key: number } | null>(null)
  const [justResolved, setJustResolved] = useState<number | null>(null)
  const [resetting, setResetting] = useState(false)
  const [toasts, setToasts] = useState<Toast[]>([])
  const [approver, setApprover] = useState(() => localStorage.getItem('cc-approver') ?? '')
  const lastBalance = useRef<number | null>(null)

  const toast = useCallback((tone: Toast['tone'], text: string) => {
    const id = Date.now() + Math.random()
    setToasts((t) => [...t, { id, tone, text }])
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 5000)
  }, [])

  // ---------------------------------------------------------------- loaders

  const loadTickets = useCallback(async () => {
    try {
      const list = await api.tickets()
      setTickets(list)
      setTicketsError(null)
      setOnline(true)
      return list
    } catch (e) {
      setTicketsError((e as Error).message)
      return null
    }
  }, [])

  const loadApprovals = useCallback(async () => {
    try {
      setApprovals(await api.approvals())
      setApprovalsError(null)
    } catch (e) {
      setApprovalsError((e as Error).message)
    }
  }, [])

  const loadCash = useCallback(async () => {
    try {
      const next = await api.cash()
      const prev = lastBalance.current
      if (prev !== null && Math.abs(next.balance - prev) > 0.004) {
        setDelta({ amount: next.balance - prev, key: Date.now() })
      }
      lastBalance.current = next.balance
      setCash(next)
      setCashError(null)
    } catch (e) {
      setCashError((e as Error).message)
    }
  }, [])

  const run = runs[selected]
  const running = run?.phase === 'running'
  const anyRunning = Object.values(runs).some((r) => r.phase === 'running')

  const loadEvents = useCallback(async (ticketId: number, since?: number) => {
    try {
      const all = await api.events(ticketId)
      setEvents(latestRun(all, since))
      setEventsError(null)
    } catch (e) {
      setEventsError((e as Error).message)
    }
  }, [])

  // ---------------------------------------------------------------- polling

  useEffect(() => {
    const check = () =>
      api
        .health()
        .then(() => setOnline(true))
        .catch(() => setOnline(false))
    check()
    loadTickets()
    loadApprovals()
    loadCash()
    const id = setInterval(() => {
      check()
      loadApprovals()
      loadCash()
    }, BACKGROUND_POLL_MS)
    return () => clearInterval(id)
  }, [loadTickets, loadApprovals, loadCash])

  // Activity for the selected ticket: once on selection, then every 1.5s while its run is going.
  useEffect(() => {
    setEvents([])
    loadEvents(selected, running ? run?.startedAt : undefined)
    if (!running) return
    const id = setInterval(() => loadEvents(selected, run?.startedAt), EVENT_POLL_MS)
    return () => clearInterval(id)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selected, running, loadEvents])

  // ---------------------------------------------------------------- actions

  async function startRun(ticketId: number) {
    const startedAt = Date.now()
    setRuns((r) => ({ ...r, [ticketId]: { phase: 'running', startedAt } }))
    try {
      const response = await api.run(ticketId)
      setRuns((r) => ({ ...r, [ticketId]: { phase: 'done', startedAt, response } }))
      if (response.ticket_status === 'resolved') {
        setJustResolved(ticketId)
        toast('ok', `Ticket ${ticketId} resolved by the agent team.`)
      } else {
        toast('info', `Ticket ${ticketId} run ended: ${response.result.status.replace(/_/g, ' ')}. It stays open.`)
      }
    } catch (e) {
      const message = (e as Error).message
      setRuns((r) => ({ ...r, [ticketId]: { phase: 'error', startedAt, error: message } }))
      toast('err', `Ticket ${ticketId}: ${message}`)
    } finally {
      loadTickets()
      loadApprovals()
      loadCash()
      if (ticketId === selected) loadEvents(ticketId)
    }
  }

  async function approve(a: Approval) {
    let result
    try {
      result = await api.approve(a.id, approver.trim())
    } catch (e) {
      // A refusal (e.g. insufficient cash) may also close the request, so surface it outside the card too.
      toast('err', `Request #${a.id} not approved: ${(e as Error).message}`)
      await Promise.all([loadApprovals(), loadCash()])
      throw e
    }
    if (a.request_type === 'payment') {
      toast('ok', `Paid ${money(a.amount ?? 0)} for ticket ${a.ticket_id}. New balance ${money(result.new_balance ?? 0)}.`)
    } else {
      toast('ok', `Purchase order #${a.id} approved for manual follow-up.`)
    }
    const before = tickets?.find((t) => t.id === a.ticket_id)?.status
    const [, , after] = await Promise.all([loadApprovals(), loadCash(), loadTickets()])
    if (before === 'open' && after?.find((t) => t.id === a.ticket_id)?.status === 'resolved') {
      setJustResolved(a.ticket_id)
      toast('ok', `Ticket ${a.ticket_id} is now resolved.`)
    }
  }

  async function reject(a: Approval, reason: string) {
    await api.reject(a.id, approver.trim(), reason)
    toast('info', `Request #${a.id} declined.`)
    await loadApprovals()
  }

  async function reset() {
    if (!window.confirm('Reset the working database to the original values? Payments, approvals, drafts and ticket statuses go back to the start. The audit trail is kept.')) return
    setResetting(true)
    try {
      await api.reset()
      setRuns({})
      setEvents([])
      setJustResolved(null)
      toast('ok', 'Desk reset. All three tickets are open again.')
      await Promise.all([loadTickets(), loadApprovals(), loadCash()])
    } catch (e) {
      toast('err', `Reset failed: ${(e as Error).message}`)
    } finally {
      setResetting(false)
    }
  }

  const ticket = tickets?.find((t) => t.id === selected)
  const resolved = ticket?.status === 'resolved'

  return (
    <div className="app">
      <Header
        online={online}
        apiBase={API_BASE}
        cash={cash}
        cashError={cashError}
        delta={delta}
        resetting={resetting}
        canReset={!anyRunning && online !== false}
        onReset={reset}
      />

      {online === false && (
        <div className="banner">
          Can't reach the backend at <code>{API_BASE}</code>. Start it from <code>backend/</code> with{' '}
          <code>uvicorn main:app --reload --port 8000</code>. The dashboard will reconnect on its own.
        </div>
      )}

      <main className="desk">
        <TicketRail
          tickets={tickets}
          error={ticketsError}
          selected={selected}
          runs={runs}
          justResolved={justResolved}
          onSelect={setSelected}
          onRetry={loadTickets}
        />

        <div className="workspace">
          {ticket ? (
            <section className={`ticket-card ${resolved ? 'is-resolved' : ''}`}>
              <div className="ticket-card-main">
                <div className="eyebrow">Ticket #{ticket.id} · from {ticket.requester}</div>
                <h2>{ticket.subject}</h2>
                {ticket.notes && <blockquote>“{ticket.notes}”</blockquote>}
                <div className="facts">
                  {ticket.sku && <span className="fact"><b>SKU</b> {ticket.sku}</span>}
                  {ticket.size && <span className="fact"><b>Size</b> {ticket.size}</span>}
                  {ticket.qty !== null && <span className="fact"><b>Qty</b> {ticket.qty}</span>}
                  <span className="fact"><b>Status</b> {ticket.status}</span>
                </div>
              </div>
              <div className="ticket-card-cta">
                {resolved ? (
                  <div className="resolved-note">
                    <span className="check">✓</span> Resolved
                    <small>Reset the desk to run it again.</small>
                  </div>
                ) : (
                  <button
                    className="btn btn-primary btn-large"
                    onClick={() => startRun(ticket.id)}
                    disabled={anyRunning || online === false}
                  >
                    {running ? (
                      <><span className="spinner light" /> Agents working…</>
                    ) : anyRunning ? (
                      'Another ticket is running'
                    ) : run?.phase === 'error' ? (
                      'Try the agent team again'
                    ) : (
                      'Start agent team'
                    )}
                  </button>
                )}
                {run?.phase === 'error' && <p className="cta-error">{run.error}</p>}
                {running && <p className="cta-note">Usually 30–90 seconds. Activity updates live.</p>}
              </div>
            </section>
          ) : (
            <section className="ticket-card skeleton tall" />
          )}

          <RunReport events={events} response={run?.response} />
          <ActivityFeed events={events} running={running} error={eventsError} />
        </div>

        <Approvals
          approvals={approvals}
          error={approvalsError}
          cash={cash}
          approver={approver}
          onApproverChange={(name) => {
            setApprover(name)
            localStorage.setItem('cc-approver', name)
          }}
          onApprove={approve}
          onReject={reject}
        />
      </main>

      <div className="toasts" role="status" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`}>{t.text}</div>
        ))}
      </div>
    </div>
  )
}
