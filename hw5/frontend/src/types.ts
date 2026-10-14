// Shapes returned by the FastAPI backend (backend/models.py and backend/main.py).

export type AgentName = 'Boss' | 'Inventory' | 'Accounting' | 'Facilities' | 'Customer Service'

export interface DeskTicket {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  notes: string | null
  sku: string | null
  size: string | null
  qty: number | null
}

export interface AgentEvent {
  time: string
  run_id: string | null
  ticket_id: number | null
  agent: string
  event: string
  said: string | null
  tools: string[]
  delegated_to: string | null
  depth: number
}

export interface AgentAction {
  kind: string
  summary: string
  source_tool: string | null
  approval_request_id: number | null
}

export interface AgentResult {
  agent: AgentName
  ticket_id: number
  status: 'completed' | 'needs_human_approval' | 'blocked' | 'budget_limit' | 'error'
  summary: string
  verified_findings: string[]
  actions: AgentAction[]
  customer_message_draft: string | null
  approval_request_ids: number[]
  delegated_to: AgentName[]
  unresolved_questions: string[]
}

export interface AgentRunResponse {
  run_id: string
  ticket_id: number
  model: string
  result: AgentResult
  usage: {
    requests?: number
    tool_calls?: number
    input_tokens?: number
    output_tokens?: number
    delegations?: number
    elapsed_seconds?: number
  }
  ticket_status: string | null
}

export interface Approval {
  id: number
  ticket_id: number
  request_type: 'payment' | 'purchase_order'
  ref_id: number | null
  amount: number | null
  account: string | null
  status: string
  requested_by: string
  requested_at: string
  payload: Record<string, unknown>
}

export interface CashStatus {
  account: string
  balance: number
  as_of: string
  pending_payment_reservations: number
  available_after_pending_requests: number
}

export interface PaymentRecorded {
  status: string
  amount?: number
  new_balance?: number
  ticket_id?: number
}
