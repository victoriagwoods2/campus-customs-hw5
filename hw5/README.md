# Campus Customs Multi-Agent Operations (HW5)

A five-agent team (Boss, Inventory, Accounting, Facilities, Customer Service) resolves Campus Customs shop tickets. The agents are built with PydanticAI and use `gpt-6-luna` through Portkey. All shop facts and operations go through a FastMCP server on a SQLite working database. A FastAPI backend connects the agents to a React dashboard, where a person watches the agents work and approves any payment or purchase order before it happens.

## Project layout

```
hw5/
├── AI_prompts.md            prompts used for each problem
├── requirements.txt         Python dependencies (backend + MCP server, one venv)
├── .env.example             copy to .env and add PORTKEY_API_KEY
├── .mcp.json                MCP client config: launches mcp_server/server.py over stdio
├── data/
│   ├── campus_customs.db        original database (never modified; the reset source)
│   └── campus_customs_new.db    working copy used by the MCP server and backend
├── mcp_server/              FastMCP server (server.py) and its README
├── backend/                 FastAPI app (main.py), shared models, agents/, prompts/
├── frontend/                React + Vite + TypeScript dashboard
└── output/                  harness, smoke tests, audit trail, ticket pages, screenshots
```

`output/harness.md` documents every table, MCP tool, agent, API route, and safety rule.

> **Note:** the committed `data/campus_customs_new.db` holds the final state after the graded run: all three tickets resolved and $160.00 in checking. Follow step 3 or step 7 below to start from a clean copy.

## Requirements

- Python **3.11 or newer** (tested with 3.13). The macOS system `python3` (3.9) is too old.
- Node.js **20 or newer** (tested with 24) and npm.
- A Portkey API key for `PORTKEY_API_KEY`. Every agent uses only `gpt-6-luna`.

## Setup

Run all commands from the `hw5/` folder unless a step says otherwise.

### 1. Python environment

```bash
python3.13 -m venv .venv          # or any python 3.11+
source .venv/bin/activate         # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. API key

```bash
cp .env.example .env
# edit .env and set PORTKEY_API_KEY=<your key>
```

`.env` is ignored by git. The backend also finds a `.env` in a parent folder.

### 3. Copy the original database to the working copy (clean run)

```bash
cp data/campus_customs.db data/campus_customs_new.db
```

This gives you a working copy that matches the original: tickets 101–103 open and $3,400.00 in checking. The original `data/campus_customs.db` is never written to.

### 4. Start the MCP server

The backend starts the MCP server for you. On startup it reads `.mcp.json` and launches `python mcp_server/server.py` over stdio with the same virtual environment, so you don't need to start it separately for the dashboard.

To run it on its own (for example, to connect another MCP client), with the venv active:

```bash
python mcp_server/server.py        # speaks MCP over stdin/stdout; Ctrl+C to stop
```

Claude Code and other clients that read `.mcp.json` pick up the `campus-customs` server automatically when opened in this folder with the venv active.

### 5. Start the FastAPI backend

In a new terminal:

```bash
source .venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
```

Check it at <http://localhost:8000/api/health>. The interactive API docs are at <http://localhost:8000/docs>.

### 6. Start the React dashboard

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open <http://localhost:5173>. The header should say **Backend connected** and show the checking balance.

If port 8000 is already in use, start the backend on another port (for example `--port 8001`) and point the dashboard at it:

```bash
VITE_API_BASE=http://localhost:8001 npm run dev
```

### 7. Reset the database, then run all three tickets

1. Click **Reset desk** in the dashboard header. This calls `POST /api/reset`, which copies the original database over the working copy. Or from a terminal: `curl -X POST http://localhost:8000/api/reset`. Checking should read **$3,400.00** and all three tickets should be **Open**.
2. Select ticket **101** and click **Start agent team**. The activity feed shows each agent's steps, hand-offs, and MCP tool calls as they happen. When the run finishes, the ticket is stamped **Resolved** and each agent's summary appears.
3. Repeat for tickets **102** and **103**. Only one ticket can run at a time.
4. Payment and purchase-order requests appear under **Needs your sign-off**. Enter your name in **Signing as**, then **Approve** or **Decline** each one. Only this human step moves money. A payment that would overdraw checking is refused.

Each agent-loop step is appended to `output/audit_trail.json`. Earlier records are kept.

## API routes (backend)

| Method | URL | Purpose |
|---|---|---|
| GET | `/api/health` | Backend status and model |
| GET | `/api/agents` | The five agents and their prompt files |
| GET | `/api/tickets` | Tickets 101–103 with open/resolved status |
| POST | `/api/tickets/{id}/run` | Run the agent team on one ticket |
| GET | `/api/events` | Recent agent events (`?ticket_id=`, `?run_id=`, `?limit=`) |
| GET | `/api/approvals` | Pending payment and purchase-order requests |
| POST | `/api/approvals/{id}/approve` | Human approval; the only route that pays or approves an order |
| POST | `/api/approvals/{id}/reject` | Human rejection with a reason |
| GET | `/api/cash` | Checking balance from `cash_accounts` |
| POST | `/api/reset` | Copy the original database over the working copy |

## Safety rules

- Every payment and purchase order needs human approval in the dashboard. Agents can only create pending requests, because the approval tools are hidden from them.
- Payments that exceed available cash are refused, and the balance can never go negative. Cash only goes out; no revenue is modelled.
- Vendors with an unpaid invoice cannot ship. Lead times come from the database. Overdue checks use `desk.date_today`.
- No real customer, landlord, or vendor is contacted. Customer messages stay as drafts on the board.
- Token and loop limits apply to every agent and ticket run (see `output/harness.md`).

## Outputs

| File | Contents |
|---|---|
| `output/harness.md` | Tables, MCP tools, agents, routes, dashboard, safety rules, and verified run results |
| `output/mcp_smoke.json` | MCP tool smoke tests |
| `output/desk_tickets.html` | Expected vs. actual for each ticket, the Cash tab, and the Reflection (open in a browser) |
| `output/design.md` | Dashboard design notes |
| `output/resolved_tickets.json` | Final status, outcome, agent contributions, and approvals per ticket |
| `output/resolved_board.html` | Real dashboard screenshots of each resolved ticket (standalone page) |
| `output/audit_trail.json` | Append-only log of every agent-loop step |
| `output/github_url.txt` | URL of this repository |
