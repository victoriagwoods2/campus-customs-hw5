"""Load the one permitted model through Portkey and construct MCP toolsets."""

from __future__ import annotations

import json
import os
import sys
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic_ai.mcp import MCPToolset, StdioTransport
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.models.openai import OpenAIResponsesModel


PROJECT_ROOT = Path(__file__).resolve().parents[2]
MCP_CONFIG_PATH = PROJECT_ROOT / ".mcp.json"
MCP_SERVER_NAME = "campus-customs"
MODEL_NAME = "gpt-6-luna"
PORTKEY_BASE_URL = "https://api.portkey.ai/v1"
HUMAN_ONLY_TOOLS = {
    "approve_payment_request",
    "approve_purchase_order_request",
    "reject_approval_request",
    "mark_ticket_resolved",
}
# Proposal and draft tools belong to one role each; other agents delegate to that role.
ROLE_ONLY_TOOLS = {
    "request_payment_approval": "Accounting",
    "request_purchase_order_approval": "Accounting",
    "save_customer_message_draft": "Customer Service",
}

for folder in (PROJECT_ROOT, *PROJECT_ROOT.parents):
    env_file = folder / ".env"
    if env_file.is_file():
        load_dotenv(env_file, override=False)


def require_portkey_key() -> str:
    key = os.environ.get("PORTKEY_API_KEY", "").strip()
    if not key:
        raise RuntimeError("PORTKEY_API_KEY is missing from the project or a parent .env file.")
    return key


@lru_cache(maxsize=1)
def build_model() -> OpenAIResponsesModel:
    """Use only gpt-6-luna, routed through the Portkey OpenAI-compatible endpoint."""
    client = AsyncOpenAI(
        api_key=require_portkey_key(),
        base_url=PORTKEY_BASE_URL,
        default_headers={"x-portkey-provider": "openai"},
    )
    provider = OpenAIProvider(openai_client=client)
    return OpenAIResponsesModel(MODEL_NAME, provider=provider)


def load_mcp_server() -> MCPToolset:
    """Build the stdio MCP server from .mcp.json, resolving paths against the project root.

    `.mcp.json` uses relative paths so it works on any machine and from Claude Code. A bare
    `python` command runs with this backend's interpreter, so the server shares its virtualenv.
    """
    if not MCP_CONFIG_PATH.is_file():
        raise RuntimeError(f"MCP configuration file is missing: {MCP_CONFIG_PATH}")
    servers = json.loads(MCP_CONFIG_PATH.read_text(encoding="utf-8")).get("mcpServers", {})
    server = servers.get(MCP_SERVER_NAME)
    if server is None or len(servers) != 1:
        raise RuntimeError(f"Expected exactly one MCP server named {MCP_SERVER_NAME!r} in .mcp.json.")
    command = server["command"]
    if command in {"python", "python3"}:
        command = sys.executable
    transport = StdioTransport(
        command=command,
        args=list(server.get("args") or []),
        env=server.get("env"),
        cwd=str(PROJECT_ROOT / server.get("cwd", ".")),
    )
    return MCPToolset(transport, id=MCP_SERVER_NAME)


def build_agent_toolset(role: str):
    """Load the configured MCP process, hide human decision tools, and keep role-only tools with their role."""
    base_toolset = load_mcp_server().prefixed(MCP_SERVER_NAME)

    def is_agent_tool(_ctx, tool_def) -> bool:
        unprefixed_name = tool_def.name.removeprefix(f"{MCP_SERVER_NAME}_")
        if unprefixed_name in HUMAN_ONLY_TOOLS:
            return False
        owner = ROLE_ONLY_TOOLS.get(unprefixed_name)
        return owner is None or owner == role

    return base_toolset.filtered(is_agent_tool)
