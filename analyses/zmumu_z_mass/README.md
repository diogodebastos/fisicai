# Z → μμ peak position — CMS 2012 Open Data analysis bundle

A self-contained, reproducible determination of the dimuon Z-resonance peak
position in real CMS collision data. The fitted result and all quoted numbers
live in `results/results.json`; the write-up in `note/note.pdf` quotes them
exclusively through generated LaTeX macros, so code and note cannot drift apart.

## Data provenance

- **Input:** `zmumu_skim.root` — a skim of the CMS 2012 `DoubleMuParked`
  primary dataset (proton–proton collisions at √s = 8 TeV), published on the
  [CERN Open Data portal](https://opendata.cern.ch) and converted to a flat
  NanoAOD-like format with the CMS `AOD2NanoAODOutreachTool`.
- **Default local path:**
  `/Users/ketchum/REPOS/fisicai/src/fisicai/hepabench/data/opendata_zmumu/zmumu_skim.root`
  (override with `--data PATH`).
- Branches used: `Muon_pt`, `Muon_eta`, `Muon_phi`, `Muon_mass`,
  `Muon_charge` (GeV). Raw event counts only — no luminosity weighting.

## Bundle layout

```
analysis.py        # full analysis: selection, histogram, Voigtian+exp fit
results/
  results.json     # every number the note quotes
  results.tex      # generated LaTeX macros (do not edit by hand)
figures/
  dimuon_mass.pdf  # dimuon mass spectrum with fit (produced by analysis.py)
note/
  note.tex         # analysis note (quotes numbers only via results.tex macros)
  references.bib   # fetched from INSPIRE-HEP via inspire_bibtex
  note.pdf         # compiled note
```

## Regenerating everything

From this directory, using a Python environment with the Scikit-HEP stack
(`uproot`, `awkward`, `hist`, `scipy`, `matplotlib`) and `fisicai` installed
(e.g. the repo venv, `/Users/ketchum/REPOS/fisicai/.venv/bin/python`):

```sh
# 1. Run the analysis: writes results/results.json and figures/dimuon_mass.pdf.
#    Deterministic — no randomness; running twice gives identical output.
python analysis.py            # or: python analysis.py --data /path/to/zmumu_skim.root

# 2. Generate the LaTeX macros from the results
python -m fisicai.writeup results/results.json --out results/results.tex

# 3. Compile the note (run from note/ so ../results and ../figures resolve)
cd note && tectonic note.tex
```

The result: the fitted peak position, its statistical uncertainty from the
fit, and a fit-range systematic are stored in `results.json` under
`m_z_peak`, `m_z_peak_stat`, and `m_z_peak_syst_range`. See `note/note.pdf`
for the full selection, method, and uncertainty discussion — including which
systematics are *not* evaluated (muon momentum scale, FSR modeling, signal
and background shape choices).
