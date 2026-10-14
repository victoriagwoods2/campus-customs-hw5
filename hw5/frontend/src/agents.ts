import type { AgentEvent, AgentName } from './types'

export interface AgentStyle {
  name: AgentName
  short: string
  icon: string
  color: string // text-safe on paper and white
  tint: string // soft background
  role: string
}

export const AGENTS: AgentStyle[] = [
  { name: 'Boss', short: 'Boss', icon: '🧭', color: '#00356b', tint: '#e3ebf4', role: 'Reads the ticket, assigns work, decides' },
  { name: 'Inventory', short: 'Inventory', icon: '📦', color: '#2c6e49', tint: '#e2f0e7', role: 'Stock by SKU and size, vendors' },
  { name: 'Accounting', short: 'Accounting', icon: '🧾', color: '#8a5a0b', tint: '#f6ecd8', role: 'Cash, invoices, margins, requests' },
  { name: 'Facilities', short: 'Facilities', icon: '🏬', color: '#a1412b', tint: '#f6e3dd', role: 'Leases, rent, the shop space' },
  { name: 'Customer Service', short: 'Customer Svc', icon: '💬', color: '#5f4597', tint: '#ebe5f5', role: 'Drafts customer messages' },
]

const FALLBACK: AgentStyle = { name: 'Boss', short: '?', icon: '•', color: '#4a5160', tint: '#eceae4', role: '' }

export const agentStyle = (name: string | null | undefined): AgentStyle =>
  AGENTS.find((a) => a.name === name) ?? { ...FALLBACK, short: name ?? '?' }

export interface FeedLine {
  key: string
  event: AgentEvent
  verb: string
  text: string | null
  tools: string[]
  seconds: number
}

/** Turn raw audit events into readable feed lines; low-level bookkeeping steps are skipped. */
export function toFeed(events: AgentEvent[]): FeedLine[] {
  if (events.length === 0) return []
  const start = Date.parse(events[0].time)
  const lines: FeedLine[] = []
  events.forEach((e, i) => {
    const tools = e.tools.filter((t) => !t.startsWith('delegate_to_'))
    let verb: string
    let text: string | null = null
    switch (e.event) {
      case 'ticket_run_started':
        verb = 'opened the ticket'
        break
      case 'agent_started':
        if (e.depth > 0) return // the hand-off line already shows the task
        verb = 'picked up the ticket'
        break
      case 'model_action':
        if (tools.length === 0 && !e.said) return
        verb = tools.some((t) => t.startsWith('request_'))
          ? 'filed a request for human approval'
          : tools.includes('save_customer_message_draft')
            ? 'saved a draft to the board'
            : tools.length
              ? 'checked the shop records'
              : 'said'
        text = e.said
        break
      case 'delegation_started':
        verb = `handed off to ${e.delegated_to}`
        text = e.said
        break
      case 'delegation_finished':
        verb = `heard back from ${e.delegated_to}`
        break
      case 'agent_finished':
        verb = 'reported back'
        text = e.said
        break
      case 'agent_budget_stopped':
        verb = 'stopped at the budget limit'
        text = e.said
        break
      case 'agent_error':
        verb = 'hit an error'
        text = e.said
        break
      case 'ticket_run_finished':
        verb = 'closed out the run'
        break
      default:
        return
    }
    lines.push({
      key: `${e.time}-${i}`,
      event: e,
      verb,
      text,
      tools,
      seconds: Math.max(0, Math.round((Date.parse(e.time) - start) / 1000)),
    })
  })
  return lines
}

/** Latest summary each agent reported in this run. */
export function agentSummaries(events: AgentEvent[]): Map<string, string> {
  const map = new Map<string, string>()
  for (const e of events) {
    if (e.event === 'agent_finished' && e.said) map.set(e.agent, e.said)
  }
  return map
}

/** Keep only the latest run on this ticket (optionally one that started after `since`). */
export function latestRun(events: AgentEvent[], since?: number): AgentEvent[] {
  const starts = events.filter((e) => e.event === 'ticket_run_started')
  const last = starts[starts.length - 1]
  if (!last) return []
  if (since !== undefined && Date.parse(last.time) < since - 5000) return []
  return events.filter((e) => e.run_id === last.run_id)
}
