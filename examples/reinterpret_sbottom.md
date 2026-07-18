# Example: reinterpreting the ATLAS sbottom multi-b search from its published likelihood

This walkthrough reproduces a real statistical result of an ATLAS SUSY search using only
public artifacts — the exact loop fisicai's agent runs when you ask it to reinterpret a
search.

**Analysis:** Search for bottom-squark pair production in final states with Higgs bosons,
b-jets and missing transverse momentum (ATLAS SUSY-2018-31,
[arXiv:1908.03122](https://arxiv.org/abs/1908.03122), INSPIRE
[1748602](https://inspirehep.net/literature/1748602)).

## Agent-driven

```console
$ fisicai "Download the published pyhf likelihood of the ATLAS sbottom multi-b search \
           (INSPIRE 1748602), and compute the observed and expected CLs for the \
           sbottom_1300_205_60 signal point in Region A."
```

The agent chains `hepdata_get` → `hepdata_download_likelihood` → `pyhf_list_patches` →
`pyhf_cls` (see the `reinterpretation` skill).

## By hand, with the same tools

```python
from fisicai.tools.hepdata import get_record, download_likelihood
from fisicai.tools.pyhf_tools import list_patches, compute_cls

# 1. The HEPData record lists an "Archive of full likelihoods in the HistFactory
#    JSON format" among its resources:
print(get_record(1748602))

# 2. Download and extract it (RegionA/B/C, each with BkgOnly.json + patchset.json):
download_likelihood(
    "https://www.hepdata.net/record/resource/1935437?view=true",
    "workspace/sbottom_multib",
)

# 3. Signal points are patches named sbottom_<msb>_<mn2>_<mn1>:
print(list_patches("workspace/sbottom_multib/RegionA"))

# 4. Fit:
print(compute_cls("workspace/sbottom_multib/RegionA", patch_name="sbottom_1300_205_60"))
```

## Result

```
Workspace: workspace/sbottom_multib/RegionA/BkgOnly.json + patch 'sbottom_1300_205_60'
POI (signal strength mu) = 1.0
CLs observed = 0.24444  -> not excluded at 95% CL
CLs expected band (-2s, -1s, median, +1s, +2s) = 0.09022, 0.19378, 0.38432, 0.65577, 0.89104
```

**Validation:** the observed CLs for this point, 0.24444, matches the reference value
obtained from this published likelihood in the
[pyhf documentation](https://pyhf.readthedocs.io/en/stable/examples/notebooks/learn/UsingCalculators.html)
(0.2444362776) — i.e. fisicai reproduces the analysis's own statistical model exactly,
not a digitized approximation of its exclusion curve.

The point (m_sbottom = 1300 GeV, m_chi2 = 205 GeV, m_chi1 = 60 GeV) is *not* excluded at
95% CL in Region A alone — consistent with the published contour, where sensitivity at
low chi2 masses is driven by the other regions.
