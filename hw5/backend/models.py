"""Shared request, result, and agent-team models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


AgentName = Literal["Boss", "Inventory", "Accounting", "Facilities", "Customer Service"]
AgentStatus = Literal["completed", "needs_human_approval", "blocked", "budget_limit", "error"]
ActionKind = Literal[
    "lookup",
    "delegation",
    "recommendation",
    "payment_request",
    "purchase_order_request",
    "message_draft",
    "decision",
]


class AgentAction(BaseModel):
    """A concise, reviewable action or conclusion in an agent's report."""

    kind: ActionKind
    summary: str = Field(min_length=1, max_length=1200)
    source_tool: str | None = Field(default=None, max_length=120)
    approval_request_id: int | None = Field(default=None, ge=1)


class AgentResult(BaseModel):
    """Structured report returned by each team member."""

    agent: AgentName
    ticket_id: int = Field(ge=1)
    status: AgentStatus
    summary: str = Field(min_length=1, max_length=1800)
    verified_findings: list[str] = Field(default_factory=list, max_length=12)
    actions: list[AgentAction] = Field(default_factory=list, max_length=16)
    customer_message_draft: str | None = Field(default=None, max_length=1600)
    approval_request_ids: list[int] = Field(default_factory=list, max_length=8)
    delegated_to: list[AgentName] = Field(default_factory=list, max_length=8)
    unresolved_questions: list[str] = Field(default_factory=list, max_length=8)


class AgentRunRequest(BaseModel):
    """Optional focus for a ticket-resolution run; ticket facts still come from MCP."""

    focus: str | None = Field(default=None, max_length=1000)


class AgentCard(BaseModel):
    name: AgentName
    responsibility: str
    prompt_file: str


class AgentRunResponse(BaseModel):
    run_id: str
    ticket_id: int
    model: str
    result: AgentResult
    usage: dict[str, Any] = Field(default_factory=dict)
    ticket_status: str | None = None


class DeskTicket(BaseModel):
    id: int
    type: str
    requester: str
    subject: str
    status: str
    notes: str | None = None
    sku: str | None = None
    size: str | None = None
    qty: int | None = None


class AgentEvent(BaseModel):
    """One audit-trail step reshaped for the dashboard feed."""

    time: str
    run_id: str | None = None
    ticket_id: int | None = None
    agent: str
    event: str
    said: str | None = None
    tools: list[str] = Field(default_factory=list)
    delegated_to: str | None = None
    depth: int = 0


class ApproveRequest(BaseModel):
    approved_by: str = Field(min_length=1, max_length=120)


class RejectRequest(BaseModel):
    rejected_by: str = Field(min_length=1, max_length=120)
    reason: str = Field(min_length=1, max_length=500)


class CashStatus(BaseModel):
    account: str
    balance: float
    as_of: str
    pending_payment_reservations: float
    available_after_pending_requests: float


class MCPToolCard(BaseModel):
    name: str
    tables: list[str]
    access: Literal["read", "proposal", "human_approval", "draft"]
    human_only: bool = False
