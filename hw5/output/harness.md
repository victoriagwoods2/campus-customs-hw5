# Campus Customs Database Harness

Reference for the Campus Customs multi-agent operations system: the database, MCP server, five PydanticAI agents, FastAPI routes, React dashboard, safety rules, and the verified results of resolving tickets 101–103.

## Database files

- `data/campus_customs.db` is the extracted source database and remains the reset copy.
- `data/campus_customs_new.db` is the working database used by the MCP server and backend. The two files had the same SHA-256 hash when the working copy was created.
- MCP workflow tables `approval_requests` and `customer_message_drafts` are created lazily in the working database when an agent first requests an approval or saves a draft. They are not part of the untouched source database.

## Database tables and fields

- **`cash_accounts`** — `name`, `balance`, `date`. Accounting checks that an approved payment fits the available balance. Seed row: checking, $3,400.00, dated 2026-08-31.
- **`desk`** — `date_today`, `notes`. All overdue checks use this shop-controlled date. Seed value: 2026-08-31.
- **`inventory`** — `sku`, `name`, `size`, `qty`, `location`. Inventory checks stock and shortages by SKU and size.
- **`invoices`** — `id`, `vendor_id`, `amount`, `due_date`, `status`, `description`. Accounting tracks obligations here; an unpaid invoice blocks its vendor from shipping.
- **`leases`** — `id`, `space_name`, `landlord`, `monthly_rent`, `next_due`, `notes`. Facilities checks rent terms and upcoming or overdue dates.
- **`payments`** — `id`, `kind`, `ref_id`, `amount`, `account`, `paid_at`, `approved_by`. Approved outgoing payments are recorded here.
- **`pricing`** — `sku`, `unit_cost`, `list_price`. Accounting calculates margins and reviews price overrides from these values.
- **`tickets`** — `id`, `type`, `requester`, `subject`, `sku`, `size`, `qty`, `lease_id`, `invoice_id`, `status`, `notes`, `created_at`. Boss uses the request and linked records to assign work and make a final recommendation.
- **`vendors`** — `id`, `name`, `specialty`, `lead_days`. Inventory checks vendor specialty and lead time. The database has no SKU-to-vendor mapping, so compatibility may need human verification.
- **`approval_requests`** — `id`, `ticket_id`, `request_type`, `ref_id`, `amount`, `account`, `payload_json`, `status`, `requested_by`, `requested_at`, `decided_by`, `decided_at`, `decision_note`. MCP stores pending payment and purchase-order proposals here for human review; only the working copy receives this table.
- **`customer_message_drafts`** — `id`, `ticket_id`, `drafted_by`, `draft_text`, `status`, `created_at`. Customer Service stores unsent drafts for the operations board here.

## Desk tickets and related records (starting state)

As loaded from `data/campus_customs.db`, before any run. The shop date is 2026-08-31 from `desk.date_today`.

- **Ticket 101 — Bulldog tee:** Tauhid Zaman requests one `CC-TEE-WHITE` in size S. Inventory has 0; the pricing row has $8.00 unit cost and $28.00 list price. The ticket references invoice 501, open for $840.00 and due 2026-08-28. Invoice 501 references vendor 1, Bulldog Print Co., whose database lead time is five days. The unpaid invoice blocks shipment.
- **Ticket 102 — Rent due:** Elm City Properties sent a rent notice. The ticket references lease 1 for the Chapel Street shop: monthly rent is $2,400.00 and next due is 2026-09-02, two days after the shop date.
- **Ticket 103 — Bulk hoodie discount:** Yale AI Club requests 20 `CC-HOOD-NAVY` hoodies in size M. Inventory has 8, leaving a shortage of 12. The SKU pricing row shows $22.00 unit cost and $58.00 list price; it implies a $720.00 gross margin at list price for 20 units before any discount, without accounting for the stock shortage.

Ticket-to-lease and ticket-to-invoice links are declared foreign keys. Ticket-to-inventory and ticket-to-pricing SKU joins use matching values but are not declared foreign keys.

## Agents

| Agent | Responsibility | Prompt |
|---|---|---|
| Boss | Reads each ticket, assigns work, reviews findings, and makes final recommendations. | `backend/prompts/boss.md` |
| Inventory | Checks SKU/size stock, shortages, vendors, unpaid invoices, and lead times. | `backend/prompts/inventory.md` |
| Accounting | Tracks cash, invoices, and margins; prepares payment or purchase-order requests for approval. | `backend/prompts/accounting.md` |
| Facilities | Handles shop space, leases, landlords, and rent. | `backend/prompts/facilities.md` |
| Customer Service | Drafts customer messages from verified facts. | `backend/prompts/customer_service.md` |

Every agent can delegate to each of the other four agents, but each prompt tells it to delegate only when another agent's expertise is needed. Boss explains which agent it starts with and why, and does not give the same task to two agents. Delegation is bounded by the run limits below.

## MCP tools

| Tool | Database tables (read / write) | Access | Ticket use |
|---|---|---|---|
| `get_ticket_101_stock_and_vendor_status` | R: `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `desk` | Read | 101: tee shortage, price, linked unpaid invoice, vendor lead time, and overdue status. |
| `get_ticket_102_lease_and_rent_due_date` | R: `tickets`, `leases`, `desk` | Read | 102: lease terms and days until rent is due. |
| `get_ticket_103_bulk_hoodie_stock_and_pricing` | R: `tickets`, `inventory`, `pricing` | Read | 103: requested quantity versus size-M stock and margin at list price. |
| `get_ticket_context` | R: `tickets`, `inventory`, `pricing`, `invoices`, `vendors`, `leases`, `cash_accounts`, `desk` | Read | Any ticket: gives Boss and specialists its current linked shop context. |
| `lookup_inventory` | R: `inventory` | Read | Any SKU/size request: returns actual on-hand stock and location. |
| `list_vendors` | R: `vendors`, `invoices` | Read | Restock work: shows each database lead time, specialty, and unpaid-invoice shipping block. |
| `get_cash_status` | R: `cash_accounts`, `desk`, `approval_requests` (when present) | Read | Payment planning: returns the balance and pending-request reservations. |
| `request_payment_approval` | R: `tickets`, `invoices`, `leases`, `cash_accounts`, `approval_requests`, `desk`; W: `approval_requests` | Proposal | Tickets with a linked invoice or lease: stores a pending human approval request after checking available cash. Does not pay. |
| `request_purchase_order_approval` | R: `tickets`, `inventory`, `vendors`, `invoices`, `approval_requests`, `desk`; W: `approval_requests` | Proposal | Stock shortage: stores an internal restock proposal, only if the selected vendor has no unpaid invoice. No vendor is contacted. |
| `save_customer_message_draft` | R: `tickets`, `desk`; W: `customer_message_drafts` | Draft | Any ticket: saves a message for the board, always unsent. |
| `get_pending_approvals` | R: `approval_requests` | Read | Returns pending payment and purchase-order proposals for the board. |
| `approve_payment_request` | R/W: `approval_requests`, `cash_accounts`, `payments`, `invoices`, `leases`, `tickets`, `desk` | Human only | A human-approved payment is recorded atomically; cash decreases, the obligation is updated, and overdrafts are refused. |
| `approve_purchase_order_request` | R/W: `approval_requests`, `vendors`, `invoices`, `desk` | Human only | Marks an internally approved proposal ready for manual follow-up; it never contacts a vendor or places an order. |
| `reject_approval_request` | R/W: `approval_requests`, `desk` | Human only | Records a human rejection without changing cash or contacting anyone. |
| `mark_ticket_resolved` | R/W: `tickets` | Backend only | Called by the run route after a finished agent run to set the desk ticket to `resolved`; hidden from agents. |

## Backend routes

`backend/main.py` (FastAPI). All shop reads and approval decisions go through the MCP server on `data/campus_customs_new.db`; the original database is only read by the reset route. Local CORS allows `http://localhost:*` and `http://127.0.0.1:*`, which includes the Vite dashboard at `http://localhost:5173`.

- `GET /api/health` — Confirms the backend is up and reports the model (`gpt-6-luna`).
- `GET /api/agents` — Lists the five agents, their responsibilities, and prompt files.
- `GET /api/tickets` — Returns tickets 101, 102, and 103 with their current status (`open` or `resolved`).
- `POST /api/tickets/{ticket_id}/run` — Runs the agent team on one desk ticket. When the run finishes (status completed, needs human approval, or blocked), the ticket is marked `resolved` and `ticket_status` is returned; errors and budget stops leave it open. Returns 404 for tickets other than 101–103, 409 if the ticket is already resolved or another run is in progress.
- `GET /api/events?limit=&ticket_id=&run_id=` — Returns recent agent-loop events from `output/audit_trail.json`: the agent, what it said, the tools it used, and who it delegated to.
- `GET /api/approvals` — Lists pending payment and purchase-order requests prepared by agents.
- `POST /api/approvals/{request_id}/approve` — The only path that carries out a payment or purchase order (body: `approved_by`). Payments update `cash_accounts`, `payments`, and the linked invoice or lease. Returns 404 for an unknown request and 409 for insufficient cash or a changed obligation.
- `POST /api/approvals/{request_id}/reject` — Records a human rejection (body: `rejected_by`, `reason`) without moving money.
- `GET /api/cash` — Returns the checking balance from `cash_accounts`, plus pending reservations.
- `POST /api/reset` — Copies `data/campus_customs.db` over the working database so tickets can run again from the start. Refused while a ticket run is in progress; the audit trail is kept.

## Dashboard

`frontend/` is a React + Vite + TypeScript dashboard that calls the routes above at `http://localhost:8000` (override with `VITE_API_BASE`). It lists the desk tickets, starts runs, polls `GET /api/events` every 1.5s during a run, shows per-agent summaries, lets a person approve or decline pending requests, and refreshes the checking balance after approvals. Design notes are in `output/design.md`.

## Shop safety rules

These rules are written into the agent prompts and enforced in code where possible.

1. **Shop date:** `desk.date_today` (2026-08-31) is the current date for every overdue or due-soon check.
2. **Vendor lead times** come from `vendors.lead_days`. A vendor with any unpaid invoice cannot ship new products. `request_purchase_order_approval` and `approve_purchase_order_request` both refuse in that case.
3. **Every payment needs human approval.** Agents can only create pending requests. Only `POST /api/approvals/{id}/approve`, triggered by a person in the dashboard, calls `approve_payment_request`.
4. **No overspending:** a payment is refused if it exceeds available cash, both when requested and again when approved. The balance can never go negative.
5. **Cash only goes out.** No incoming revenue is modelled.
6. **Reset before a full run:** `POST /api/reset` (the dashboard's Reset desk button) copies the original database over the working copy.
7. **No real contact:** customer messages stay as drafts on the board. No customer, landlord, or vendor is emailed or contacted.
8. **Only `gpt-6-luna` through Portkey**, authenticated with `PORTKEY_API_KEY`.

## Safety mechanisms and token limits

- Every agent receives the read tools, but the three human-only decision tools and the backend-only `mark_ticket_resolved` are filtered out of all agent toolsets, so no agent can approve or reject a proposal or close a ticket.
- Proposal and draft tools are limited to one role each: only Accounting can call `request_payment_approval` and `request_purchase_order_approval`, and only Customer Service can call `save_customer_message_draft`. Inventory and Facilities hand payment and purchase-order details to Accounting by delegation.
- Each agent prompt in `backend/prompts/` repeats the shop safety rules relevant to that role.
- Payment proposals do not change cash. Approval rechecks the current balance inside a SQLite transaction, refuses insufficient cash, subtracts the payment without allowing a negative balance, writes the payment and approver, and updates the linked invoice or rent due date. No incoming revenue is recorded.
- Purchase orders remain internal proposals. Vendor lead times and unpaid invoices come from the database; when a product-to-vendor match is not represented there, the proposal says human verification is required. No real vendor or customer is contacted.
- Customer messages are persisted as drafts only. Audit entries are appended one loop step at a time; prior JSON records are preserved. They include visible actions and tool results, not hidden model reasoning.
- Each agent is limited to 6 model requests, 12 tool calls, and 20,000 tokens per invocation. Each ticket run is limited to 100 loop steps, 40 model requests, 40 tool calls, 60,000 total tokens, 8 delegations, and delegation depth 4. When a limit is reached, the agent stops and reports `budget_limit` instead of continuing.

## Ticket resolution results (Prompt 9, 2026-10-12)

Before the runs, the working database was reset from the original using the dashboard (it matched by SHA-256) and checking was **$3,400.00**. Each ticket was started from the React dashboard. Both payment requests were approved by a person (V. Woods) on the dashboard's sign-off cards. The 146 new audit records were appended after the 91 existing ones in `output/audit_trail.json`, which were left unchanged.

| Ticket | Run | Agents (first → others) | Requests and human decision | Cash change | Final status |
|---|---|---|---|---|---|
| 101 Bulldog tee | `aa3854d2`, 102s | Boss → Inventory → Accounting; Boss → Customer Service (→ Inventory re-check) | #1 payment $840.00, invoice 501: approved by V. Woods | −$840.00 | resolved |
| 102 Rent due | `9fc64d79`, 22s | Boss → Facilities → Accounting | #2 payment $2,400.00, lease 1 rent: approved by V. Woods | −$2,400.00 | resolved |
| 103 Bulk hoodie discount | `ff6dc368`, 39s | Boss → Inventory and Customer Service (in parallel) | None. A 10% discount ($52.20 each) is recommended for a human to decide | $0.00 | resolved |

**Verified against `data/campus_customs_new.db` after the runs:**

- `tickets`: 101, 102, and 103 are all `resolved`.
- `cash_accounts`: checking = **160.0**, and $3,400.00 − $840.00 − $2,400.00 = $160.00.
- `payments`: two rows, `invoice` 501 for 840.0 and `lease_rent` 1 for 2400.0, both `approved_by = V. Woods`.
- `invoices`: 501 is `paid`, so Bulldog Print Co can ship again. `leases`: lease 1 `next_due` = 2026-10-02.
- `approval_requests`: #1 and #2 are `approved`, decided by V. Woods. No purchase-order requests were made.
- `customer_message_drafts`: draft 1 (ticket 101) and draft 2 (ticket 103), both `draft` (unsent).

**Open items and limitations found during the runs:**

- Ticket 101 is resolved at the desk level and its blocking invoice is paid, but no restock purchase order was created in the run, so the size-S tee has not been reordered yet.
- Ticket 103's discount is only a recommendation. No MCP tool records an approved price override.
- Ticket 103 did not involve Accounting as planned. Inventory weighed the discount margin instead (see `output/desk_tickets.html`).
- No MCP tool reads the `payments` table directly. Facilities relies on lease due dates and the duplicate check inside `request_payment_approval`.

## Output files

- `output/harness.md`: this document.
- `output/mcp_smoke.json`: MCP smoke tests from Prompt 4.
- `output/audit_trail.json`: append-only record of every agent-loop step.
- `output/desk_tickets.html`: expected plan versus actual result for each ticket, plus the Cash tab.
- `output/resolved_tickets.json`: final status, outcome, each agent's contribution, and human approvals per ticket.
- `output/resolved_board.html` and `output/screenshots/`: real dashboard screenshots of each resolved ticket and of both approvals.
- `output/design.md`: dashboard design notes.
