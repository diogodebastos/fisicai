import json

import pytest

from fisicai.hepabench import load_tasks, score_answer, task_score
from fisicai.tools.pyhf_tools import compute_cls


def test_scores_are_continuous():
    task = load_tasks()["toy_cls"]  # reference 0.0525 +- 0.003
    exact = score_answer(task, {"cls_obs": 0.0525})[0]
    at_tol = score_answer(task, {"cls_obs": 0.0555})[0]
    beyond = score_answer(task, {"cls_obs": 0.0625})[0]
    missing = score_answer(task, {})[0]
    assert exact.score == pytest.approx(1.0)
    assert at_tol.passed and at_tol.score == pytest.approx(0.5)
    assert not beyond.passed and beyond.score == 0.0
    assert missing.score == 0.0
    # closer answers always score higher — the property that makes it maximizable
    closer = score_answer(task, {"cls_obs": 0.0530})[0]
    farther = score_answer(task, {"cls_obs": 0.0545})[0]
    assert closer.score > farther.score
    assert task_score([exact, at_tol]) == pytest.approx(0.75)


def test_tasks_load_and_are_well_formed():
    tasks = load_tasks()
    assert {"toy_cls", "literature_stop_4body", "atlas_multib_cls"} <= set(tasks)
    for task in tasks.values():
        assert task.prompt
        assert set(task.reference) == set(task.answer_keys)
        if task.assets:
            assert task.assets_dir.is_dir()


def test_score_numeric_within_tolerance():
    task = load_tasks()["toy_cls"]
    checks = score_answer(task, {"cls_obs": 0.0525})
    assert all(c.passed for c in checks)
    checks = score_answer(task, {"cls_obs": 0.10})
    assert not any(c.passed for c in checks)


def test_score_equals_normalizes():
    task = load_tasks()["literature_stop_4body"]
    assert score_answer(task, {"arxiv_id": "arXiv:2301.08096"})[0].passed
    assert score_answer(task, {"arxiv_id": "2301.08096"})[0].passed
    assert not score_answer(task, {"arxiv_id": "1805.05784"})[0].passed


def test_score_bool_and_missing_keys():
    task = load_tasks()["atlas_multib_cls"]
    checks = score_answer(task, {"cls_obs": 0.2444, "excluded": False})
    assert all(c.passed for c in checks)
    checks = score_answer(task, {"cls_obs": 0.2444})
    assert {c.key: c.passed for c in checks} == {"cls_obs": True, "excluded": False}


def test_toy_task_is_solvable_with_fisicai_tools(tmp_path):
    """The reference answer for toy_cls must be reproducible by the pyhf tool itself."""
    task = load_tasks()["toy_cls"]
    workdir = tmp_path / "toy"
    workdir.mkdir()
    (workdir / "BkgOnly.json").write_text(
        (task.assets_dir / "BkgOnly.json").read_text()
    )
    text = compute_cls(str(workdir), poi_value=1.0)
    cls_obs = float(text.split("CLs observed = ")[1].split()[0])
    checks = score_answer(task, {"cls_obs": cls_obs})
    assert all(c.passed for c in checks)


def test_answer_json_roundtrip(tmp_path):
    task = load_tasks()["toy_cls"]
    answer_file = tmp_path / "answer.json"
    answer_file.write_text(json.dumps({"cls_obs": 0.0524}))
    checks = score_answer(task, json.loads(answer_file.read_text()))
    assert all(c.passed for c in checks)
