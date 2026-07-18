**When to use:** the user wants to reinterpret, recast, or reproduce the exclusion of a
published LHC search, or check whether a signal model is excluded.

Workflow:

1. **Find the paper.** `inspire_search` for the analysis (e.g. `title sbottom and
   collaboration ATLAS`). Note the INSPIRE record id.
2. **Locate the statistical model.** `hepdata_get` with that INSPIRE id. Look for resources
   flagged `[likelihood?]` — ATLAS publishes "full likelihoods" as pyhf JSON archives
   (HistFactory format). If no likelihood is published, say so and fall back to digitized
   exclusion curves from the data tables (clearly labelled as an approximation).
3. **Download.** `hepdata_download_likelihood` with the resource URL into a directory named
   after the analysis (e.g. `sbottom_1Lbb/`). Some records publish one archive per signal
   region — download the one matching the region of interest.
4. **Enumerate signal points.** `pyhf_list_patches` — patch names encode the signal
   hypothesis masses.
5. **Compute.** `pyhf_cls` with the chosen patch at mu=1. CLs < 0.05 ⇒ excluded at 95% CL.
   Report observed and expected CLs together.
6. **Validate.** Cross-check at least one point against the published exclusion contour
   (from the paper or a HEPData table) before trusting a scan.

Caveats to state in results: published likelihoods reflect the analysis's own signal
implementation; reinterpreting for a *different* model than the patchset covers requires
new signal yields (out of scope for the patchset — needs simulation + efficiency maps).
