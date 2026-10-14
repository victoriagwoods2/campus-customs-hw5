"""FastAPI entry point connecting the React dashboard to the agent team and MCP server."""

from __future__ import annotations

import asyncio
import fcntl
import hashlib
import json
import os
import shutil
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic_ai.exceptions import ModelRetry

try:
    from .agents.config import MODEL_NAME, PROJECT_ROOT, load_mcp_server
    from .agents.team import ROLE_DESCRIPTIONS, ROLE_PROMPTS, AgentTeam, build_agent_team
    from .audit import AUDIT_PATH
    from .models import (
        AgentCard,
        AgentEvent,
        AgentRunRequest,
        AgentRunResponse,
        ApproveRequest,
        CashStatus,
        DeskTicket,
        RejectRequest,
    )
except ImportError:  # Support `uvicorn main:app` from backend/.
    from agents.config import MODEL_NAME, PROJECT_ROOT, load_mcp_server
    from agents.team import ROLE_DESCRIPTIONS, ROLE_PROMPTS, AgentTeam, build_agent_team
    from audit import AUDIT_PATH
    from models import (
        AgentCard,
        AgentEvent,
        AgentRunRequest,
        AgentRunResponse,
        ApproveRequest,
        CashStatus,
        DeskTicket,
        RejectRequest,
    )


ORIGINAL_DB = PROJECT_ROOT / "data" / "campus_customs.db"
WORKING_DB = PROJECT_ROOT / "data" / "campus_customs_new.db"
DESK_TICKET_IDS = (101, 102, 103)
TOOL_PREFIX = "campus-customs_"
RESOLVING_STATUSES = {"completed", "needs_human_approval", "blocked"}

# One agent run at a time; reset waits for nothing and refuses while a run holds this lock.
_run_lock = asyncio.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Keep one MCP connection open for route lookups and human approval decisions."""
    server = load_mcp_server()  # unprefixed, unfiltered: includes the human-only tools
    async with server:
        app.state.mcp = server
        yield


app = FastAPI(
    title="Campus Customs Multi-Agent Operations",
    description="Ticket-resolution agents that use the Campus Customs MCP server.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@lru_cache(maxsize=1)
def get_team() -> AgentTeam:
    """Construct agents lazily; server startup does not call a model."""
    return build_agent_team()


async def call_mcp(tool: str, args: dict[str, Any] | None = None) -> Any:
    """Call an MCP tool; turn its error messages into HTTP errors."""
    try:
        return await app.state.mcp.direct_call_tool(tool, args or {})
    except ModelRetry as exc:
        message = str(exc)
        for prefix in (f"Error calling tool '{tool}': ", f"Error executing tool {tool}: "):
            message = message.removeprefix(prefix)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message) from exc


def require_desk_ticket(ticket_id: int) -> None:
    if ticket_id not in DESK_TICKET_IDS:
        raise HTTPException(status_code=404, detail=f"Ticket {ticket_id} is not on the desk (101, 102, 103).")


def refused(result: dict[str, Any]) -> HTTPException:
    """Map an MCP refusal to a safe HTTP error; insufficient cash is a 409 conflict."""
    reason = result.get("reason", "Request refused.")
    status = 404 if "not found" in reason.lower() else 409
    return HTTPException(status_code=status, detail=reason)


# ---------------------------------------------------------------- general


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "model": MODEL_NAME}


@app.get("/api/agents", response_model=list[AgentCard])
def list_agents() -> list[AgentCard]:
    return [
        AgentCard(name=name, responsibility=description, prompt_file=f"backend/prompts/{ROLE_PROMPTS[name]}")
        for name, description in ROLE_DESCRIPTIONS.items()
    ]


# ---------------------------------------------------------------- tickets


@app.get("/api/tickets", response_model=list[DeskTicket])
async def list_tickets() -> list[DeskTicket]:
    tickets = []
    for ticket_id in DESK_TICKET_IDS:
        context = await call_mcp("get_ticket_context", {"ticket_id": ticket_id})
        tickets.append(DeskTicket(**context["ticket"]))
    return tickets


@app.post("/api/tickets/{ticket_id}/run", response_model=AgentRunResponse)
async def run_ticket(ticket_id: int, request: AgentRunRequest | None = None) -> AgentRunResponse:
    require_desk_ticket(ticket_id)
    context = await call_mcp("get_ticket_context", {"ticket_id": ticket_id})
    if context["ticket"]["status"].lower() != "open":
        raise HTTPException(status_code=409, detail=f"Ticket {ticket_id} is already {context['ticket']['status']}; reset to run it again.")
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="Another ticket run is in progress.")
    try:
        team = get_team()
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    async with _run_lock:
        run_id, result, usage = await team.resolve_ticket(ticket_id, request.focus if request else None)
        # A finished run resolves the desk ticket; errors and budget stops leave it open to retry.
        ticket_status = "open"
        if result.status in RESOLVING_STATUSES:
            ticket_status = (await call_mcp("mark_ticket_resolved", {"ticket_id": ticket_id}))["status"]
    return AgentRunResponse(
        run_id=run_id, ticket_id=ticket_id, model=MODEL_NAME, result=result, usage=usage, ticket_status=ticket_status
    )


# ---------------------------------------------------------------- agent events


def _read_audit_trail() -> list[dict[str, Any]]:
    if not AUDIT_PATH.is_file():
        return []
    with AUDIT_PATH.open("rb") as trail:
        fcntl.flock(trail, fcntl.LOCK_SH)
        try:
            raw = trail.read()
        finally:
            fcntl.flock(trail, fcntl.LOCK_UN)
    return json.loads(raw) if raw.strip() else []


def _to_event(record: dict[str, Any]) -> AgentEvent:
    action = record.get("action")
    result = record.get("result")
    said = None
    tools: list[str] = []
    delegated_to = None
    if isinstance(action, dict):
        said = action.get("visible_text") or action.get("task")
        tools = [call["tool"] for call in action.get("tool_calls", []) + action.get("tool_results", [])]
        delegated_to = action.get("to_agent")
    elif isinstance(action, str) and record.get("event") in {"agent_started", "agent_error", "agent_budget_stopped"}:
        said = action
    if isinstance(result, dict) and result.get("summary"):
        said = result["summary"]
    return AgentEvent(
        time=record.get("time", ""),
        run_id=record.get("run_id"),
        ticket_id=record.get("ticket_id"),
        agent=record.get("agent", "?"),
        event=record.get("event", "?"),
        said=said,
        tools=list(dict.fromkeys(t.removeprefix(TOOL_PREFIX) for t in tools if t != "final_result")),
        delegated_to=delegated_to,
        depth=record.get("delegation_depth") or 0,
    )


@app.get("/api/events", response_model=list[AgentEvent])
def recent_events(
    limit: int = Query(50, ge=1, le=500),
    ticket_id: int | None = None,
    run_id: str | None = None,
) -> list[AgentEvent]:
    """Most recent agent-loop events from output/audit_trail.json, oldest first."""
    try:
        records = _read_audit_trail()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail="The audit trail is not valid JSON.") from exc
    if ticket_id is not None:
        records = [r for r in records if r.get("ticket_id") == ticket_id]
    if run_id is not None:
        records = [r for r in records if r.get("run_id") == run_id]
    return [_to_event(r) for r in records[-limit:]]


# ---------------------------------------------------------------- approvals


@app.get("/api/approvals")
async def pending_approvals() -> list[dict[str, Any]]:
    return await call_mcp("get_pending_approvals")


async def _pending_request(request_id: int) -> dict[str, Any]:
    for item in await call_mcp("get_pending_approvals"):
        if item["id"] == request_id:
            return item
    raise HTTPException(status_code=404, detail=f"Pending approval request {request_id} was not found.")


@app.post("/api/approvals/{request_id}/approve")
async def approve(request_id: int, body: ApproveRequest) -> dict[str, Any]:
    """The only path that carries out a payment or purchase; MCP rechecks cash inside a transaction."""
    item = await _pending_request(request_id)
    tool = "approve_payment_request" if item["request_type"] == "payment" else "approve_purchase_order_request"
    result = await call_mcp(tool, {"request_id": request_id, "approved_by": body.approved_by})
    if result.get("status") == "refused":
        raise refused(result)
    return result


@app.post("/api/approvals/{request_id}/reject")
async def reject(request_id: int, body: RejectRequest) -> dict[str, Any]:
    await _pending_request(request_id)
    result = await call_mcp(
        "reject_approval_request",
        {"request_id": request_id, "rejected_by": body.rejected_by, "reason": body.reason},
    )
    if result.get("status") == "refused":
        raise refused(result)
    return result


# ---------------------------------------------------------------- cash and reset


@app.get("/api/cash", response_model=CashStatus)
async def cash() -> CashStatus:
    status = await call_mcp("get_cash_status", {"account_name": "checking"})
    return CashStatus(
        account=status["account"]["name"],
        balance=status["account"]["balance"],
        as_of=status["account"]["date"],
        pending_payment_reservations=status["pending_payment_reservations"],
        available_after_pending_requests=status["available_after_pending_requests"],
    )


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@app.post("/api/reset")
def reset_working_database() -> dict[str, Any]:
    """Copy the untouched original over the working database. The audit trail is kept."""
    if _run_lock.locked():
        raise HTTPException(status_code=409, detail="Cannot reset while a ticket run is in progress.")
    if not ORIGINAL_DB.is_file():
        raise HTTPException(status_code=500, detail="The original database is missing; nothing was changed.")
    temp = WORKING_DB.with_suffix(".db.tmp")
    shutil.copyfile(ORIGINAL_DB, temp)
    os.replace(temp, WORKING_DB)
    matches = _sha256(ORIGINAL_DB) == _sha256(WORKING_DB)
    return {"status": "reset", "working_database": "data/campus_customs_new.db", "matches_original": matches}
