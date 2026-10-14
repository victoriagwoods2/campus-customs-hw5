import { money } from '../api'
import type { CashStatus } from '../types'

interface Props {
  online: boolean | null
  apiBase: string
  cash: CashStatus | null
  cashError: string | null
  delta: { amount: number; key: number } | null
  resetting: boolean
  canReset: boolean
  onReset: () => void
}

export function Header({ online, apiBase, cash, cashError, delta, resetting, canReset, onReset }: Props) {
  return (
    <header className="masthead">
      <div className="brand">
        <div className="brand-mark" aria-hidden>CC</div>
        <div>
          <h1>Campus Customs</h1>
          <p className="brand-sub">
            Operations Desk
            {cash && <span className="shop-date"> · Shop date {formatDate(cash.as_of)}</span>}
          </p>
        </div>
      </div>

      <div className="masthead-right">
        <span className={`conn conn-${online === null ? 'wait' : online ? 'on' : 'off'}`} title={apiBase}>
          <span className="conn-dot" />
          {online === null ? 'Connecting…' : online ? 'Backend connected' : 'Backend offline'}
        </span>

        <section className="till" aria-label="Checking balance">
          <div className="till-label">Checking</div>
          {cash ? (
            <div className="till-row">
              <div key={delta?.key ?? 0} className={`till-amount ${delta ? (delta.amount < 0 ? 'flash-out' : 'flash-in') : ''}`}>
                {money(cash.balance)}
              </div>
              {delta && (
                <span key={`d${delta.key}`} className={`till-delta ${delta.amount < 0 ? 'neg' : 'pos'}`}>
                  {delta.amount < 0 ? '−' : '+'}
                  {money(Math.abs(delta.amount))}
                </span>
              )}
            </div>
          ) : (
            <div className="till-amount muted">{cashError ? 'Unavailable' : '—'}</div>
          )}
          {cash && cash.pending_payment_reservations > 0 && (
            <div className="till-note">
              {money(cash.pending_payment_reservations)} awaiting sign-off · {money(cash.available_after_pending_requests)} free
            </div>
          )}
          {cashError && <div className="till-note err">{cashError}</div>}
        </section>

        <button className="btn btn-ghost" onClick={onReset} disabled={!canReset || resetting}>
          {resetting ? 'Resetting…' : 'Reset desk'}
        </button>
      </div>
    </header>
  )
}

function formatDate(iso: string) {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
}
