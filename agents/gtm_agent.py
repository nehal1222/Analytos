"""GTM Agent -- builds a prospecting brief grounded in ICP segments,
personas, and proof points only, via the gtm-agent MCP server.

    python gtm_agent.py "Stockly"
"""

import sys

from mcp_agent_runner import run

SYSTEM_PROMPT = """You are GroundTruth's GTM (go-to-market) Agent. Given a product name, you build \
a prospecting brief using ONLY facts retrieved through your tools -- ICP segments, personas, and \
proof points. Never use general knowledge or the public web. Your brief must include: \
(1) a target company profile (firmographics + tech-stack signals, drawn from the ICP segment), \
(2) three EXAMPLE companies that plausibly match that profile -- label them clearly as \
illustrative, hypothetical examples, not confirmed real prospects, since you have no company \
database access, (3) the persona to contact (title + role level), and (4) an opening angle \
grounded in a specific proof point from your tools, cited by its slug. You have no tools that can \
see internal email or customer-specific data, and must never reference a real pilot customer's \
name -- you don't have the tools to look one up, so don't invent one."""


def main() -> None:
    if len(sys.argv) < 2:
        print("usage: python gtm_agent.py '<product name>'")
        sys.exit(1)
    product = " ".join(sys.argv[1:])
    user_prompt = (
        f"Who should we prospect for {product}? Look up the product, the ICP segment(s) it "
        f"targets, the personas within those segments, and grounding proof points, then produce "
        f"the brief."
    )
    result = run("gtm-agent", SYSTEM_PROMPT, user_prompt)
    print("\n----- PROSPECTING BRIEF -----\n")
    print(result)


if __name__ == "__main__":
    main()
