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
    """One scored comparison between an answer value and its reference.

    ``score`` is continuous in [0, 1] so the benchmark yields a number to maximize,
    not just a pass/fail bit. For numeric references it decays linearly with the
    distance from the reference value (1.0 exact, 0.5 at the tolerance edge, 0.0 at
    twice the tolerance); exact-match references score 1.0 or 0.0. When not set
    explicitly it defaults to 1.0/0.0 from ``passed``.
    """

    key: str
    passed: bool
    expected: str
    got: str
    score: float | None = None

    def __post_init__(self) -> None:
        if self.score is None:
            self.score = 1.0 if self.passed else 0.0


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
            checks.append(Check(key, False, _describe(ref), "(missing)", score=0.0))
            continue
        got = answer[key]
        if "value" in ref:
            passed, score = _numeric_score(got, ref["value"], ref.get("abs_tol", 0.0))
        else:
            passed = _normalize(got) == _normalize(ref["equals"])
            score = 1.0 if passed else 0.0
        checks.append(Check(key, passed, _describe(ref), repr(got), score=score))
    return checks


def task_score(checks: list[Check]) -> float:
    """Aggregate a task's checks into one number in [0, 1] (mean of check scores)."""
    if not checks:
        return 0.0
    return sum(c.score for c in checks) / len(checks)


def _numeric_score(got: Any, expected: float, abs_tol: float) -> tuple[bool, float]:
    try:
        delta = abs(float(got) - float(expected))
    except (TypeError, ValueError):
        return False, 0.0
    if abs_tol <= 0:
        return delta == 0, 1.0 if delta == 0 else 0.0
    passed = delta <= abs_tol * (1.0 + 1e-9)  # FP-robust at the tolerance edge
    return passed, max(0.0, 1.0 - delta / (2.0 * abs_tol))


def _normalize(value: Any) -> str:
    text = str(value).strip().lower()
    return text.removeprefix("arxiv:").strip()


def _describe(ref: dict[str, Any]) -> str:
    if "value" in ref:
        return f"{ref['value']} ± {ref.get('abs_tol', 0.0)}"
    return repr(ref["equals"])
