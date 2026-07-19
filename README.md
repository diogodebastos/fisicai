# fisicai

**An open-source agentic harness for high-energy physics.**

fisicai gives an AI agent the tools a particle physicist actually uses: the INSPIRE-HEP
literature database, arXiv, HEPData, the Scikit-HEP analysis stack, and — most importantly —
**published statistical likelihoods from real LHC searches**. It doesn't just talk about
papers. It reinterprets them.

```console
$ fisicai "download the pyhf likelihood for the ATLAS sbottom 1Lbb search and \
           compute the CLs exclusion for the (600, 280, 150) GeV signal point"
```

## Why

A single LHC analysis takes a team of physicists years: skims, background estimates,
systematics, multivariate discriminants, statistical interpretation. Reinterpreting that
analysis for a new theory model — the thing that makes a search scientifically durable —
usually never happens, because nobody has the time.

But the field quietly built the infrastructure to change that. ATLAS (and increasingly CMS)
now publish their **full statistical models** as [pyhf](https://pyhf.readthedocs.io) JSON
workspaces on [HEPData](https://www.hepdata.net). An agent that can read a paper, fetch its
likelihood, patch in a new signal, and run `pyhf.infer` can do in minutes what today takes a
phenomenologist weeks.

fisicai is the harness that makes that loop routine.

## What it can do today

- **Literature** — search INSPIRE-HEP, fetch arXiv abstracts and full text.
- **Data** — locate HEPData records and their resources, including published pyhf workspaces.
- **Statistics** — apply signal patches to published likelihoods and compute observed and
  expected CLs limits with `pyhf`.
- **Analysis** — the agent works in a sandbox with the Scikit-HEP stack (`uproot`, `awkward`,
  `hist`, `pyhf`, `matplotlib`) available for cutflows, histograms, and plots.

Domain knowledge lives in versioned markdown **skills** (`src/fisicai/skills/`) — how to
reinterpret a search, how to run a cutflow. This is the community contribution surface: teach
the agent your workflow by writing a skill, not by patching code.

## Quickstart

```console
$ pip install fisicai   # or: pip install -e . from a checkout
$ fisicai "find the latest CMS top squark search and summarize its exclusion reach"
$ fisicai chat          # interactive session
```

fisicai is built on the [Claude Agent SDK](https://code.claude.com/docs/en/agent-sdk) and uses
your existing Claude Code credentials (`claude` CLI login or `ANTHROPIC_API_KEY`). Select a
model with `--model` or `FISICAI_MODEL`.

## Use it from the agent you already have (MCP)

The tools are also exposed as a standard [MCP](https://modelcontextprotocol.io) server —
vendor-neutral, works with Claude Code, Cursor, opencode, LangChain adapters, or any other
MCP client:

```console
$ claude mcp add fisicai -- fisicai-mcp        # Claude Code
```

or in any MCP client config:

```json
{ "mcpServers": { "fisicai": { "command": "fisicai-mcp" } } }
```

Your agent then has `inspire_search`, `arxiv_fetch`, `hepdata_get`,
`hepdata_download_likelihood`, `pyhf_list_patches`, and `pyhf_cls`.

## Analysis bundles: the code *and* the paper

Research output isn't a chat answer — it's an analysis. `fisicai analyze` makes the agent
deliver a complete, reproducible **analysis bundle**: the analysis code, every result as
data, and a compiled LaTeX note.

```console
$ fisicai analyze "measure the Z boson mass in the Open Data dimuon skim"
```

produces:

```
analyses/<name>/
├── analysis.py        # deterministic, runs end-to-end
├── results/
│   ├── results.json   # every number the note quotes
│   └── results.tex    # auto-generated \newcommand macros (python -m fisicai.writeup)
├── figures/*.pdf
└── note/
    ├── note.tex       # quotes numbers ONLY via the macros — no hand-typed values
    ├── references.bib # every entry fetched from INSPIRE (inspire_bibtex tool)
    └── note.pdf       # compiled with tectonic
```

The invariant: **the note cannot drift from the code.** Prose numbers come from generated
macros; citations come from INSPIRE's own BibTeX; rerunning `analysis.py` regenerates the
whole artifact. See [analyses/zmumu_z_mass](analyses/zmumu_z_mass) for a complete example
produced by the agent.

## HEPAnalysisBench (HEPAbench)

How do you trust an AI with physics? You score it against results that are already known.
**HEPAbench** is a benchmark of analysis tasks with published reference answers — from a
toy-workspace CLs fit to reproducing a real ATLAS exclusion from its published likelihood.
The scorer is harness-agnostic: any agent that writes an `answer.json` can be benchmarked.

```console
$ hepabench list
$ hepabench run --offline        # tasks that need no network
$ hepabench run                  # the full suite, driven by the fisicai agent
$ hepabench score toy_cls answer.json   # score any agent's answer
```

Current v0 suite — the fisicai agent scores **4/4**:

| Task | Reference | Agent result |
|---|---|---|
| `toy_cls` — CLs fit on a toy workspace | 0.0525 (pyhf docs) | 0.05251 |
| `literature_stop_4body` — INSPIRE retrieval | arXiv:2301.08096 | exact |
| `atlas_multib_cls` — CLs from the ATLAS SUSY-2018-31 published likelihood | 0.24444 | 0.24444 |
| `opendata_zmumu` — Z mass from real CMS 2012 collision data | 91.1876 GeV (PDG) | 90.95 GeV |

The `opendata_zmumu` skim ships with the package (3.7 MB, regenerable from CERN Open Data
with `scripts/make_zmumu_skim.py`), so that task runs offline on a laptop.

Contributing a task = one YAML file with a prompt and a published reference value
(`src/fisicai/hepabench/tasks/`). Tasks that agents fail are the most valuable ones.

## Roadmap

- **M1 — Literature agent**: end-to-end INSPIRE/arXiv research tasks. *(done)*
- **M2 — Reinterpretation**: reproduce a published ATLAS exclusion point from its HEPData
  likelihood — an objective, physics-grade correctness check. *(done — see
  [examples/reinterpret_sbottom.md](examples/reinterpret_sbottom.md))*
- **M3 — Community**: grow HEPAbench (CMS Open Data cutflow tasks, more published
  likelihoods), recast scans over patchsets, simplified-likelihood support, and whatever
  the reinterpretation community asks for first.
- **Beyond**: the simulation chain for reinterpreting *new* models (MadGraph → fast sim →
  efficiency maps → patched likelihoods), and new results on new data.

## The north star

The long-term goal is not tooling — it is to advance physics itself. Agents that can hold the
entire literature, run every published likelihood, and test a theory against all existing
data at once change what a single physicist can ask. Deeper questions — unification, what
lies beyond the Standard Model — stay on this README as the direction of travel. The wedge is
making today's analyses fast, reproducible, and reinterpretable.

## Contributing

Issues and PRs welcome — especially new skills, support for more published-likelihood
formats, and reports of analyses the agent gets wrong. Physics correctness bugs are the
highest-value contributions.

## License

Apache-2.0
