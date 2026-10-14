import { useState } from 'react'
import { money } from '../api'
import type { Approval, CashStatus } from '../types'

type CardState = { phase: 'idle' | 'approving' | 'rejecting' | 'confirm-reject'; error?: string; reason?: string }

interface Props {
  approvals: Approval[] | null
  error: string | null
  cash: CashStatus | null
  approver: string
  onApproverChange: (name: string) => void
  onApprove: (a: Approval) => Promise<void>
  onReject: (a: Approval, reason: string) => Promise<void>
}

export function Approvals({ approvals, error, cash, approver, onApproverChange, onApprove, onReject }: Props) {
  const [cards, setCards] = useState<Record<number, CardState>>({})
  const set = (id: number, s: CardState) => setCards((c) => ({ ...c, [id]: s }))

  async function approve(a: Approval) {
    set(a.id, { phase: 'approving' })
    try {
      await onApprove(a)
      set(a.id, { phase: 'idle' })
    } catch (e) {
      set(a.id, { phase: 'idle', error: (e as Error).message })
    }
  }

  async function reject(a: Approval, reason: string) {
    set(a.id, { phase: 'rejecting', reason })
    try {
      await onReject(a, reason)
      set(a.id, { phase: 'idle' })
    } catch (e) {
      set(a.id, { phase: 'confirm-reject', reason, error: (e as Error).message })
    }
  }

  const nameMissing = approver.trim().length === 0

  return (
    <aside className="approvals" aria-label="Pending approvals">
      <h2 className="panel-title">
        Needs your sign-off
        {approvals && approvals.length > 0 && <span className="count hot">{approvals.length}</span>}
      </h2>

      <label className="approver">
        <span>Signing as</span>
        <input
          value={approver}
          onChange={(e) => onApproverChange(e.target.value)}
          placeholder="Your name"
          maxLength={120}
        />
      </label>

      {error && <div className="callout err"><p>{error}</p></div>}
      {!approvals && !error && <div className="approval skeleton" />}

      {approvals?.length === 0 && (
        <p className="empty-note">Nothing waiting. Agents will put payment and purchase-order requests here for a person to approve.</p>
      )}

      {approvals?.map((a) => {
        const state = cards[a.id] ?? { phase: 'idle' }
        const busy = state.phase === 'approving' || state.phase === 'rejecting'
        const isPayment = a.request_type === 'payment'
        const amount = a.amount ?? 0
        const after = cash ? cash.balance - amount : null
        const short = isPayment && after !== null && after < 0
        const p = a.payload
        return (
          <article key={a.id} className={`approval ${isPayment ? 'pay' : 'po'} ${busy ? 'busy' : ''}`}>
            <div className="approval-top">
              <span className="kind">{isPayment ? 'Payment' : 'Purchase order'}</span>
              <span className="ref">Request #{a.id} · Ticket {a.ticket_id}</span>
            </div>

            {isPayment ? (
              <>
                <div className="approval-amount">{money(amount)}</div>
                <div className="approval-what">
                  {p.kind === 'lease_rent' ? 'Rent' : 'Invoice'} · {String(p.description ?? '')}
                  {p.due_date ? <> · due {String(p.due_date)}</> : null}
                </div>
                {after !== null && (
                  <div className={`after ${short ? 'short' : ''}`}>
                    {short
                      ? `Exceeds checking by ${money(-after)}. The backend will refuse it.`
                      : `Checking after payment: ${money(after)}`}
                  </div>
                )}
              </>
            ) : (
              <>
                <div className="approval-amount small">
                  {String(p.order_quantity ?? '?')} × {String(p.item_name ?? p.sku ?? '')} ({String(p.size ?? '')})
                </div>
                <div className="approval-what">
                  {String((p.vendor as { name?: string } | undefined)?.name ?? 'Vendor')} · lead time{' '}
                  {String((p.vendor as { lead_days?: number } | undefined)?.lead_days ?? '?')} days
                </div>
                <div className="after">Approving records it for manual follow-up. No vendor is contacted.</div>
              </>
            )}

            <div className="requested">Prepared by {a.requested_by}</div>

            {state.error && <div className="callout err small"><p>{state.error}</p></div>}

            {state.phase === 'confirm-reject' || state.phase === 'rejecting' ? (
              <form
                className="reject-form"
                onSubmit={(e) => {
                  e.preventDefault()
                  if (state.reason?.trim()) reject(a, state.reason.trim())
                }}
              >
                <input
                  autoFocus
                  placeholder="Reason for declining"
                  value={state.reason ?? ''}
                  maxLength={500}
                  onChange={(e) => set(a.id, { ...state, reason: e.target.value })}
                />
                <div className="actions">
                  <button type="button" className="btn btn-ghost btn-small" onClick={() => set(a.id, { phase: 'idle' })} disabled={busy}>
                    Cancel
                  </button>
                  <button type="submit" className="btn btn-decline btn-small" disabled={busy || nameMissing || !state.reason?.trim()}>
                    {state.phase === 'rejecting' ? 'Declining…' : 'Decline'}
                  </button>
                </div>
              </form>
            ) : (
              <div className="actions">
                <button className="btn btn-ghost btn-small" onClick={() => set(a.id, { phase: 'confirm-reject' })} disabled={busy || nameMissing}>
                  Decline
                </button>
                <button className="btn btn-approve" onClick={() => approve(a)} disabled={busy || nameMissing}>
                  {state.phase === 'approving' ? 'Approving…' : isPayment ? `Approve ${money(amount)}` : 'Approve order'}
                </button>
              </div>
            )}
            {nameMissing && <div className="hint">Enter your name above to sign.</div>}
          </article>
        )
      })}
    </aside>
  )
}
