"""Content Agent -- writes a blog post draft grounded in approved graph
knowledge only, via the content-agent MCP server (main-only, no EmailThread
access).

    python content_agent.py "demand forecasting for mid-market retail"
"""

import sys

from mcp_agent_runner import run

SYSTEM_PROMPT = """You are GroundTruth's Content Agent. You write blog post drafts about \
GroundTruth's own products (Stockly, Inspectly) using ONLY facts retrieved through your tools -- \
never general knowledge, never the public web, never anything you weren't given by a tool call. \
Ground every claim in a specific tool result. Include at least 3 specific facts or metrics \
returned by your tools, and cite each one's proof-point slug in parentheses right after the claim \
so a reader can trace it back to the graph, e.g. "(pp--product--stockly--stockouts-drop-by-34-)". \
You have no tools that can see customer/email data and must never reference a specific customer \
or pilot company name, even if you happen to know of one -- you don't have the tools to look one \
up, so don't invent one. If your tools don't return enough to support a claim, say what's missing \
instead of guessing."""


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python content_agent.py '<topic>'")
        sys.exit(1)
    topic = " ".join(sys.argv[1:])
    user_prompt = (
        f"Write a ~350 word blog post about: {topic}. Use your tools to find the relevant "
        f"product, its features, and its proof points before writing. Cite proof point slugs "
        f"inline."
    )
    result = run("content-agent", SYSTEM_PROMPT, user_prompt)
    print("\n----- BLOG POST DRAFT -----\n")
    print(result)


if __name__ == "__main__":
    main()
