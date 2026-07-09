"""Drive an LLM tool-use loop against one of this POC's role-scoped MCP
servers (mcp-server/mcp_server.py --role content-agent|gtm-agent).

Each agent script (content_agent.py, gtm_agent.py) spawns its own MCP
server subprocess over stdio, hands the LLM the tool catalog *that server
exposes* (which is already curated per role -- see mcp-server/policy.yaml),
and loops tool-call turns until the model produces a final answer. Because
the tool catalog itself never includes an EmailThread-touching query for
content-agent, there's no path for the model to request internal email
data even if a prompt tried to induce it -- the enforcement is structural,
not prompt-based.

Two providers, picked automatically (or via AGENT_LLM_PROVIDER=claude|gemini):
- Claude (Anthropic Messages API + tool_use), needs ANTHROPIC_API_KEY.
- Gemini (google-genai + function calling), needs GEMINI_API_KEY.
Both drive the identical MCP session/tool-catalog -- only the model-facing
tool-call wire format differs.
"""

from __future__ import annotations

import asyncio
import os
import sys
from contextlib import AsyncExitStack

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

DEFAULT_CLAUDE_MODEL = os.environ.get("ANTHROPIC_AGENT_MODEL", "claude-sonnet-5")
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_AGENT_MODEL", "gemini-2.5-flash")
MAX_TOOL_TURNS = 10  # hard cap so a runaway tool loop can't spin forever

_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "mcp-server", "mcp_server.py")


def _server_params(role: str) -> StdioServerParameters:
    # sys.executable, not the bare string "python" -- the latter resolves
    # via PATH independent of which interpreter (venv or system) is
    # actually running this process, and can launch the MCP server under a
    # Python that doesn't have its dependencies (mcp, pyyaml, ...) installed.
    return StdioServerParameters(command=sys.executable, args=[_SERVER_SCRIPT, "--role", role])


def _provider() -> str:
    explicit = os.environ.get("AGENT_LLM_PROVIDER", "").lower()
    if explicit in ("claude", "gemini"):
        return explicit
    # Gemini takes priority over Claude when both keys happen to be set in
    # the environment (e.g. left over from an earlier session) -- if you
    # bothered to set GEMINI_API_KEY, you meant to use it. Set
    # AGENT_LLM_PROVIDER=claude explicitly if you want the opposite.
    if os.environ.get("GEMINI_API_KEY"):
        return "gemini"
    return "claude"


# ---------------------------------------------------------------- Claude --

def _mcp_tool_to_anthropic(tool) -> dict:
    return {
        "name": tool.name,
        "description": tool.description or "",
        "input_schema": tool.inputSchema,
    }


async def _run_claude_agent(role: str, system_prompt: str, user_prompt: str, model: str) -> str:
    from anthropic import Anthropic

    anthropic = Anthropic()

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(_server_params(role)))
        session: ClientSession = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        tool_list = (await session.list_tools()).tools
        anthropic_tools = [_mcp_tool_to_anthropic(t) for t in tool_list]
        print(f"[{role}] MCP tools available: {', '.join(t.name for t in tool_list)}")

        messages = [{"role": "user", "content": user_prompt}]

        for _ in range(MAX_TOOL_TURNS):
            response = anthropic.messages.create(
                model=model,
                max_tokens=2000,
                system=system_prompt,
                messages=messages,
                tools=anthropic_tools,
            )
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason != "tool_use":
                return "".join(b.text for b in response.content if b.type == "text")

            tool_results = []
            for block in response.content:
                if block.type != "tool_use":
                    continue
                print(f"[{role}] calling tool {block.name}({block.input})")
                result = await session.call_tool(block.name, block.input)
                text = "".join(c.text for c in result.content if c.type == "text")
                tool_results.append(
                    {"type": "tool_result", "tool_use_id": block.id, "content": text}
                )
            messages.append({"role": "user", "content": tool_results})

        return "(stopped: exceeded max tool-use turns)"


# ---------------------------------------------------------------- Gemini --

async def _run_gemini_agent(role: str, system_prompt: str, user_prompt: str, model: str) -> str:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    async with AsyncExitStack() as stack:
        read, write = await stack.enter_async_context(stdio_client(_server_params(role)))
        session: ClientSession = await stack.enter_async_context(ClientSession(read, write))
        await session.initialize()

        tool_list = (await session.list_tools()).tools
        print(f"[{role}] MCP tools available: {', '.join(t.name for t in tool_list)}")

        function_declarations = [
            types.FunctionDeclaration(
                name=t.name,
                description=t.description or "",
                # google-genai accepts a raw JSON Schema dict here directly --
                # the same inputSchema the MCP server already generated from
                # each tool's Python type hints, no reshaping needed.
                parametersJsonSchema=t.inputSchema,
            )
            for t in tool_list
        ]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(functionDeclarations=function_declarations)],
        )

        contents = [types.Content(role="user", parts=[types.Part(text=user_prompt)])]

        for _ in range(MAX_TOOL_TURNS):
            response = client.models.generate_content(model=model, contents=contents, config=config)
            candidate = response.candidates[0]
            contents.append(candidate.content)

            function_calls = [p.function_call for p in candidate.content.parts if p.function_call]
            if not function_calls:
                return "".join(p.text for p in candidate.content.parts if p.text)

            response_parts = []
            for fc in function_calls:
                print(f"[{role}] calling tool {fc.name}({dict(fc.args or {})})")
                result = await session.call_tool(fc.name, dict(fc.args or {}))
                text = "".join(c.text for c in result.content if c.type == "text")
                response_parts.append(types.Part.from_function_response(name=fc.name, response={"result": text}))
            contents.append(types.Content(role="user", parts=response_parts))

        return "(stopped: exceeded max tool-use turns)"


# ----------------------------------------------------------------- shared --

async def run_agent(role: str, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    provider = _provider()
    if provider == "gemini":
        return await _run_gemini_agent(role, system_prompt, user_prompt, model or DEFAULT_GEMINI_MODEL)
    return await _run_claude_agent(role, system_prompt, user_prompt, model or DEFAULT_CLAUDE_MODEL)


def run(role: str, system_prompt: str, user_prompt: str, model: str | None = None) -> str:
    return asyncio.run(run_agent(role, system_prompt, user_prompt, model))
