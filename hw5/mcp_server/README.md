# Campus Customs MCP Server

The FastMCP server provides the only path for agent shop lookups and operations. It uses `../data/campus_customs_new.db`; the source `campus_customs.db` is never opened for writes. Each database connection is closed after its tool call.

## Read tools

- `get_ticket_101_stock_and_vendor_status` — ticket 101 stock, pricing, linked invoice, vendor lead time, shop date, and shipping eligibility.
- `get_ticket_102_lease_and_rent_due_date` — ticket 102 lease, rent amount, and days until the next due date.
- `get_ticket_103_bulk_hoodie_stock_and_pricing` — ticket 103 size-M stock, shortage, and cost/margin at list price.
- `get_ticket_context` — current ticket and matching inventory, pricing, invoice, vendor, lease, cash-account, and shop-date records.
- `lookup_inventory` — actual inventory rows by SKU and optional size.
- `list_vendors` — database vendors, specialties, lead times, and unpaid invoices that block shipping.
- `get_cash_status` — account balance and reservations from pending payment proposals.
- `get_pending_approvals` — pending payment and purchase-order proposals for the operations board.

## Proposal and draft tools

- `request_payment_approval` — validates a ticket-linked invoice or rent obligation and available cash, then stores a pending request. It does not make a payment.
- `request_purchase_order_approval` — checks shortage and unpaid invoices, then stores an internal restock proposal. It does not place an order or contact a vendor.
- `save_customer_message_draft` — stores an unsent draft against a ticket.

These tools lazily create `approval_requests` and `customer_message_drafts` in the working database. They never modify the original database.

## Human-only decision tools

- `approve_payment_request` — rechecks cash in a transaction, refuses an overdraft, records the payment and approver, decreases cash, and updates the linked invoice or lease.
- `approve_purchase_order_request` — approves a proposal for manual follow-up only; it does not contact a vendor or place an order.
- `reject_approval_request` — records a human rejection without making a payment.

## Backend-only tool

- `mark_ticket_resolved` — sets a ticket's status to `resolved`; called by the backend run route after a finished agent run.

The PydanticAI agent toolsets filter these human-only and backend-only tools out. Payment and purchase-order request tools are visible only to Accounting, and the draft tool only to Customer Service. The project-root `.mcp.json` launches the server over stdio with `python mcp_server/server.py` from the project root, using the same `.venv` as the backend (the backend resolves `python` to its own interpreter). Built with FastMCP (`fastmcp` package).
