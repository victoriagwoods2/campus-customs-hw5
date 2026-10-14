import type { DeskTicket } from '../types'
import type { RunState } from '../App'

const TYPE_LABEL: Record<string, string> = {
  customer_order: 'Customer order',
  rent_notice: 'Rent notice',
  price_override: 'Price override',
}

interface Props {
  tickets: DeskTicket[] | null
  error: string | null
  selected: number
  runs: Record<number, RunState>
  justResolved: number | null
  onSelect: (id: number) => void
  onRetry: () => void
}

export function TicketRail({ tickets, error, selected, runs, justResolved, onSelect, onRetry }: Props) {
  return (
    <nav className="rail" aria-label="Desk tickets">
      <h2 className="panel-title">
        Desk tickets
        {tickets && (
          <span className="count">{tickets.filter((t) => t.status === 'open').length} open</span>
        )}
      </h2>

      {error && (
        <div className="callout err">
          <p>{error}</p>
          <button className="btn btn-small" onClick={onRetry}>Try again</button>
        </div>
      )}

      {!tickets && !error && [0, 1, 2].map((i) => <div key={i} className="stub skeleton" />)}

      {tickets?.map((t) => {
        const run = runs[t.id]
        const resolved = t.status === 'resolved'
        return (
          <button
            key={t.id}
            className={[
              'stub',
              selected === t.id && 'selected',
              resolved && 'resolved',
              run?.phase === 'running' && 'running',
              justResolved === t.id && 'just-resolved',
            ]
              .filter(Boolean)
              .join(' ')}
            onClick={() => onSelect(t.id)}
            aria-current={selected === t.id}
          >
            <div className="stub-top">
              <span className="stub-no">#{t.id}</span>
              <span className="stub-type">{TYPE_LABEL[t.type] ?? t.type}</span>
            </div>
            <div className="stub-subject">{t.subject}</div>
            <div className="stub-from">{t.requester}</div>
            <div className="stub-foot">
              {run?.phase === 'running' ? (
                <span className="pill pill-running"><span className="spinner" /> Agents working</span>
              ) : run?.phase === 'error' ? (
                <span className="pill pill-error">Run failed</span>
              ) : resolved ? null : (
                <span className="pill pill-open">Open</span>
              )}
            </div>
            {resolved && <span className="stamp" aria-label="Resolved">Resolved</span>}
          </button>
        )
      })}
    </nav>
  )
}
