"""MCP server exposing OmniGraph stored queries as tools, scoped per role.

Local use (Claude Desktop/Code spawns this as a subprocess over stdio), with
the query gateway (gateway.py) already running:

    python gateway.py &
    python mcp_server.py --role content-agent
    python mcp_server.py --role gtm-agent

Hosted use (a remote MCP client connects over HTTP -- e.g. deployed
alongside the query gateway so an evaluator's own Claude Desktop/Code can
point at a URL instead of spawning a local process):

    python mcp_server.py --role content-agent --transport streamable-http --host 0.0.0.0 --port 9001
    python mcp_server.py --role gtm-agent      --transport streamable-http --host 0.0.0.0 --port 9002

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


def build_server(role: str, host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    policy = load_policy()
    if role not in policy["roles"]:
        raise SystemExit(f"unknown role '{role}'; known roles: {sorted(policy['roles'])}")
    role_config = policy["roles"][role]

    tools.CLIENT = tools.GatewayClient(role_config["gateway_api_key"])

    mcp = FastMCP(f"analytos-context-{role}", host=host, port=port)
    for tool_name in role_config["allowed_queries"]:
        fn = tools.TOOL_REGISTRY[tool_name]
        mcp.add_tool(fn, name=tool_name, description=(fn.__doc__ or "").strip())
    return mcp


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", required=True, choices=["content-agent", "gtm-agent"])
    parser.add_argument(
        "--transport", default="stdio", choices=["stdio", "streamable-http"],
        help="stdio for a locally-spawned MCP client (Claude Desktop/Code); "
        "streamable-http to serve over the network for a remote client",
    )
    parser.add_argument("--host", default="127.0.0.1", help="only used with --transport streamable-http")
    parser.add_argument("--port", type=int, default=8000, help="only used with --transport streamable-http")
    args = parser.parse_args()

    mcp = build_server(args.role, host=args.host, port=args.port)
    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
