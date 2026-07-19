"""Create the HEPAbench opendata_zmumu skim from CERN Open Data.

Source: CMS DoubleMuParked 2012 B+C dimuon NanoAOD-style outreach file
(CERN Open Data record 12341-12342 derived data, AOD2NanoAODOutreachTool):
https://opendata.web.cern.ch/eos/opendata/cms/derived-data/AOD2NanoAODOutreachTool/Run2012BC_DoubleMuParked_Muons.root

We keep the first N events that contain at least two muons, with all muon branches,
so the benchmark task stays laptop-sized and offline while remaining real collision data.
Event selection beyond "has two muons" is deliberately left to the agent being benchmarked.
"""

import argparse
from pathlib import Path

import awkward as ak
import numpy as np
import uproot

SOURCE_URL = (
    "https://opendata.web.cern.ch/eos/opendata/cms/derived-data/"
    "AOD2NanoAODOutreachTool/Run2012BC_DoubleMuParked_Muons.root"
)
DEFAULT_OUT = (
    Path(__file__).parent.parent
    / "src/fisicai/hepabench/data/opendata_zmumu/zmumu_skim.root"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entries", type=int, default=400_000, help="Events to read.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    tree = uproot.open(SOURCE_URL)["Events"]
    events = tree.arrays(
        ["nMuon", "Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge"],
        entry_stop=args.entries,
    )
    skim = events[events.nMuon >= 2]
    print(f"read {len(events)} events, kept {len(skim)} with nMuon >= 2")

    branches = {
        "Muon_pt": ak.values_astype(skim.Muon_pt, np.float32),
        "Muon_eta": ak.values_astype(skim.Muon_eta, np.float32),
        "Muon_phi": ak.values_astype(skim.Muon_phi, np.float32),
        "Muon_mass": ak.values_astype(skim.Muon_mass, np.float32),
        "Muon_charge": ak.values_astype(skim.Muon_charge, np.int32),
    }
    types = {name: "var * float32" for name in branches} | {"Muon_charge": "var * int32"}

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.unlink(missing_ok=True)  # recreate over an existing file leaves stale allocation
    with uproot.recreate(args.out, compression=uproot.ZLIB(6)) as f:
        f.mktree("Events", types)
        f["Events"].extend(branches)
    size_mb = args.out.stat().st_size / 1e6
    print(f"wrote {args.out} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
