"""fisicai command-line interface."""

import argparse
import asyncio
import sys

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    query,
)

from fisicai.agent import DEFAULT_MODEL, build_options

BANNER = "fisicai — agentic harness for high-energy physics"

COMMANDS = ("run", "chat", "analyze")

ANALYZE_PROMPT = (
    "Produce a complete, reproducible analysis bundle in your current working directory, "
    "following the analysis-writeup skill exactly: analysis.py, results/results.json, "
    "results/results.tex generated with `python -m fisicai.writeup`, figures/, and "
    "note/note.tex compiled to note.pdf with tectonic, with references.bib entries "
    "fetched via inspire_bibtex, plus a README.md with regeneration instructions. "
    "Verify the bundle end-to-end before finishing.\n\nAnalysis task: {task}"
)


def build_parser() -> argparse.ArgumentParser:
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "--model", default=None, help=f"Model to use (default: {DEFAULT_MODEL})"
    )
    shared.add_argument(
        "--workdir", default=None, help="Agent working directory (default: ./workspace)"
    )
    shared.add_argument(
        "--yolo",
        action="store_true",
        help="Skip permission prompts entirely (bypassPermissions).",
    )

    parser = argparse.ArgumentParser(prog="fisicai", description=BANNER)
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", parents=[shared], help="Run a one-shot task (the default).")
    p_run.add_argument("task", nargs="+", help="Task for the agent.")

    sub.add_parser("chat", parents=[shared], help="Interactive session.")

    p_analyze = sub.add_parser(
        "analyze",
        parents=[shared],
        help="Produce a full analysis bundle (code + LaTeX note).",
    )
    p_analyze.add_argument("task", nargs="+", help="Analysis task for the bundle.")
    p_analyze.add_argument(
        "--name",
        default=None,
        help="Bundle name (directory under ./analyses/; default: derived from the task).",
    )
    return parser


def normalize_argv(argv: list[str]) -> list[str]:
    """Allow `fisicai "some task"` and bare `fisicai` without an explicit subcommand.

    The first argument decides: a known subcommand dispatches to it; no arguments
    means `chat`; anything else (including flags) becomes a `run` task invocation.
    """
    if not argv:
        return ["chat"]
    if argv[0] in COMMANDS or argv[0] in ("-h", "--help"):
        return argv
    return ["run", *argv]


def main() -> None:
    parser = build_parser()
    args = parser.parse_args(normalize_argv(sys.argv[1:]))

    if args.command == "analyze":
        task = " ".join(args.task)
        name = args.name or _slugify(task)
        workdir = args.workdir or f"analyses/{name}"
        options = build_options(model=args.model, workdir=workdir, yolo=args.yolo)
        print(f"[analysis bundle -> {workdir}]", file=sys.stderr)
        asyncio.run(run_task(ANALYZE_PROMPT.format(task=task), options))
        return

    options = build_options(model=args.model, workdir=args.workdir, yolo=args.yolo)

    if args.command == "chat":
        asyncio.run(chat(options))
    else:
        asyncio.run(run_task(" ".join(args.task), options))


def _slugify(text: str, max_words: int = 4) -> str:
    import re

    words = re.findall(r"[a-z0-9]+", text.lower())
    return "_".join(words[:max_words]) or "analysis"


def _print_message(message: object) -> None:
    if isinstance(message, AssistantMessage):
        for block in message.content:
            if isinstance(block, TextBlock):
                print(block.text, flush=True)
            elif isinstance(block, ToolUseBlock):
                name = block.name.removeprefix("mcp__hep__")
                print(f"  ⚛ {name}", file=sys.stderr, flush=True)
    elif isinstance(message, ResultMessage):
        cost = message.total_cost_usd
        if cost is not None:
            print(f"\n[done — ${cost:.4f}]", file=sys.stderr, flush=True)


async def run_task(task: str, options) -> None:
    async for message in query(prompt=task, options=options):
        _print_message(message)


async def chat(options) -> None:
    print(BANNER)
    print("Type a task, or 'exit' to quit.\n")
    async with ClaudeSDKClient(options=options) as client:
        while True:
            try:
                user_input = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                break
            await client.query(user_input)
            async for message in client.receive_response():
                _print_message(message)


if __name__ == "__main__":
    main()
