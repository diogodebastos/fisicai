"""HEPAnalysisBench (HEPAbench): scored physics tasks with published reference answers.

Each task is a YAML file defining a prompt, the keys the agent must write to
``answer.json``, and reference values with tolerances. The scorer is harness-agnostic:
any agent that produces an ``answer.json`` can be benchmarked.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

TASKS_DIR = Path(__file__).parent / "tasks"
DATA_DIR = Path(__file__).parent / "data"


@dataclass
class Check:
    """One scored comparison between an answer value and its reference."""

    key: str
    passed: bool
    expected: str
    got: str


@dataclass
class Task:
    id: str
    title: str
    prompt: str
    answer_keys: list[str]
    reference: dict[str, dict[str, Any]]
    network: bool = False
    assets: str | None = None
    tags: list[str] = field(default_factory=list)

    @property
    def assets_dir(self) -> Path | None:
        return DATA_DIR / self.assets if self.assets else None


def load_tasks(tasks_dir: Path = TASKS_DIR) -> dict[str, Task]:
    tasks = {}
    for path in sorted(tasks_dir.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text())
        task = Task(**raw)
        tasks[task.id] = task
    return tasks


def score_answer(task: Task, answer: dict[str, Any]) -> list[Check]:
    """Score an answer.json dict against the task's reference values."""
    checks = []
    for key, ref in task.reference.items():
        if key not in answer:
            checks.append(Check(key, False, _describe(ref), "(missing)"))
            continue
        got = answer[key]
        if "value" in ref:
            passed = _numeric_match(got, ref["value"], ref.get("abs_tol", 0.0))
        else:
            passed = _normalize(got) == _normalize(ref["equals"])
        checks.append(Check(key, passed, _describe(ref), repr(got)))
    return checks


def _numeric_match(got: Any, expected: float, abs_tol: float) -> bool:
    try:
        return abs(float(got) - float(expected)) <= abs_tol
    except (TypeError, ValueError):
        return False


def _normalize(value: Any) -> str:
    text = str(value).strip().lower()
    return text.removeprefix("arxiv:").strip()


def _describe(ref: dict[str, Any]) -> str:
    if "value" in ref:
        return f"{ref['value']} ± {ref.get('abs_tol', 0.0)}"
    return repr(ref["equals"])
