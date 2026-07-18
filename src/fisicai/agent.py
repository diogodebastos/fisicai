"""fisicai agent: system prompt, tool registration, options."""

import os
from pathlib import Path

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server

from fisicai.tools import ALL_TOOLS

DEFAULT_MODEL = os.environ.get("FISICAI_MODEL", "claude-fable-5")
SKILLS_DIR = Path(__file__).parent / "skills"

SYSTEM_PROMPT = """\
You are fisicai, an agentic research assistant for high-energy physics. You work like a
careful collaborator on an LHC analysis: precise about definitions, explicit about
assumptions, and honest about statistical and systematic caveats.

You have HEP-native tools (prefixed mcp__hep__): INSPIRE-HEP search, arXiv retrieval,
HEPData record lookup, published-likelihood download, and pyhf inference. You also have a
Python environment with the Scikit-HEP stack installed (uproot, awkward, hist, pyhf,
matplotlib) — write and run scripts in your working directory for anything beyond the
dedicated tools.

Ground rules:
- Never invent physics results. Quote numbers only from tool output, papers, or computations
  you actually ran, and cite the source (arXiv id / INSPIRE id / HEPData record).
- Distinguish observed from expected limits, and state the CL convention (CLs, 95% CL).
- When reinterpreting a search, say clearly which published likelihood and signal patch you
  used and what approximations that entails.
- Prefer published statistical models over digitized curves whenever they exist.
"""


def load_skills() -> str:
    """Concatenate the markdown skills into a system-prompt appendix."""
    sections = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        sections.append(f"## Skill: {path.stem}\n\n{path.read_text().strip()}")
    if not sections:
        return ""
    return "\n\n# fisicai skills\n\n" + "\n\n".join(sections)


def build_options(
    model: str | None = None,
    workdir: str | Path | None = None,
    yolo: bool = False,
) -> ClaudeAgentOptions:
    hep_server = create_sdk_mcp_server(name="hep", version="0.1.0", tools=ALL_TOOLS)
    workdir = Path(workdir or Path.cwd() / "workspace")
    workdir.mkdir(parents=True, exist_ok=True)

    mcp_tool_names = [f"mcp__hep__{t.name}" for t in ALL_TOOLS]
    return ClaudeAgentOptions(
        system_prompt={
            "type": "preset",
            "preset": "claude_code",
            "append": SYSTEM_PROMPT + load_skills(),
        },
        model=model or DEFAULT_MODEL,
        mcp_servers={"hep": hep_server},
        allowed_tools=[
            *mcp_tool_names,
            "Bash",
            "Read",
            "Write",
            "Edit",
            "Glob",
            "Grep",
            "WebFetch",
            "WebSearch",
        ],
        permission_mode="bypassPermissions" if yolo else "acceptEdits",
        cwd=workdir,
        setting_sources=[],
    )
