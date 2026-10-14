"""Campus Customs MCP tools for shop lookups and approval-gated operations."""

import calendar
import json
from contextlib import contextmanager
from datetime import date
from pathlib import Path
import sqlite3
from typing import Any

from fastmcp import FastMCP


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "data" / "campus_customs_new.db"
DATABASE_URI = f"{DATABASE_PATH.as_uri()}?mode=ro"

mcp = FastMCP("Campus Customs Operations")


def _fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    """Fetch one row from the working database without opening it for writes."""
    with _working_database(readonly=True) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql, params).fetchone()

    if row is None:
        raise ValueError("The requested ticket or its related records were not found.")
    return dict(row)


@mcp.tool()
def get_ticket_101_stock_and_vendor_status() -> dict[str, Any]:
    """Look up ticket 101's tee stock, pricing, linked invoice, and vendor status."""
    record = _fetch_one(
        """
        SELECT
            t.id AS ticket_id,
            t.requester,
            t.subject,
            t.sku,
            t.size,
            t.qty AS requested_quantity,
            t.status AS ticket_status,
            i.qty AS stock_quantity,
            i.location AS stock_location,
            p.unit_cost,
            p.list_price,
            invoice.id AS invoice_id,
            invoice.amount AS invoice_amount,
            invoice.due_date AS invoice_due_date,
            invoice.status AS invoice_status,
            vendor.id AS vendor_id,
            vendor.name AS vendor_name,
            vendor.specialty AS vendor_specialty,
            vendor.lead_days AS vendor_lead_days,
            desk.date_today AS shop_date,
            (
                SELECT COUNT(*)
                FROM invoices AS unpaid_invoice
                WHERE unpaid_invoice.vendor_id = vendor.id
                  AND lower(unpaid_invoice.status) <> 'paid'
            ) AS vendor_unpaid_invoice_count
        FROM tickets AS t
        LEFT JOIN inventory AS i
          ON i.sku = t.sku AND i.size = t.size
        LEFT JOIN pricing AS p
          ON p.sku = t.sku
        LEFT JOIN invoices AS invoice
          ON invoice.id = t.invoice_id
        LEFT JOIN vendors AS vendor
          ON vendor.id = invoice.vendor_id
        CROSS JOIN desk
        WHERE t.id = 101
        """
    )

    requested = record["requested_quantity"] or 0
    on_hand = record["stock_quantity"] or 0
    record["stock_shortage"] = max(requested - on_hand, 0)
    record["vendor_can_ship"] = record["vendor_unpaid_invoice_count"] == 0
    due_date = record["invoice_due_date"]
    record["invoice_overdue"] = bool(
        due_date
        and record["invoice_status"]
        and record["invoice_status"].lower() != "paid"
        and date.fromisoformat(due_date) < date.fromisoformat(record["shop_date"])
    )
    return record


@mcp.tool()
def get_ticket_102_lease_and_rent_due_date() -> dict[str, Any]:
    """Look up ticket 102's lease, rent amount, and days until its due date."""
    record = _fetch_one(
        """
        SELECT
            t.id AS ticket_id,
            t.requester,
            t.subject,
            t.status AS ticket_status,
            t.notes AS ticket_notes,
            lease.id AS lease_id,
            lease.space_name,
            lease.landlord,
            lease.monthly_rent,
            lease.next_due,
            lease.notes AS lease_notes,
            desk.date_today AS shop_date
        FROM tickets AS t
        JOIN leases AS lease
          ON lease.id = t.lease_id
        CROSS JOIN desk
        WHERE t.id = 102
        """
    )

    record["days_until_due"] = (
        date.fromisoformat(record["next_due"]) - date.fromisoformat(record["shop_date"])
    ).days
    record["rent_overdue"] = record["days_until_due"] < 0
    return record


@mcp.tool()
def get_ticket_103_bulk_hoodie_stock_and_pricing() -> dict[str, Any]:
    """Look up ticket 103's requested hoodie quantity, available stock, and margins."""
    record = _fetch_one(
        """
        SELECT
            t.id AS ticket_id,
            t.requester,
            t.subject,
            t.sku,
            t.size,
            t.qty AS requested_quantity,
            t.status AS ticket_status,
            inventory.qty AS stock_quantity,
            inventory.location AS stock_location,
            pricing.unit_cost,
            pricing.list_price
        FROM tickets AS t
        JOIN inventory
          ON inventory.sku = t.sku AND inventory.size = t.size
        JOIN pricing
          ON pricing.sku = t.sku
        WHERE t.id = 103
        """
    )

    requested = record["requested_quantity"]
    on_hand = record["stock_quantity"]
    record["stock_shortage"] = max(requested - on_hand, 0)
    record["stock_sufficient"] = on_hand >= requested
    record["list_price_total"] = round(record["list_price"] * requested, 2)
    record["unit_cost_total"] = round(record["unit_cost"] * requested, 2)
    record["gross_margin_at_list_price"] = round(
        (record["list_price"] - record["unit_cost"]) * requested, 2
    )
    return record


def _connect_working_database(*, readonly: bool = True) -> sqlite3.Connection:
    """Open only the configured working database, read-only unless a tool must record an action."""
    if not DATABASE_PATH.is_file():
        raise FileNotFoundError(f"Working database not found: {DATABASE_PATH}")
    if readonly:
        connection = sqlite3.connect(DATABASE_URI, uri=True)
    else:
        connection = sqlite3.connect(DATABASE_PATH.as_posix(), timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def _working_database(*, readonly: bool = True):
    """Close each SQLite connection after its MCP tool call and commit successful writes."""
    connection = _connect_working_database(readonly=readonly)
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def _ensure_workflow_tables(connection: sqlite3.Connection) -> None:
    """Create MCP-owned approval and draft tables in the working copy when first needed."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            request_type TEXT NOT NULL CHECK (request_type IN ('payment', 'purchase_order')),
            ref_id INTEGER,
            amount REAL,
            account TEXT,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'approved', 'rejected')),
            requested_by TEXT NOT NULL,
            requested_at TEXT NOT NULL,
            decided_by TEXT,
            decided_at TEXT,
            decision_note TEXT
        )"""
    )
    connection.execute(
        """CREATE INDEX IF NOT EXISTS idx_approval_requests_status
           ON approval_requests(status, request_type, id)"""
    )
    connection.execute(
        """CREATE TABLE IF NOT EXISTS customer_message_drafts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER NOT NULL REFERENCES tickets(id),
            drafted_by TEXT NOT NULL,
            draft_text TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status = 'draft'),
            created_at TEXT NOT NULL
        )"""
    )


def _shop_date(connection: sqlite3.Connection) -> str:
    row = connection.execute("SELECT date_today FROM desk LIMIT 1").fetchone()
    if row is None:
        raise ValueError("The shop date is missing from desk.")
    return row["date_today"]


def _unpaid_invoice_count(connection: sqlite3.Connection, vendor_id: int) -> int:
    row = connection.execute(
        "SELECT COUNT(*) AS count FROM invoices WHERE vendor_id = ? AND lower(status) <> 'paid'",
        (vendor_id,),
    ).fetchone()
    return int(row["count"])


@mcp.tool()
def get_ticket_context(ticket_id: int) -> dict[str, Any]:
    """Read a ticket and its matching inventory, pricing, invoice, vendor, lease, and cash records."""
    with _working_database() as connection:
        ticket = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            raise ValueError(f"Ticket {ticket_id} was not found.")
        ticket_data = dict(ticket)
        sku = ticket_data.get("sku")
        size = ticket_data.get("size")
        inventory = None
        pricing = None
        if sku:
            row = connection.execute(
                "SELECT * FROM inventory WHERE sku = ? AND (? IS NULL OR size = ?)",
                (sku, size, size),
            ).fetchall()
            inventory = [dict(item) for item in row]
            price_row = connection.execute("SELECT * FROM pricing WHERE sku = ?", (sku,)).fetchone()
            pricing = dict(price_row) if price_row else None
        invoice = None
        vendor = None
        if ticket_data.get("invoice_id") is not None:
            row = connection.execute("SELECT * FROM invoices WHERE id = ?", (ticket_data["invoice_id"],)).fetchone()
            invoice = dict(row) if row else None
            if invoice:
                row = connection.execute("SELECT * FROM vendors WHERE id = ?", (invoice["vendor_id"],)).fetchone()
                vendor = dict(row) if row else None
                if vendor:
                    vendor["unpaid_invoice_count"] = _unpaid_invoice_count(connection, vendor["id"])
                    vendor["can_ship"] = vendor["unpaid_invoice_count"] == 0
        lease = None
        if ticket_data.get("lease_id") is not None:
            row = connection.execute("SELECT * FROM leases WHERE id = ?", (ticket_data["lease_id"],)).fetchone()
            lease = dict(row) if row else None
        account = connection.execute("SELECT * FROM cash_accounts ORDER BY name LIMIT 1").fetchone()
        return {
            "ticket": ticket_data,
            "shop_date": _shop_date(connection),
            "inventory": inventory,
            "pricing": pricing,
            "invoice": invoice,
            "vendor": vendor,
            "lease": dict(lease) if lease else None,
            "cash_account": dict(account) if account else None,
        }


@mcp.tool()
def lookup_inventory(sku: str, size: str | None = None) -> list[dict[str, Any]]:
    """Look up actual stock rows for a SKU, optionally limited to one size."""
    sku = sku.strip()
    if not sku or len(sku) > 80:
        raise ValueError("Provide a valid SKU.")
    with _working_database() as connection:
        if size:
            rows = connection.execute(
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? AND size = ? ORDER BY size LIMIT 30",
                (sku, size.strip()),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT sku, name, size, qty, location FROM inventory WHERE sku = ? ORDER BY size LIMIT 30",
                (sku,),
            ).fetchall()
    return [dict(row) for row in rows]


@mcp.tool()
def list_vendors() -> list[dict[str, Any]]:
    """List database vendors, their lead times, specialties, and unpaid invoice status."""
    with _working_database() as connection:
        vendors = connection.execute("SELECT id, name, specialty, lead_days FROM vendors ORDER BY id").fetchall()
        result = []
        for vendor_row in vendors:
            vendor = dict(vendor_row)
            invoices = connection.execute(
                "SELECT id, amount, due_date, status, description FROM invoices WHERE vendor_id = ? ORDER BY id",
                (vendor["id"],),
            ).fetchall()
            vendor["invoices"] = [dict(row) for row in invoices]
            vendor["unpaid_invoice_count"] = sum(1 for row in invoices if row["status"].lower() != "paid")
            vendor["can_ship"] = vendor["unpaid_invoice_count"] == 0
            result.append(vendor)
    return result


@mcp.tool()
def get_cash_status(account_name: str = "checking") -> dict[str, Any]:
    """Read the selected cash balance and pending payment reservations from the working database."""
    with _working_database() as connection:
        account = connection.execute(
            "SELECT name, balance, date FROM cash_accounts WHERE name = ?", (account_name,)
        ).fetchone()
        if account is None:
            raise ValueError(f"Cash account {account_name!r} was not found.")
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        pending = 0.0
        if "approval_requests" in tables:
            row = connection.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM approval_requests "
                "WHERE status = 'pending' AND request_type = 'payment' AND account = ?",
                (account_name,),
            ).fetchone()
            pending = float(row["total"] or 0)
        return {
            "account": dict(account),
            "shop_date": _shop_date(connection),
            "pending_payment_reservations": round(pending, 2),
            "available_after_pending_requests": round(float(account["balance"]) - pending, 2),
        }


@mcp.tool()
def request_payment_approval(ticket_id: int, requested_by: str = "Accounting") -> dict[str, Any]:
    """Create a pending human approval request for a ticket's invoice or rent; never pays it."""
    with _working_database(readonly=False) as connection:
        _ensure_workflow_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        ticket = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"status": "refused", "reason": f"Ticket {ticket_id} was not found."}
        if ticket["status"].lower() != "open":
            return {"status": "refused", "reason": "Only open tickets can create a payment request."}
        if ticket["invoice_id"] is not None:
            obligation = connection.execute(
                "SELECT id AS ref_id, amount, due_date, status, vendor_id, description "
                "FROM invoices WHERE id = ?",
                (ticket["invoice_id"],),
            ).fetchone()
            kind = "invoice"
            ref_id = int(ticket["invoice_id"])
        elif ticket["lease_id"] is not None:
            obligation = connection.execute(
                "SELECT id AS ref_id, monthly_rent AS amount, next_due AS due_date, space_name "
                "FROM leases WHERE id = ?",
                (ticket["lease_id"],),
            ).fetchone()
            kind = "lease_rent"
            ref_id = int(ticket["lease_id"])
        else:
            return {"status": "refused", "reason": "This ticket does not reference a payable invoice or lease."}
        if obligation is None:
            return {"status": "refused", "reason": "The linked obligation was not found."}
        if kind == "invoice" and obligation["status"].lower() == "paid":
            return {"status": "refused", "reason": "The linked invoice is already paid."}
        if kind == "invoice":
            recorded = connection.execute(
                "SELECT id FROM payments WHERE kind = 'invoice' AND ref_id = ? LIMIT 1", (ref_id,)
            ).fetchone()
            if recorded:
                return {"status": "refused", "reason": "A payment for this invoice is already recorded."}
        account = connection.execute(
            "SELECT name, balance FROM cash_accounts ORDER BY name LIMIT 1"
        ).fetchone()
        if account is None:
            return {"status": "refused", "reason": "No cash account is available."}
        duplicate = connection.execute(
            "SELECT id FROM approval_requests WHERE status = 'pending' "
            "AND request_type = 'payment' AND ref_id = ? AND account = ? LIMIT 1",
            (ref_id, account["name"]),
        ).fetchone()
        if duplicate:
            return {"status": "pending", "request_id": duplicate["id"], "reason": "An approval request already exists."}
        reservations = connection.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM approval_requests "
            "WHERE status = 'pending' AND request_type = 'payment' AND account = ?",
            (account["name"],),
        ).fetchone()["total"]
        available = float(account["balance"]) - float(reservations or 0)
        amount = float(obligation["amount"])
        if amount <= 0:
            return {"status": "refused", "reason": "The obligation amount must be positive; no payment request was created."}
        if amount > available:
            return {
                "status": "refused",
                "reason": "Insufficient available cash; no payment request was created.",
                "cash_balance": float(account["balance"]),
                "pending_reservations": float(reservations or 0),
                "available_cash": round(available, 2),
                "requested_amount": amount,
            }
        shop_date = _shop_date(connection)
        payload = {
            "kind": kind,
            "ref_id": ref_id,
            "amount": amount,
            "due_date": obligation["due_date"],
            "description": obligation["description"] if kind == "invoice" else obligation["space_name"],
            "approval_required": True,
        }
        cursor = connection.execute(
            "INSERT INTO approval_requests "
            "(ticket_id, request_type, ref_id, amount, account, payload_json, requested_by, requested_at) "
            "VALUES (?, 'payment', ?, ?, ?, ?, ?, ?)",
            (ticket_id, ref_id, amount, account["name"], json.dumps(payload), requested_by.strip()[:80] or "Agent", shop_date),
        )
        return {
            "status": "pending_human_approval",
            "request_id": cursor.lastrowid,
            "ticket_id": ticket_id,
            "kind": kind,
            "ref_id": ref_id,
            "amount": amount,
            "account": account["name"],
            "cash_balance": float(account["balance"]),
            "available_after_request": round(available - amount, 2),
            "payment_made": False,
            "approval_required": True,
        }


@mcp.tool()
def request_purchase_order_approval(ticket_id: int, vendor_id: int, requested_by: str = "Inventory") -> dict[str, Any]:
    """Prepare a purchase order request for human approval without contacting the vendor."""
    with _working_database(readonly=False) as connection:
        _ensure_workflow_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        ticket = connection.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None or ticket["status"].lower() != "open":
            return {"status": "refused", "reason": "An open ticket was not found."}
        if not ticket["sku"] or not ticket["size"] or not ticket["qty"]:
            return {"status": "refused", "reason": "The ticket has no SKU, size, and quantity to restock."}
        stock = connection.execute(
            "SELECT qty, name, location FROM inventory WHERE sku = ? AND size = ?",
            (ticket["sku"], ticket["size"]),
        ).fetchone()
        stock_quantity = int(stock["qty"]) if stock else 0
        shortage = max(int(ticket["qty"]) - stock_quantity, 0)
        if shortage == 0:
            return {"status": "not_needed", "reason": "Database inventory covers the ticket quantity."}
        vendor_row = connection.execute(
            "SELECT id, name, specialty, lead_days FROM vendors WHERE id = ?", (vendor_id,)
        ).fetchone()
        if vendor_row is None:
            return {"status": "refused", "reason": f"Vendor {vendor_id} was not found."}
        unpaid_count = _unpaid_invoice_count(connection, vendor_id)
        if unpaid_count:
            return {
                "status": "refused",
                "reason": "The vendor has an unpaid invoice and cannot ship new products.",
                "vendor_id": vendor_id,
                "unpaid_invoice_count": unpaid_count,
            }
        duplicate = connection.execute(
            "SELECT id FROM approval_requests WHERE status = 'pending' AND request_type = 'purchase_order' "
            "AND ticket_id = ? AND ref_id = ? LIMIT 1",
            (ticket_id, vendor_id),
        ).fetchone()
        if duplicate:
            return {"status": "pending", "request_id": duplicate["id"], "reason": "An approval request already exists."}
        vendor = dict(vendor_row)
        payload = {
            "sku": ticket["sku"],
            "item_name": stock["name"] if stock else None,
            "size": ticket["size"],
            "requested_quantity": int(ticket["qty"]),
            "stock_quantity": stock_quantity,
            "order_quantity": shortage,
            "stock_location": stock["location"] if stock else None,
            "vendor": vendor,
            "vendor_unpaid_invoice_count": unpaid_count,
            "supplier_compatibility": "No SKU-to-vendor mapping exists in the database; human verification required.",
            "vendor_contacted": False,
            "vendor_quote": None,
        }
        shop_date = _shop_date(connection)
        cursor = connection.execute(
            "INSERT INTO approval_requests "
            "(ticket_id, request_type, ref_id, payload_json, requested_by, requested_at) "
            "VALUES (?, 'purchase_order', ?, ?, ?, ?)",
            (ticket_id, vendor_id, json.dumps(payload), requested_by.strip()[:80] or "Agent", shop_date),
        )
        return {
            "status": "pending_human_approval",
            "request_id": cursor.lastrowid,
            "ticket_id": ticket_id,
            **payload,
            "approval_required": True,
            "purchase_order_placed": False,
        }


@mcp.tool()
def save_customer_message_draft(ticket_id: int, draft_text: str, drafted_by: str = "Customer Service") -> dict[str, Any]:
    """Save an unsent customer message draft for display on the operations board."""
    draft_text = draft_text.strip()
    if not draft_text or len(draft_text) > 1600:
        raise ValueError("A customer message draft must contain 1 to 1600 characters.")
    with _working_database(readonly=False) as connection:
        _ensure_workflow_tables(connection)
        ticket = connection.execute("SELECT id FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"status": "refused", "reason": f"Ticket {ticket_id} was not found."}
        cursor = connection.execute(
            "INSERT INTO customer_message_drafts (ticket_id, drafted_by, draft_text, created_at) "
            "VALUES (?, ?, ?, ?)",
            (ticket_id, drafted_by.strip()[:80] or "Customer Service", draft_text, _shop_date(connection)),
        )
        return {
            "status": "draft_saved",
            "draft_id": cursor.lastrowid,
            "ticket_id": ticket_id,
            "draft_text": draft_text,
            "sent": False,
        }


@mcp.tool()
def get_pending_approvals() -> list[dict[str, Any]]:
    """List pending payment and purchase-order approval requests for the operations board."""
    with _working_database() as connection:
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "approval_requests" not in tables:
            return []
        rows = connection.execute(
            "SELECT * FROM approval_requests WHERE status = 'pending' ORDER BY id"
        ).fetchall()
    approvals = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item.pop("payload_json"))
        approvals.append(item)
    return approvals


def _next_month(value: str) -> str:
    parsed = date.fromisoformat(value)
    year = parsed.year + (parsed.month == 12)
    month = 1 if parsed.month == 12 else parsed.month + 1
    day = min(parsed.day, calendar.monthrange(year, month)[1])
    return date(year, month, day).isoformat()


@mcp.tool()
def approve_payment_request(request_id: int, approved_by: str) -> dict[str, Any]:
    """Record human approval and make one outgoing payment; rejects overdrafts and duplicate payments."""
    approved_by = approved_by.strip()
    if not approved_by or len(approved_by) > 120:
        raise ValueError("A human approver name is required.")
    with _working_database(readonly=False) as connection:
        _ensure_workflow_tables(connection)
        connection.execute("BEGIN IMMEDIATE")
        request = connection.execute(
            "SELECT * FROM approval_requests WHERE id = ? AND request_type = 'payment'",
            (request_id,),
        ).fetchone()
        if request is None or request["status"] != "pending":
            return {"status": "refused", "reason": "The pending payment request was not found."}
        balance = connection.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (request["account"],)
        ).fetchone()
        amount = float(request["amount"])
        if amount <= 0:
            return {"status": "refused", "reason": "Payment amount must be positive; no payment was made."}
        if balance is None or float(balance["balance"]) < amount:
            connection.execute(
                "UPDATE approval_requests SET status = 'rejected', decided_by = 'system', "
                "decided_at = ?, decision_note = 'Insufficient cash; payment refused.' WHERE id = ?",
                (_shop_date(connection), request_id),
            )
            return {"status": "refused", "reason": "Insufficient cash; no payment was made."}
        payload = json.loads(request["payload_json"])
        shop_date = _shop_date(connection)
        kind = payload["kind"]
        ref_id = int(payload["ref_id"])
        if kind == "invoice":
            invoice = connection.execute(
                "SELECT id, vendor_id, amount, status FROM invoices WHERE id = ?", (ref_id,)
            ).fetchone()
            if invoice is None or invoice["status"].lower() == "paid" or abs(float(invoice["amount"]) - amount) > 0.005:
                return {"status": "refused", "reason": "The invoice changed or is already paid; no payment was made."}
            duplicate = connection.execute(
                "SELECT id FROM payments WHERE kind = 'invoice' AND ref_id = ? LIMIT 1", (ref_id,)
            ).fetchone()
            if duplicate:
                return {"status": "refused", "reason": "A payment for this invoice already exists."}
        elif kind == "lease_rent":
            lease = connection.execute(
                "SELECT id, monthly_rent, next_due FROM leases WHERE id = ?", (ref_id,)
            ).fetchone()
            if (
                lease is None
                or lease["next_due"] != payload["due_date"]
                or abs(float(lease["monthly_rent"]) - amount) > 0.005
            ):
                return {"status": "refused", "reason": "The rent obligation changed; no payment was made."}
            next_due = _next_month(lease["next_due"])
        else:
            return {"status": "refused", "reason": "Unsupported payment type; no payment was made."}

        updated = connection.execute(
            "UPDATE cash_accounts SET balance = balance - ?, date = ? "
            "WHERE name = ? AND balance >= ?",
            (amount, shop_date, request["account"], amount),
        )
        if updated.rowcount != 1:
            connection.execute(
                "UPDATE approval_requests SET status = 'rejected', decided_by = 'system', "
                "decided_at = ?, decision_note = 'Insufficient cash; payment refused.' WHERE id = ?",
                (shop_date, request_id),
            )
            return {"status": "refused", "reason": "Insufficient cash; no payment was made."}
        cursor = connection.execute(
            "INSERT INTO payments (kind, ref_id, amount, account, paid_at, approved_by) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (kind, ref_id, amount, request["account"], shop_date, approved_by),
        )
        if kind == "invoice":
            connection.execute("UPDATE invoices SET status = 'paid' WHERE id = ?", (ref_id,))
        else:
            connection.execute("UPDATE leases SET next_due = ? WHERE id = ?", (next_due, ref_id))
            connection.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (request["ticket_id"],))
        connection.execute(
            "UPDATE approval_requests SET status = 'approved', decided_by = ?, decided_at = ?, "
            "decision_note = 'Approved by human; payment recorded.' WHERE id = ?",
            (approved_by, shop_date, request_id),
        )
        new_balance = connection.execute(
            "SELECT balance FROM cash_accounts WHERE name = ?", (request["account"],)
        ).fetchone()["balance"]
        return {
            "status": "payment_recorded",
            "payment_id": cursor.lastrowid,
            "request_id": request_id,
            "ticket_id": request["ticket_id"],
            "amount": amount,
            "account": request["account"],
            "new_balance": round(float(new_balance), 2),
            "approved_by": approved_by,
            "paid_at": shop_date,
            "invoice_status": "paid" if kind == "invoice" else None,
            "next_rent_due": next_due if kind == "lease_rent" else None,
        }


@mcp.tool()
def approve_purchase_order_request(request_id: int, approved_by: str) -> dict[str, Any]:
    """Approve a purchase-order proposal internally; this does not contact or place an order with a vendor."""
    approved_by = approved_by.strip()
    if not approved_by or len(approved_by) > 120:
        raise ValueError("A human approver name is required.")
    with _working_database(readonly=False) as connection:
        _ensure_workflow_tables(connection)
        request = connection.execute(
            "SELECT * FROM approval_requests WHERE id = ? AND request_type = 'purchase_order' AND status = 'pending'",
            (request_id,),
        ).fetchone()
        if request is None:
            return {"status": "refused", "reason": "The pending purchase-order request was not found."}
        payload = json.loads(request["payload_json"])
        vendor_id = int(request["ref_id"])
        unpaid_count = _unpaid_invoice_count(connection, vendor_id)
        if unpaid_count:
            return {"status": "refused", "reason": "Vendor now has an unpaid invoice; no order was placed."}
        shop_date = _shop_date(connection)
        connection.execute(
            "UPDATE approval_requests SET status = 'approved', decided_by = ?, decided_at = ?, "
            "decision_note = 'Approved internally; no vendor contacted.' WHERE id = ?",
            (approved_by, shop_date, request_id),
        )
        return {
            "status": "approved_for_manual_follow_up",
            "request_id": request_id,
            "ticket_id": request["ticket_id"],
            "vendor_id": vendor_id,
            "vendor_contacted": False,
            "order_placed": False,
            "supplier_compatibility": payload.get("supplier_compatibility"),
        }


@mcp.tool()
def reject_approval_request(request_id: int, rejected_by: str, reason: str) -> dict[str, Any]:
    """Reject a pending payment or purchase-order request without changing shop cash or contacting anyone."""
    rejected_by = rejected_by.strip()
    reason = reason.strip()
    if not rejected_by or not reason or len(rejected_by) > 120 or len(reason) > 500:
        raise ValueError("Provide a human reviewer and a short rejection reason.")
    with _working_database(readonly=False) as connection:
        _ensure_workflow_tables(connection)
        row = connection.execute(
            "SELECT id FROM approval_requests WHERE id = ? AND status = 'pending'", (request_id,)
        ).fetchone()
        if row is None:
            return {"status": "refused", "reason": "The pending request was not found."}
        connection.execute(
            "UPDATE approval_requests SET status = 'rejected', decided_by = ?, decided_at = ?, decision_note = ? "
            "WHERE id = ?",
            (rejected_by, _shop_date(connection), reason, request_id),
        )
        return {"status": "rejected", "request_id": request_id, "rejected_by": rejected_by, "reason": reason}


@mcp.tool()
def mark_ticket_resolved(ticket_id: int) -> dict[str, Any]:
    """Mark an open ticket resolved after the agent team finishes; backend-only, hidden from agents."""
    with _working_database(readonly=False) as connection:
        ticket = connection.execute("SELECT id, status FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
        if ticket is None:
            return {"status": "refused", "reason": f"Ticket {ticket_id} was not found."}
        if ticket["status"].lower() == "resolved":
            return {"status": "resolved", "ticket_id": ticket_id, "changed": False}
        connection.execute("UPDATE tickets SET status = 'resolved' WHERE id = ?", (ticket_id,))
        return {"status": "resolved", "ticket_id": ticket_id, "changed": True}


if __name__ == "__main__":
    # stdio is the protocol channel; keep stderr quiet (expected "not found" refusals are not crashes).
    mcp.run(transport="stdio", show_banner=False, log_level="CRITICAL")
