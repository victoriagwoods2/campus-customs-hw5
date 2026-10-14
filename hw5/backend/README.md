# Campus Customs Agent Backend

FastAPI exposes the five PydanticAI agents. Boss starts ticket work; each agent can delegate to any of the other four. The agents use the MCP server configured in the project-root `.mcp.json` for shop facts and operations; there is no separate shop-tools layer.

All model requests use `gpt-6-luna` through `https://api.portkey.ai/v1` and read `PORTKEY_API_KEY` from a `.env` in the project root (copy `.env.example`) or a parent folder. Human approval MCP tools are filtered out of every PydanticAI agent toolset.

## Run locally

From the project root, create `.venv` and run `pip install -r requirements.txt` (see the root `README.md`). Then, from `backend/` with the venv active:

```bash
uvicorn main:app --reload --port 8000
```

The full route list is in `output/harness.md`. `POST /api/tickets/{ticket_id}/run` starts a bounded Boss-led run, and only `POST /api/approvals/{request_id}/approve` carries out a payment or purchase order. Each visible PydanticAI loop step is appended to `output/audit_trail.json`; earlier records are preserved.

The agent prompts in `backend/prompts/` follow the role instructions in `AI_prompts.md` (Problem 5) and include the shop safety rules for each role.
