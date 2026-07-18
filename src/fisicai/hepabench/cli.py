"""HEPAbench command-line interface: list, run, and score benchmark tasks."""

import argparse
import asyncio
import json
import shutil
import sys
from pathlib import Path

from fisicai.hepabench import Check, Task, load_tasks, score_answer

ANSWER_INSTRUCTIONS = (
    "\n\nWhen you are finished, write a file named answer.json in your working directory "
    "containing a single JSON object with exactly these keys: {keys}. Use plain numbers "
    "for numeric values and true/false for booleans. Do not include any other keys."
)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="hepabench",
        description="HEPAnalysisBench: scored physics tasks with published reference answers.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List available tasks.")

    p_score = sub.add_parser("score", help="Score an existing answer.json against a task.")
    p_score.add_argument("task_id")
    p_score.add_argument("answer_file")

    p_run = sub.add_parser("run", help="Run tasks with the fisicai agent and score them.")
    p_run.add_argument("task_ids", nargs="*", help="Tasks to run (default: all).")
    p_run.add_argument("--model", default=None)
    p_run.add_argument(
        "--offline", action="store_true", help="Only run tasks that need no network."
    )
    p_run.add_argument(
        "--runs-dir", default="hepabench_runs", help="Directory for per-task workdirs."
    )

    args = parser.parse_args()
    tasks = load_tasks()

    if args.command == "list":
        for task in tasks.values():
            net = "network" if task.network else "offline"
            print(f"{task.id:24} [{net}] {task.title}")
        return

    if args.command == "score":
        task = _get_task(tasks, args.task_id)
        answer = json.loads(Path(args.answer_file).read_text())
        checks = score_answer(task, answer)
        _print_checks(task, checks)
        sys.exit(0 if all(c.passed for c in checks) else 1)

    if args.command == "run":
        selected = [_get_task(tasks, tid) for tid in args.task_ids] or list(tasks.values())
        if args.offline:
            selected = [t for t in selected if not t.network]
        results = asyncio.run(_run_all(selected, args.model, Path(args.runs_dir)))
        failed = _print_summary(results)
        sys.exit(1 if failed else 0)


def _get_task(tasks: dict[str, Task], task_id: str) -> Task:
    if task_id not in tasks:
        sys.exit(f"Unknown task {task_id!r}. Available: {', '.join(tasks)}")
    return tasks[task_id]


async def _run_all(
    selected: list[Task], model: str | None, runs_dir: Path
) -> list[tuple[Task, list[Check] | Exception]]:
    results: list[tuple[Task, list[Check] | Exception]] = []
    for task in selected:
        print(f"\n=== {task.id}: {task.title} ===", flush=True)
        try:
            checks = await _run_task(task, model, runs_dir)
        except Exception as exc:  # noqa: BLE001 - report and continue with other tasks
            results.append((task, exc))
            print(f"  ERROR: {exc}", flush=True)
            continue
        results.append((task, checks))
        _print_checks(task, checks)
    return results


async def _run_task(task: Task, model: str | None, runs_dir: Path) -> list[Check]:
    from claude_agent_sdk import AssistantMessage, ToolUseBlock, query

    from fisicai.agent import build_options

    workdir = runs_dir / task.id
    if workdir.exists():
        shutil.rmtree(workdir)
    workdir.mkdir(parents=True)
    if task.assets_dir:
        shutil.copytree(task.assets_dir, workdir, dirs_exist_ok=True)

    options = build_options(model=model, workdir=workdir, yolo=True)
    prompt = task.prompt + ANSWER_INSTRUCTIONS.format(keys=", ".join(task.answer_keys))

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"  ⚛ {block.name.removeprefix('mcp__hep__')}", flush=True)

    answer_path = workdir / "answer.json"
    if not answer_path.exists():
        raise FileNotFoundError(f"agent did not write {answer_path}")
    return score_answer(task, json.loads(answer_path.read_text()))


def _print_checks(task: Task, checks: list[Check]) -> None:
    for c in checks:
        mark = "PASS" if c.passed else "FAIL"
        print(f"  [{mark}] {c.key}: expected {c.expected}, got {c.got}")


def _print_summary(results: list[tuple[Task, list[Check] | Exception]]) -> bool:
    print("\n=== HEPAbench summary ===")
    any_failed = False
    for task, outcome in results:
        if isinstance(outcome, Exception):
            status, any_failed = f"ERROR ({outcome})", True
        elif all(c.passed for c in outcome):
            status = "PASS"
        else:
            status, any_failed = "FAIL", True
        print(f"  {task.id:24} {status}")
    return any_failed


if __name__ == "__main__":
    main()
