**When to use:** the user asks for a full analysis with a write-up (`fisicai analyze`), a
reproducible result, an analysis note, or "the paper and the code".

The deliverable is an **analysis bundle** in the working directory:

```
analysis.py        # runs the entire analysis end-to-end; writes results/ and figures/
results/
  results.json     # every number the note quotes, as a flat/nested JSON object
  results.tex      # generated: python -m fisicai.writeup results/results.json --out results/results.tex
figures/*.pdf      # produced by analysis.py (vector PDF, one figure per file)
note/
  note.tex         # the write-up
  references.bib   # every entry fetched with inspire_bibtex — never hand-written
  note.pdf         # compiled: tectonic note/note.tex (run from the note/ directory)
README.md          # data provenance + the exact commands to regenerate everything
```

Non-negotiable rules:

1. **No hand-typed physics numbers in the note.** Every measured or computed value appears
   in `results.json` and is quoted in `note.tex` only via the `\newcommand` macros from
   `results.tex` (`\input{../results/results.tex}` in the preamble). If you want to quote
   a new number, add it to `results.json` in `analysis.py` and regenerate.
2. **analysis.py is deterministic and self-contained.** Fixed seeds if randomness is
   involved; data paths taken from CLI args with documented defaults; running it twice
   produces identical `results.json`.
3. **References come from `inspire_bibtex`.** Cite data provenance (dataset / Open Data
   record), key methods (e.g. pyhf for likelihoods), and the relevant experimental papers.
   External values you compare to (e.g. PDG averages) are *comparisons*, not results:
   name them in prose with a citation, and if you must quote the number, put it in
   `results.json` too (e.g. `m_z_pdg`) so rule 1 still holds.
4. **Write it like an experiment publication.** Start from the shipped template:
   `python -m fisicai.writeup --init-note note/` (gives `note.tex` + `hepnote.sty`).
   Structure mirrors CMS/ATLAS papers: Introduction — Detector and data — Event
   selection (cutflow as a booktabs table) — Analysis method — Systematic
   uncertainties (its own section: what is evaluated and, explicitly, what is not) —
   Results — Summary. Claim only what the analysis supports; it is an "analysis note",
   not a measurement claiming precision it doesn't have.
5. **HEP typography.** Use the `hepnote.sty` macros — `\pt`, `\abseta`, `\GeV`, `\sqs`,
   `\stat`/`\syst`, `\mmumu`, `\CLs` — never ad-hoc math like `$p_T$` or `$|eta|$`.
   Uncertainties as `\MZPeak \pm \MZPeakStat \stat \pm \MZPeakSyst \syst \GeV`.
   Selection cuts are results too: quote them via macros (`\PtMin`, `\EtaMax`).
6. **HEP figures.** Use `mplhep`: `plt.style.use(mplhep.style.CMS)`, data as black
   points with error bars, fit as a curve, axis labels with units and bin width
   ("Events / 0.5 GeV"), and `mplhep.cms.label(..., rlabel=...)` with an honest label
   (e.g. "Open Data") — never the bare experiment label, which would imply an official
   result. Vector PDF output.
7. **Verify before finishing:** run `analysis.py` fresh, regenerate `results.tex`, compile
   with tectonic, and confirm the PDF exists and the numbers in it match `results.json`.
   `hepabench validate <bundle-dir>` checks all of this — run it if available.

Keep the note to 3–6 pages.
