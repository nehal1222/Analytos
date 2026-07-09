"""MCP server exposing OmniGraph stored queries as tools, scoped per role.

Run one process per agent role (e.g. as two separate entries in a Claude
Desktop / Claude Code MCP config), with the query gateway (gateway.py)
already running:

    python gateway.py &
    python mcp_server.py --role content-agent
    python mcp_server.py --role gtm-agent

See policy.yaml and gateway.py for why role -> query scoping is enforced by
a real gateway service now, not just by which tools this process happens
to register: this process holds only a gateway API key (never a real
omnigraph-server bearer token), so even if that key leaked, the worst it
grants is exactly this role's allowed_queries list, against main, via named
queries only -- the same thing the tool catalog below already exposes.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml
from mcp.server.fastmcp import FastMCP

import tools  # noqa: E402

POLICY_PATH = Path(__file__).resolve().parent / "policy.yaml"


def load_policy() -> dict:
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))


def build_server(role: str) -> FastMCP:
    policy = load_policy()
    if role not in policy["roles"]:
        raise SystemExit(f"unknown role '{role}'; known roles: {sorted(policy['roles'])}")
    role_config = policy["roles"][role]

    tools.CLIENT = tools.GatewayClient(role_config["gateway_api_key"])

    mcp = FastMCP(f"analytos-context-{role}")
    for tool_name in role_config["allowed_queries"]:
        fn = tools.TOOL_REGISTRY[tool_name]
        mcp.add_tool(fn, name=tool_name, description=(fn.__doc__ or "").strip())
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=["content-agent", "gtm-agent"])
    args = parser.parse_args()

    mcp = build_server(args.role)
    mcp.run()


if __name__ == "__main__":
    main()
