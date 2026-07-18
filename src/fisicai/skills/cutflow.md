**When to use:** the user wants event selections, cutflows, histograms, or kinematic
distributions from a ROOT file (e.g. CERN Open Data NanoAOD).

Guidelines:

- Use `uproot` + `awkward` in a Python script; never load whole trees when a few branches
  suffice (`tree.arrays(branches, cut=...)`, or iterate in chunks for large files).
- Build histograms with `hist` and plot with `matplotlib` (`mplhep` style if available).
  Save plots as PNG in the working directory and report their paths.
- Report cutflows as a table: cut name, events passing, absolute efficiency, relative
  efficiency. State the luminosity/weighting assumptions explicitly (raw event counts vs
  weighted yields).
- Common NanoAOD conventions: `Muon_pt`, `Electron_pt`, `Jet_pt` are jagged arrays; missing
  transverse momentum is `MET_pt`/`PuppiMET_pt`; generator weight is `genWeight`.
- Sanity-check every selection by printing the number of events before and after.
