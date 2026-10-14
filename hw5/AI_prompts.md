# AI Prompts

## Problem 1 — Vibe Coder Prompts

**Prompt:**

Create `AI_prompts.md` now and keep it updated throughout the assignment. Use it to record the prompts I give you, rewritten in my own words as much as possible.

Add one section for each problem. Include the problem number and title, at least one prompt, and any follow-up prompt if needed. If you add a follow-up, include one sentence explaining what the first prompt was missing.

## Problem 2 — Study the Campus Customs Database

**Prompt:**

Inspect `data/campus_customs.db`. Review every table and its fields, then examine the three open tickets and the related records they connect to. Do not modify the original database.

Copy the original database to `data/campus_customs_new.db` for later problems to use as the working copy.

Create `output/harness.md`. For every database table, list its fields and add one short sentence explaining why the table matters to the agents. Also briefly note how the three open tickets relate to other tables. We'll add to this file in later problems.

**Follow-up prompt:**

Theres now a data.zip in the folder. unzip it and then redo that. be sure to update ai prompts md with this issue.

The first prompt didn't account for the original database not being in the folder yet, so the review and copy had to be redone after `data.zip` was added and unzipped.

## Problem 3 — Build the MCP Server

**Prompt:**

Create an MCP server in `mcp_server/` using FastMCP. It should use the working database at `data/campus_customs_new.db`. Do not connect to or run the server yet.

Create three clearly named tools that help resolve the open tickets 101, 102, and 103. Choose the tools based on the tickets and database schema you inspected in P2. Tools must retrieve real information from the database; do not invent data.

Update `output/harness.md` with each tool's name, the table it reads, the ticket it helps with, and one sentence explaining why it is useful for that specific ticket.

Add `mcp_server/README.md` explaining the server's purpose, which database file it uses, and what the three tools do.

## Problem 4 — Connect and Test the MCP Server

**Prompt:**

Configure this vibe-coding environment to use the MCP server from this project. Save its connection settings as valid JSON in `.mcp.json` at the project root, or use the configuration format this environment requires.

Then use the connected server to test each of the three MCP tools. For every test, record in `output/mcp_smoke.json`:
- The prompt you gave the vibe coder
- The tool name it called
- The tool's actual output

Run the tools and use their real outputs; do not make up results. Check that the returned values match `data/campus_customs_new.db`.

## Problem 5 — Build the Agent Team and Expand the MCP Tools

**Prompt:**

Build the Campus Customs agent team using PydanticAI: Boss, Inventory, Accounting, Facilities, and Customer Service. Use `PORTKEY_API_KEY` and only `gpt-6-luna` through Portkey for every agent. Give the agents loops and full connectivity so any agent can delegate to any other agent.

I will provide the role instructions for each agent. Use my instructions to create one prompt file per agent in `backend/prompts/`. Keep the meaning of my instructions, and show me the prompt files so I can review and revise them. Put shared data types in `backend/models.py` and agent code under `backend/`, with a clear layout for all five roles.

Add any MCP tools the agents need to resolve the open tickets. Shop facts and operations must go through the MCP server using `data/campus_customs_new.db`; do not add a separate shop-tools layer or invent data.

Follow these shop rules:
- Use `desk.date_today` to determine what is overdue.
- Use vendor lead times from the database. Vendors cannot ship while they have an unpaid invoice.
- Require human approval for every payment. Refuse payments when cash is insufficient; never allow a negative balance.
- Cash only goes out; do not model incoming revenue.
- Keep customer messages as drafts. Do not contact real customers or vendors.

Append an audit record to `output/audit_trail.json` for every agent-loop step, with enough detail to review the agent's action and result. Preserve existing records; do not overwrite the file on each run.

Update `output/harness.md` to list each agent and every MCP tool, including tools added now. For every tool, identify the database table it uses. Add a short safety section covering safeguards for real customers and money, plus limits to control token use.

Update `mcp_server/README.md` so its tool list matches the current MCP server.

**Follow-up prompt:**

Can you rerun prompt 5 because it was taking too long. so i switched to claude code. and include this detailed context it wanted. and then update ai prompts md

Use these role instructions when drafting the five agent prompts. Base all facts on MCP results and the working database. Agents should delegate only when another agent's expertise is needed.

- Boss: Review the ticket and available facts, choose the best agent to start with, and explain why. Delegate focused tasks to relevant specialists, then combine their findings into a resolution plan. Do not send every ticket to every agent.
- Inventory: Check relevant products by SKU and size. Identify shortages and check vendor lead times and unpaid invoices before recommending a restock. Give Accounting the details it needs to prepare a purchase order.
- Accounting: Check cash, invoices, costs, and margins relevant to the ticket. Prepare payment or purchase order requests when needed. Never make a payment without human approval, and never allow spending beyond available cash.
- Facilities: Handle tickets about the shop's space, leases, or rent. Check lease terms, due dates, and payment records; use `desk.date_today` to assess whether rent or another obligation is overdue.
- Customer Service: Draft clear, accurate customer messages based on confirmed information. Keep drafts on the board; never send them.

Include the relevant shop safety rules in each agent's prompt. Show me the resulting prompt files so I can review and edit them.

The first prompt said I would provide each agent's role instructions but didn't include them, so the agent prompts couldn't be finished until I sent the actual instructions for each role.

## Problem 6 — Plan the Three Tickets

**Prompt:**

Prompt 6: Plan the three tickets

Before running the agents to resolve tickets, inspect tickets 101, 102, and 103 in `data/campus_customs_new.db`, their relevant related records, the five agent prompts, and the available MCP tools.

Create `output/desk_tickets.html` as a standalone page that opens by double-clicking it. Add tabs for tickets 101, 102, and 103, plus Cash and Reflection tabs that say "Coming later."

For each ticket, fill in an "Expected" section in clear language. Based on the actual ticket information, explain:
- Which agent the Boss should delegate to first, and why
- Which other agents should be brought in, in what order, and why each is needed
- Which available MCP tools you expect the agents to use

Make each plan specific to its ticket. Don't send every specialist to every ticket, invent facts, or guess tool names. Leave an empty "Actual" section on each ticket tab for me to complete after the agents run. Do not run the agents or resolve the tickets yet.

## Problem 7 — Add Backend Routes

**Prompt:**

Prompt 7: Add backend routes

In `backend/main.py`, create a FastAPI app that connects the React dashboard to the agent team and MCP server. Use the working database, `data/campus_customs_new.db`; keep the original database unchanged.

Add routes to:
- Return tickets 101, 102, and 103 with their current open or resolved status.
- Accept a ticket ID and run the agent team on that ticket.
- Return recent agent events, including what each agent said and which tools it used.
- Approve a payment or purchase after a human requests approval. Agents may prepare these requests, but only this route should carry them out and update the relevant database records. Refuse payments that exceed available cash.
- Return the current checking balance from `cash_accounts`.
- Reset the working database to the original values so tickets can be run again from the beginning.

Choose clear HTTP methods and URL paths, and handle invalid ticket IDs, approval requests, and insufficient funds safely. Enable local CORS as needed so the React dashboard can call the backend.

In `output/harness.md`, list every route on its own line with its method, URL, and purpose.

From the `backend/` directory, start the server with:

`uvicorn main:app --reload --port 8000`

Confirm it starts successfully at `http://localhost:8000`.

## Problem 8 — Build the Agent Dashboard

**Prompt:**

Prompt 8 Build the agent dashboard

Build a React + Vite + TypeScript dashboard in `frontend/`. Connect it to the backend at `http://localhost:8000` using the routes implemented in P7. Allow the Vite origin, usually `http://localhost:5173`, in the backend's CORS settings.

The dashboard must:
- List tickets 101, 102, and 103, with their current status.
- Let a person select a ticket and start the agent team on it.
- Show agent activity and tool use while a ticket is running. Refresh activity using the events route from P7.
- Mark the ticket resolved when the backend reports that the run finished, and show a short summary of each agent's work.
- Show pending payment or purchase requests and let a person approve them.
- Display the checking balance and refresh it after an approved payment.

Use the actual backend routes and response formats from P7. Include clear loading, error, and approval states.

Make the dashboard polished, welcoming, and distinctive, like a real operations desk people would enjoy using. Give the ticket list, agent activity, approvals, and cash balance a clear visual hierarchy. Make each agent's activity easy to distinguish, and make resolved tickets and balance changes easy to notice.

Write `output/design.md` describing the layout, visual style, how agent activity is distinguished, how resolved tickets and cash are shown, and why these choices make the dashboard useful and enjoyable.

From `frontend/`, start the dashboard with `npm run dev` and confirm it loads and can reach the backend.

## Problem 9 — Resolve the Tickets

**Prompt:**

Prompt 9: Resolve the tickets

Before running any tickets, reset `data/campus_customs_new.db` from the original `data/campus_customs.db`. Record the checking balance after the reset. Then run tickets 101, 102, and 103 from the React dashboard until each is resolved.

Use the dashboard's human approval flow for any payment or purchase request. Do not bypass approval or mark a request approved without my approval. Append the actual run events to `output/audit_trail.json`; preserve the existing audit records.

Update `output/desk_tickets.html` with the results from this run:
- Keep each ticket's Expected section.
- Fill its Actual section with which agents worked, what they delegated, and which MCP tools they used.
- On the Cash tab, list the starting checking balance, each ticket's cash change and the reason for it (including the payment or purchase and amount), and the ending balance. Verify that the ending balance matches `cash_accounts` in the working database.

Also create:
- `output/resolved_tickets.json`, with each ticket's ID, final status, short outcome, each agent's contribution, and any human approvals.
- `output/resolved_board.html`, a standalone page with a genuine React dashboard screenshot for each resolved ticket. Do not fabricate screenshots.

Finish `output/harness.md` so it documents the database tables, all MCP tools, the five agents, API routes, dashboard, and safety rules. Verify the cash math and ticket statuses against the working database. Do not invent run results; if a ticket cannot be resolved, report what blocked it.

**Follow-up prompt (approval decision):**

Approve $840.00 (request #1, ticket 101). Approve $2,400.00 (request #2, ticket 102). Sign as V. Woods.

The first prompt required my approval for payments but couldn't give it in advance, because the requests and their amounts only existed after the agent runs. So I approved each one, and gave the signing name, once the dashboard showed them.

## Problem 10 — Complete the Reflection

**Prompt:**

Prompt 10: Complete the reflection
Open output/desk_tickets.html| and fill the Reflection tab. I've answered the following questions, but confirm that the answers are accurate and reflect what occurred. Make any changes and polish answers if needed, but point out what was changed. Use the Expected and Actual sections on the ticket tabs, the Cash tab, and the actual run records as evidence. 

Questions: 
1. How would you evaluate the performance of the agents on each ticket and why?
2. For each ticket, how did Actual compare to the Expected plan you wrote earlier?
3. What would have been simpler as one agent with tools and why?
4. Describe three new problems Campus Customs might face that this agent team could solve with the tools you built
5. Describe three new problems Campus Customs might face that this agent team could not solve with the tools you built, and explain the tools and agents you would need to solve them

Answers:
1.  

Ticket 101: The agents found the important blocker: there was no size-S tee in stock, and Bulldog Print Co. could not ship while invoice 501 was unpaid. Inventory and Accounting handled the stock and payment issue, and Customer Service saved a draft. The $840 payment cleared the invoice. But the ticket was marked resolved without creating a purchase order, so the tee was still not restocked. The team handled the financial blocker but did not fully complete the customer's request.
Ticket 102: This was the clearest run. Boss delegated to Facilities to check the lease and due date, then Accounting prepared the $2,400 rent payment request. I approved it on the dashboard, and the lease's next due date updated to October 2. The rent was paid, but the payment left only $160 in checking, so the cash tab is important evidence of the tradeoff.
Ticket 103: Inventory correctly found that the shop had only 8 of the 20 medium hoodies requested, and Customer Service saved a draft. The team recommended a 10% discount, or $52.20 per hoodie. But Accounting was supposed to review the margin and was not involved. The discount also remained only a recommendation, and the 12-unit shortage was not resolved. As with ticket 101, "resolved" overstated what had actually been completed.

2. 

Ticket 101: The actual run followed the expected path: Boss started with Inventory, then brought in Accounting to handle the unpaid invoice and payment request. Customer Service also drafted a message, and Inventory rechecked the issue. The main gap was that no purchase order was created after the invoice was paid, so the tee was not reordered.
Ticket 102: The run matched my expected plan: Boss sent the ticket to Facilities first to check the lease, then Accounting prepared the rent payment request. I approved it through the dashboard. That was a focused delegation, and the rent was paid without involving agents who were not needed.
Ticket 103: This was the biggest difference. I expected Accounting to help assess the discount's effect on margin, along with Inventory checking stock and Customer Service preparing a draft. Instead, Boss sent Inventory and Customer Service in parallel, and Inventory considered the discount itself. The result was a recommendation, but no Accounting review, price update, or purchase order to address the shortage.

3. Ticket 102 could have been simpler with one agent that had both Facilities and Accounting tools. It only needed to check the lease's due date, check available cash, and prepare a rent payment request. A single agent could do those steps in sequence without passing the ticket between specialists. A human would still need to approve the payment.

4. 
a. If the shop received another rent notice, Facilities could check the lease and due date using get_ticket_context, while Accounting checked the available cash with get_cash_status and prepared a payment request with request_payment_approval. A person would still review and approve the payment.

b. If a customer asked whether a specific hoodie size was in stock, Inventory could use lookup_inventory to check the quantity. Customer Service could then use save_customer_message_draft to prepare a reply based on the confirmed stock information.

c. If a vendor could not ship because it had an unpaid invoice, Inventory could use list_vendors to check the vendor's lead time and invoice status. Accounting could check the cash balance and prepare a payment request, which a person could approve to clear the block.

5. 
a. The team could prepare an internal restock proposal, but it could not place an order with a vendor or track when the shipment would arrive. That would require tools for submitting purchase orders and tracking deliveries, plus a procurement or fulfillment agent.

b. The team could recommend a customer discount, but it could not record an approved discount or change the price on an order. That would require a human-approved pricing tool that updates the relevant records, with Accounting checking the margin and a Sales or Merchandising agent handling the request.

c. The team could not process a product return or refund because it has no customer-order, return, or refund records or tools. It would need tools to look up orders, record returns, and prepare approved refunds, with Customer Service and Accounting involved.

note: 
Tie every answer to this app and the three tickets you ran - use the ticket tabs and Cash tab on the same page as your evidence. Keep the existing ticket and Cash tabs intact. Make the Reflection tab easy to read, with a separate section for each question.

## Problem 11 — Submit the Project to GitHub

**Prompt:**

Before moving to 11, can you confirm that everything looks as it should and i have everything i need? then you can confirm with these instructions 

Problem 11: Submit the project to GitHub

Prepare the project in a folder named `hw5/` and push it to a public GitHub repository so graders can clone and run it. Include both `data/campus_customs.db` and `data/campus_customs_new.db`. Do not commit `.env`, API keys, or other secrets; include `.env.example` with placeholders and a `.gitignore` that excludes secrets, virtual environments, dependencies, and generated files.

Make sure the repository contains this required structure:

```
hw5/
├── AI_prompts.md
├── requirements.txt
├── .env.example
├── .gitignore
├── .mcp.json
├── README.md
├── data/
│   ├── campus_customs.db
│   └── campus_customs_new.db
├── mcp_server/
│   ├── server.py
│   └── README.md
├── backend/
│   ├── main.py
│   ├── models.py
│   └── prompts/
│       ├── boss.md
│       ├── inventory.md
│       ├── accounting.md
│       ├── facilities.md
│       └── customer_service.md
├── frontend/
└── output/
    ├── harness.md
    ├── mcp_smoke.json
    ├── desk_tickets.html
    ├── design.md
    ├── resolved_tickets.json
    ├── resolved_board.html
    ├── audit_trail.json
    └── github_url.txt
```

Update the root `README.md` with setup and run instructions. Explain how to copy the original database to the working copy for a clean run, start the MCP server, start the FastAPI backend, start the React dashboard, and reset the database before running all three tickets.

Before pushing, check that the required files are present and no secrets are staged. Push the project to a public repository, put its URL in `output/github_url.txt`, and give me the URL so I can submit it on Canvas.
