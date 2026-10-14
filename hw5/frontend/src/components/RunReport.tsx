import { AGENTS, agentSummaries } from '../agents'
import type { AgentEvent, AgentRunResponse } from '../types'

const STATUS_LABEL: Record<string, string> = {
  completed: 'Completed',
  needs_human_approval: 'Needs your approval',
  blocked: 'Blocked',
  budget_limit: 'Stopped at budget limit',
  error: 'Error',
}

interface Props {
  events: AgentEvent[]
  response: AgentRunResponse | undefined
}

export function RunReport({ events, response }: Props) {
  const summaries = agentSummaries(events)
  const finished = events.some((e) => e.event === 'ticket_run_finished')
  if (!finished || summaries.size === 0) return null

  const boss = response?.result
  const usage = response?.usage

  return (
    <section className="report" aria-label="Run summary">
      <div className="report-head">
        <h3 className="panel-title">
          What each agent did
          {!response && <span className="count">Last run · {new Date(events[0].time).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}</span>}
        </h3>
        {boss && <span className={`pill status-${boss.status}`}>{STATUS_LABEL[boss.status] ?? boss.status}</span>}
      </div>

      <div className="report-grid">
        {AGENTS.filter((a) => summaries.has(a.name)).map((a) => (
          <article
            key={a.name}
            className={`report-card ${a.name === 'Boss' ? 'lead' : ''}`}
            style={{ '--agent': a.color, '--tint': a.tint } as React.CSSProperties}
          >
            <header>
              <span aria-hidden>{a.icon}</span> {a.name}
            </header>
            <p>{summaries.get(a.name)}</p>
          </article>
        ))}
      </div>

      {boss && boss.unresolved_questions.length > 0 && (
        <div className="open-qs">
          <strong>Still open:</strong>
          <ul>{boss.unresolved_questions.map((q) => <li key={q}>{q}</li>)}</ul>
        </div>
      )}

      {usage && (
        <p className="usage">
          {usage.requests} model requests · {usage.tool_calls} tool calls · {usage.delegations} hand-offs ·{' '}
          {((usage.input_tokens ?? 0) + (usage.output_tokens ?? 0)).toLocaleString()} tokens · {usage.elapsed_seconds}s
        </p>
      )}
    </section>
  )
}
