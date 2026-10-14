# Campus Customs Operations Desk: Dashboard Design

The dashboard in `frontend/` (React + Vite + TypeScript) is where a person picks a desk ticket, watches the agent team work on it, and signs off on any money the agents propose to spend. It is styled like the counter of a campus print shop: warm paper, Yale blue, brass trim, and tickets that look like torn receipt stubs.

## Layout

The page has a masthead and three columns, ordered by how a person uses the desk:

1. **Masthead (always visible).** The Campus Customs brand, the shop date from `desk.date_today`, a backend connection light, the **checking balance**, and a **Reset desk** button. Cash sits at the top because it limits every decision on the desk.
2. **Left: Desk tickets.** Tickets 101, 102, and 103 as receipt stubs, each showing its number, type, subject, requester, and status. The rail stays in place while you scroll, so you can always switch tickets.
3. **Centre: the selected ticket (the main area).** From top to bottom:
   - **Ticket card:** the subject in a large serif, the customer's words as a quote, fact chips (SKU, size, quantity, status), and one main action, **Start agent team**.
   - **What each agent did:** after a run, one summary card per agent that took part. The Boss's summary spans the full width.
   - **Agent activity:** the live feed of agent steps.
4. **Right: Needs your sign-off.** Pending payment and purchase-order requests, with a red count badge. A brass top border sets it apart, because this is the one place a person is expected to act.

Below 1180px wide, the approvals panel moves under the main area. On narrow screens, all columns stack.

## Visual style

- **Palette:** warm paper (`#f5f1e8`) with a faint dot grid, near-black ink, Yale blue (`#00356b`) for structure and the main buttons, and brass (`#b8862b`) as the trim colour. Green means money approved or work finished. Red is used only for errors, refusals, and the RESOLVED stamp.
- **Type:** a serif (Iowan Old Style / Palatino) for ticket subjects and the brand, so it reads like a shop sign or a printed receipt. A system sans-serif for interface text. Monospace with tabular numbers for ticket numbers, money, tool names, and timings.
- **Shapes:** ticket stubs have a dashed perforation down the left edge. The balance sits in a dark display with green digits, like a cash register. Panels are cream cards with soft shadows and a coloured top border for their role: blue for the ticket, brass for approvals, green for the run report.
- **Motion:** small and purposeful. New feed lines rise into place, the running ticket gets a moving brass stripe, and the active agent's chip pulses. All of it turns off under `prefers-reduced-motion`.

## How agent activity is distinguished

Each agent has a fixed colour and icon used everywhere it appears: the crew chips, feed avatars, hand-off badges, and report cards.

| Agent | Icon | Colour |
|---|---|---|
| Boss | 🧭 | Yale navy `#00356b` |
| Inventory | 📦 | Green `#2c6e49` |
| Accounting | 🧾 | Amber `#8a5a0b` |
| Facilities | 🏬 | Terracotta `#a1412b` |
| Customer Service | 💬 | Violet `#5f4597` |

All five colours meet text contrast against their pale tints, so names and badges stay readable.

- **Crew strip:** the five agents appear as chips at the top of the feed. Chips start out dashed and grey, and fill with the agent's colour once that agent joins the run. The agent working right now gets a pulsing ring. This shows at a glance that the Boss did **not** send every ticket to every agent.
- **Feed lines** pair an avatar with the agent's name in its colour, a plain-language verb ("checked the shop records", "handed off to Facilities", "filed a request for human approval", "reported back"), and the time since the run started.
- **Tool use:** every MCP tool an agent called shows as a monospace chip with a gear in the agent's colour (`get_cash_status`, `request_payment_approval`, …).
- **Hand-offs:** a delegation shows the target agent as a coloured badge. The target's own steps are indented under it, with a thin rail in the target's colour, so you can follow chains like Boss → Facilities → Accounting.
- **Reports:** when an agent reports back, its summary sits in a block tinted with its colour, so conclusions stand out from routine steps.
- **Filtering:** low-level bookkeeping steps (raw prompts, tool-return rows) are hidden, so the feed reads like a story.

While a run is going, the feed reloads from `GET /api/events` every 1.5 seconds. It shows typing dots and "Boss is reading the ticket…" before the first step arrives, and scrolls to keep up.

## How resolved tickets and cash are shown

- **Resolved tickets:** when the run route reports `ticket_status: "resolved"`, or an approved rent payment resolves a ticket, the stub gets a tilted red **RESOLVED** rubber stamp. The stamp animates down onto the stub the moment it happens. The stub's text fades, the open count in the rail header drops, and the ticket card's top border turns green. The Start button is replaced by a green check and "Resolved: reset the desk to run it again". A toast confirms the change.
- **Cash:** the balance is the brightest number on the screen. After an approved payment, the dashboard reloads `GET /api/cash`. The digits flash red-to-green, and a "−$2,400.00" badge appears next to them and fades over six seconds. While requests are pending, a line under the balance shows how much is awaiting sign-off and how much is free.
- **Approvals:** each payment card shows the amount large and in monospace, what it pays for and when it is due, and **checking after payment**. If a payment would overdraw the account, that line turns red and says the backend will refuse it. Approving needs a "Signing as" name, which is saved in the browser and sent as `approved_by`. Every button shows its state ("Approving…", "Declining…"). Refusals from the backend, such as insufficient cash, appear on the card and as a toast. Declining asks for a short reason.

## Loading, error, and empty states

- Shimmering placeholder stubs and cards appear while data loads.
- If the backend is unreachable, a red banner names the URL and the exact start command. The connection light turns red, and the page reconnects on its own.
- Each panel reports its own errors and offers a retry where it makes sense.
- Only one run can go at a time, matching the backend's lock. Other tickets' buttons say "Another ticket is running" and Reset is disabled until the run ends.
- Empty states explain what will appear: "No run on this ticket yet…", "Nothing waiting. Agents will put payment and purchase-order requests here…".

## Why these choices make the desk useful and enjoyable

- **The hierarchy follows the job.** Pick a ticket (left), watch it get handled (centre), sign off on money (right), and keep an eye on cash (top). The two things a person must never miss, money leaving and tickets closing, get the boldest treatment: the till display and the rubber stamp.
- **Consistent agent identity makes a multi-agent run easy to follow.** Because the same colour and icon follow each agent through chips, feed, hand-offs, and reports, you can tell who did what without reading every line. The indented hand-offs show the delegation chain the Boss chose.
- **Human approval feels deliberate.** Money only moves through a signed approval card that shows the balance after payment first, matching the shop rule that every payment needs a person.
- **It's pleasant to come back to.** The print-shop paper, shop-sign serif, cash-register till, and the small payoff of the RESOLVED stamp make it feel like a place where work gets done, without getting in the way of the information.
