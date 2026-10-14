import type { AgentEvent, AgentRunResponse, Approval, CashStatus, DeskTicket, PaymentRecorded } from './types'

const configured = import.meta.env.VITE_API_BASE as string | undefined
export const API_BASE = (configured || 'http://localhost:8000').replace(/\/$/, '')

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
    })
  } catch {
    throw new ApiError(0, `Can't reach the backend at ${API_BASE}.`)
  }
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') message = body.detail
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join('; ')
    } catch {
      /* keep the status text */
    }
    throw new ApiError(response.status, message)
  }
  return response.json() as Promise<T>
}

const post = <T>(path: string, body?: unknown) =>
  request<T>(path, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })

export const api = {
  health: () => request<{ status: string; model: string }>('/api/health'),
  tickets: () => request<DeskTicket[]>('/api/tickets'),
  run: (ticketId: number) => post<AgentRunResponse>(`/api/tickets/${ticketId}/run`),
  events: (ticketId: number, limit = 400) =>
    request<AgentEvent[]>(`/api/events?ticket_id=${ticketId}&limit=${limit}`),
  approvals: () => request<Approval[]>('/api/approvals'),
  approve: (id: number, approvedBy: string) =>
    post<PaymentRecorded>(`/api/approvals/${id}/approve`, { approved_by: approvedBy }),
  reject: (id: number, rejectedBy: string, reason: string) =>
    post<{ status: string }>(`/api/approvals/${id}/reject`, { rejected_by: rejectedBy, reason }),
  cash: () => request<CashStatus>('/api/cash'),
  reset: () => post<{ status: string; matches_original: boolean }>('/api/reset'),
}

export const money = (value: number) =>
  value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
