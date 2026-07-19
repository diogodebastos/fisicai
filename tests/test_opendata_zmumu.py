"""The opendata_zmumu reference must be reproducible from the shipped skim itself."""

import awkward as ak
import numpy as np
import uproot
import vector

from fisicai.hepabench import load_tasks, score_answer

vector.register_awkward()


def measure_z_peak(skim_path) -> float:
    events = uproot.open(skim_path)["Events"].arrays(
        ["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge"]
    )
    muons = ak.zip(
        {
            "pt": events.Muon_pt,
            "eta": events.Muon_eta,
            "phi": events.Muon_phi,
            "mass": events.Muon_mass,
            "charge": events.Muon_charge,
        },
        with_name="Momentum4D",
    )
    muons = muons[(muons.pt > 20) & (abs(muons.eta) < 2.4)]
    pairs = muons[ak.num(muons) == 2]
    pairs = pairs[ak.sum(pairs.charge, axis=1) == 0]
    mass = ak.to_numpy((pairs[:, 0] + pairs[:, 1]).mass)
    mass = mass[(mass > 60) & (mass < 120)]
    assert len(mass) > 5000, "skim should contain thousands of Z candidates"

    counts, edges = np.histogram(mass, bins=120, range=(60, 120))
    centers = 0.5 * (edges[:-1] + edges[1:])
    i = int(np.argmax(counts))
    y0, y1, y2 = counts[i - 1], counts[i], counts[i + 1]
    return float(
        centers[i] + 0.5 * (y0 - y2) / (y0 - 2 * y1 + y2) * (edges[1] - edges[0])
    )


def test_task_is_solvable_from_shipped_skim():
    task = load_tasks()["opendata_zmumu"]
    peak = measure_z_peak(task.assets_dir / "zmumu_skim.root")
    checks = score_answer(task, {"m_z_peak": peak})
    assert all(c.passed for c in checks), f"measured {peak:.3f} GeV outside tolerance"


def test_wrong_peak_fails():
    task = load_tasks()["opendata_zmumu"]
    assert not score_answer(task, {"m_z_peak": 80.4})[0].passed  # W mass is not the Z
