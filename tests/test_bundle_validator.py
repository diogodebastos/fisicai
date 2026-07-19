import json
import shutil
import textwrap

import pytest

from fisicai.hepabench.bundle import validate_bundle
from fisicai.writeup import results_to_tex

RESULTS = {"m_peak": 91.002, "n_events": 8589}

ANALYSIS_PY = textwrap.dedent(
    """
    import json, pathlib
    out = pathlib.Path(__file__).parent / "results"
    out.mkdir(exist_ok=True)
    results = {"m_peak": 91.002, "n_events": 8589}
    (out / "results.json").write_text(json.dumps(results, indent=2))
    """
)

NOTE_TEX = textwrap.dedent(
    r"""
    \documentclass{article}
    \input{../results/results.tex}
    \begin{document}
    The peak is at \MPeak~GeV from \NEvents\ events~\cite{CMS:2008xjf}.
    \bibliographystyle{unsrt}
    \bibliography{references}
    \end{document}
    """
)

BIB = "@article{CMS:2008xjf,\n  title = {{The CMS experiment}},\n  year = {2008}\n}\n"


@pytest.fixture
def bundle(tmp_path):
    b = tmp_path / "mini_bundle"
    (b / "results").mkdir(parents=True)
    (b / "note").mkdir()
    (b / "figures").mkdir()
    (b / "analysis.py").write_text(ANALYSIS_PY)
    (b / "results/results.json").write_text(json.dumps(RESULTS, indent=2))
    (b / "results/results.tex").write_text(results_to_tex(RESULTS))
    (b / "note/note.tex").write_text(NOTE_TEX)
    (b / "note/references.bib").write_text(BIB)
    (b / "note/note.pdf").write_text("%PDF-fake")
    (b / "README.md").write_text("mini bundle for tests\n")
    return b


def _by_key(checks):
    return {c.key: c for c in checks}


def test_valid_bundle_passes(bundle):
    checks = _by_key(validate_bundle(bundle, compile_pdf=False))
    for key in ("files", "reproducible", "macros_in_sync", "no_raw_numbers", "citations"):
        assert checks[key].passed, f"{key}: {checks[key].got}"


def test_missing_file_fails_fast(bundle):
    (bundle / "README.md").unlink()
    checks = validate_bundle(bundle, compile_pdf=False)
    assert len(checks) == 1 and not checks[0].passed
    assert "README.md" in checks[0].got


def test_tampered_results_fail_reproducibility(bundle):
    tampered = dict(RESULTS, m_peak=91.5)
    (bundle / "results/results.json").write_text(json.dumps(tampered, indent=2))
    (bundle / "results/results.tex").write_text(results_to_tex(tampered))
    checks = _by_key(validate_bundle(bundle, compile_pdf=False))
    assert not checks["reproducible"].passed
    assert "m_peak" in checks["reproducible"].got


def test_stale_macros_fail(bundle):
    (bundle / "results/results.tex").write_text("\\newcommand{\\MPeak}{90.0}\n")
    checks = _by_key(validate_bundle(bundle, run=False, compile_pdf=False))
    assert not checks["macros_in_sync"].passed


def test_hand_typed_number_fails(bundle):
    note = (bundle / "note/note.tex").read_text().replace("\\MPeak~GeV", "91.002 GeV")
    (bundle / "note/note.tex").write_text(note)
    checks = _by_key(validate_bundle(bundle, run=False, compile_pdf=False))
    assert not checks["no_raw_numbers"].passed
    assert "m_peak" in checks["no_raw_numbers"].got


def test_uncited_reference_fails(bundle):
    (bundle / "note/references.bib").write_text(BIB + "\n@article{Unused:2020abc,\n}\n")
    checks = _by_key(validate_bundle(bundle, run=False, compile_pdf=False))
    assert not checks["citations"].passed
    assert "Unused:2020abc" in checks["citations"].got


@pytest.mark.skipif(shutil.which("tectonic") is None, reason="tectonic not installed")
def test_compile_check_runs(bundle):
    checks = _by_key(validate_bundle(bundle, run=False, compile_pdf=True))
    assert checks["compiles"].passed, checks["compiles"].got
