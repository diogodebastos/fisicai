import json

import pytest

from fisicai.tools.pyhf_tools import compute_cls, list_patches

# The two-bin uncorrelated-background example from the pyhf documentation.
WORKSPACE = {
    "channels": [
        {
            "name": "singlechannel",
            "samples": [
                {
                    "name": "signal",
                    "data": [12.0, 11.0],
                    "modifiers": [{"name": "mu", "type": "normfactor", "data": None}],
                },
                {
                    "name": "background",
                    "data": [50.0, 52.0],
                    "modifiers": [
                        {
                            "name": "uncorr_bkguncrt",
                            "type": "shapesys",
                            "data": [3.0, 7.0],
                        }
                    ],
                },
            ],
        }
    ],
    "observations": [{"name": "singlechannel", "data": [51.0, 48.0]}],
    "measurements": [{"name": "meas", "config": {"poi": "mu", "parameters": []}}],
    "version": "1.0.0",
}

PATCHSET = {
    "metadata": {
        "description": "signal patchset",
        "digests": {},  # filled in by the fixture with the real workspace digest
        "labels": ["mass"],
        "references": {"hepdata": "ins1234567"},
    },
    "version": "1.0.0",
    "patches": [
        {
            "metadata": {"name": "boosted_signal", "values": [100]},
            "patch": [
                {
                    "op": "replace",
                    "path": "/channels/0/samples/0/data",
                    "value": [24.0, 22.0],
                }
            ],
        }
    ],
}


@pytest.fixture
def workspace_dir(tmp_path):
    import pyhf

    patchset = json.loads(json.dumps(PATCHSET))
    patchset["metadata"]["digests"] = {"sha256": pyhf.utils.digest(WORKSPACE)}
    (tmp_path / "BkgOnly.json").write_text(json.dumps(WORKSPACE))
    (tmp_path / "patchset.json").write_text(json.dumps(patchset))
    return tmp_path


def test_compute_cls_reference_value(workspace_dir):
    # Known result for this workspace: CLs_obs ~= 0.0525 at mu=1 (pyhf docs example).
    text = compute_cls(str(workspace_dir), poi_value=1.0)
    cls_obs = float(text.split("CLs observed = ")[1].split()[0])
    assert cls_obs == pytest.approx(0.0525, abs=2e-3)
    assert "not excluded" in text


def test_compute_cls_with_patch_excludes(workspace_dir):
    # Doubling the signal yields should exclude mu=1.
    text = compute_cls(str(workspace_dir), patch_name="boosted_signal", poi_value=1.0)
    cls_obs = float(text.split("CLs observed = ")[1].split()[0])
    assert cls_obs < 0.05
    assert "EXCLUDED" in text


def test_list_patches(workspace_dir):
    text = list_patches(str(workspace_dir))
    assert "boosted_signal" in text
    assert "mass" in text


def test_missing_workspace(tmp_path):
    with pytest.raises(FileNotFoundError):
        compute_cls(str(tmp_path))
