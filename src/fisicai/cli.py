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


def main() -> None:
    parser = argparse.ArgumentParser(prog="fisicai", description=BANNER)
    parser.add_argument(
        "task",
        nargs="*",
        help="Task for the agent, or 'chat' for an interactive session.",
    )
    parser.add_argument("--model", default=None, help=f"Model to use (default: {DEFAULT_MODEL})")
    parser.add_argument(
        "--workdir", default=None, help="Agent working directory (default: ./workspace)"
    )
    parser.add_argument(
        "--yolo",
        action="store_true",
        help="Skip permission prompts entirely (bypassPermissions).",
    )
    args = parser.parse_args()

    options = build_options(model=args.model, workdir=args.workdir, yolo=args.yolo)

    if not args.task or args.task == ["chat"]:
        asyncio.run(chat(options))
    else:
        asyncio.run(run_task(" ".join(args.task), options))


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
