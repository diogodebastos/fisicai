"""Bundle validator: prove an analysis bundle is reproducible, not just plausible.

Checks (each reported as a :class:`~fisicai.hepabench.Check`):

- ``files``          — the bundle has the required layout
- ``reproducible``   — rerunning ``analysis.py`` in a clean temp copy regenerates an
                       identical ``results.json``
- ``macros_in_sync`` — ``results.tex`` matches what ``fisicai.writeup`` generates from
                       ``results.json``
- ``no_raw_numbers`` — no result value is hand-typed in ``note.tex`` (numbers must flow
                       through the generated macros)
- ``citations``      — every bibliography entry is cited and every ``\\cite`` resolves
- ``compiles``       — ``note.tex`` compiles with tectonic in a clean temp copy
"""

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from fisicai.hepabench import Check
from fisicai.writeup import _flatten, format_value, results_to_tex

REQUIRED_FILES = [
    "analysis.py",
    "results/results.json",
    "results/results.tex",
    "note/note.tex",
    "note/references.bib",
    "note/note.pdf",
    "README.md",
]

RERUN_TIMEOUT = 600
COMPILE_TIMEOUT = 300


def validate_bundle(
    bundle_dir: str | Path, run: bool = True, compile_pdf: bool = True
) -> list[Check]:
    bundle = Path(bundle_dir)
    checks = [_check_files(bundle)]
    if not checks[0].passed:
        return checks

    if run:
        checks.append(_check_reproducible(bundle))
    checks.append(_check_macros_in_sync(bundle))
    checks.append(_check_no_raw_numbers(bundle))
    checks.append(_check_citations(bundle))
    if compile_pdf:
        checks.append(_check_compiles(bundle))
    return checks


def _check_files(bundle: Path) -> Check:
    missing = [f for f in REQUIRED_FILES if not (bundle / f).is_file()]
    return Check(
        "files",
        not missing,
        "all required bundle files present",
        "ok" if not missing else f"missing: {', '.join(missing)}",
    )


def _check_reproducible(bundle: Path) -> Check:
    committed = json.loads((bundle / "results/results.json").read_text())
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / bundle.name
        shutil.copytree(bundle, copy, ignore=shutil.ignore_patterns("__pycache__"))
        try:
            proc = subprocess.run(
                [sys.executable, "analysis.py"],
                cwd=copy,
                capture_output=True,
                text=True,
                timeout=RERUN_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return Check("reproducible", False, "rerun completes", "timed out")
        if proc.returncode != 0:
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "?"
            return Check("reproducible", False, "rerun exits 0", f"exit {proc.returncode}: {tail}")
        rerun = json.loads((copy / "results/results.json").read_text())

    if rerun == committed:
        return Check("reproducible", True, "rerun reproduces results.json", "identical")
    changed = sorted(
        k for k in set(_flatten(committed)) | set(_flatten(rerun))
        if _flatten(committed).get(k) != _flatten(rerun).get(k)
    )
    return Check("reproducible", False, "rerun reproduces results.json", f"differs: {changed}")


def _check_macros_in_sync(bundle: Path) -> Check:
    expected = results_to_tex(json.loads((bundle / "results/results.json").read_text()))
    actual = (bundle / "results/results.tex").read_text()
    return Check(
        "macros_in_sync",
        expected == actual,
        "results.tex regenerates from results.json",
        "in sync" if expected == actual else "stale — regenerate with python -m fisicai.writeup",
    )


def _check_no_raw_numbers(bundle: Path) -> Check:
    """Result values must not appear as literals in the note (macros only).

    Only values whose formatted form is >= 4 characters are checked, to avoid false
    positives from years, section numbers, and short round numbers.
    """
    note = "\n".join(
        line for line in (bundle / "note/note.tex").read_text().splitlines()
        if not line.lstrip().startswith("%")
    )
    values = _flatten(json.loads((bundle / "results/results.json").read_text()))
    offenders = []
    for key, value in values.items():
        text = format_value(value)
        if len(text) < 4 or not re.search(r"\d", text):
            continue
        if re.search(rf"(?<![\d.]){re.escape(text)}(?![\d.])", note):
            offenders.append(f"{key}={text}")
    return Check(
        "no_raw_numbers",
        not offenders,
        "no result values hand-typed in note.tex",
        "clean" if not offenders else f"hand-typed: {', '.join(offenders)}",
    )


def _check_citations(bundle: Path) -> Check:
    bib = (bundle / "note/references.bib").read_text()
    note = (bundle / "note/note.tex").read_text()
    bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    cited = {
        key.strip()
        for cite in re.findall(r"\\cite\{([^}]+)\}", note)
        for key in cite.split(",")
    }
    uncited = sorted(bib_keys - cited)
    unresolved = sorted(cited - bib_keys)
    problems = []
    if not bib_keys:
        problems.append("references.bib has no entries")
    if uncited:
        problems.append(f"uncited: {uncited}")
    if unresolved:
        problems.append(f"unresolved \\cite: {unresolved}")
    return Check(
        "citations",
        not problems,
        "every bib entry cited, every cite resolves",
        "ok" if not problems else "; ".join(problems),
    )


def _check_compiles(bundle: Path) -> Check:
    tectonic = shutil.which("tectonic")
    if tectonic is None:
        return Check("compiles", False, "note.tex compiles with tectonic", "tectonic not installed")
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / bundle.name
        shutil.copytree(bundle, copy, ignore=shutil.ignore_patterns("__pycache__"))
        (copy / "note/note.pdf").unlink()
        try:
            proc = subprocess.run(
                [tectonic, "note.tex"],
                cwd=copy / "note",
                capture_output=True,
                text=True,
                timeout=COMPILE_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return Check("compiles", False, "note.tex compiles with tectonic", "timed out")
        if proc.returncode != 0 or not (copy / "note/note.pdf").exists():
            tail = proc.stderr.strip().splitlines()[-1] if proc.stderr.strip() else "?"
            return Check("compiles", False, "note.tex compiles with tectonic", tail)
    return Check("compiles", True, "note.tex compiles with tectonic", "ok")
