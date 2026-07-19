import pytest

from fisicai.writeup import format_value, macro_name, results_to_tex


def test_macro_names():
    assert macro_name("m_z_peak") == "MZPeak"
    assert macro_name("cls_obs") == "ClsObs"
    assert macro_name("nEvents") == "NEvents"
    assert macro_name("mass_60_120") == "MassSixZeroOneTwoZero"


def test_macro_name_rejects_unusable_keys():
    with pytest.raises(ValueError):
        macro_name("123")


def test_format_values():
    assert format_value(91.18762) == "91.19"
    assert format_value(0.0525149) == "0.05251"
    assert format_value(8589) == "8589"
    assert format_value(True) == "true"
    assert format_value("91.2 \\pm 0.1") == "91.2 \\pm 0.1"


def test_results_to_tex_flattens_and_generates():
    tex = results_to_tex(
        {"m_z_peak": 90.948, "cls": {"observed": 0.24444}, "n_events": 8589}
    )
    assert "\\newcommand{\\MZPeak}{90.95}" in tex
    assert "\\newcommand{\\ClsObserved}{0.2444}" in tex
    assert "\\newcommand{\\NEvents}{8589}" in tex
    assert tex.startswith("%")
