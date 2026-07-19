"""CLI argument dispatch tests (no agent runs)."""

import pytest

from fisicai.cli import build_parser, normalize_argv


def parse(argv):
    return build_parser().parse_args(normalize_argv(argv))


def test_bare_invocation_is_chat():
    assert parse([]).command == "chat"


def test_quoted_task_is_run():
    args = parse(["find the latest CMS top squark search"])
    assert args.command == "run"
    assert args.task == ["find the latest CMS top squark search"]


def test_unquoted_task_is_run():
    args = parse(["summarize", "the", "sbottom", "search"])
    assert args.command == "run"
    assert " ".join(args.task) == "summarize the sbottom search"


def test_task_starting_with_analyze_word_quoted_is_run():
    # A quoted sentence is one argv token != "analyze", so it must stay a run task.
    args = parse(["analyze the latest stop search and summarize it"])
    assert args.command == "run"


def test_explicit_analyze_subcommand():
    args = parse(["analyze", "measure the Z mass", "--name", "zmass"])
    assert args.command == "analyze"
    assert args.task == ["measure the Z mass"]
    assert args.name == "zmass"


def test_analyze_without_task_errors():
    with pytest.raises(SystemExit):
        parse(["analyze"])


def test_shared_flags_after_task():
    args = parse(["run", "some task", "--model", "claude-fable-5", "--yolo"])
    assert args.model == "claude-fable-5"
    assert args.yolo is True


def test_flags_on_bare_task_route_to_run():
    args = parse(["--yolo", "some task"])
    assert args.command == "run"
    assert args.yolo is True
    assert args.task == ["some task"]


def test_chat_takes_flags():
    args = parse(["chat", "--model", "claude-opus-4-8"])
    assert args.command == "chat"
    assert args.model == "claude-opus-4-8"
