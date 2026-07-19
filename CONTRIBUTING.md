# Contributing to fisicai

Thanks for your interest! The highest-value contributions, in order:

1. **Physics correctness bugs** — the agent quoted a wrong number, misread a likelihood,
   or mishandled a statistical convention. Open an issue with the exact prompt and what
   the right answer is (with a citable source). These are gold.
2. **HEPAbench tasks** — especially ones the agent *fails*.
3. **Skills** — teach the agent a workflow by writing markdown, not code.
4. Code: new tools, more published-likelihood formats, harness improvements.

## Dev setup

```console
$ git clone https://github.com/diogodebastos/fisicai && cd fisicai
$ python -m venv .venv && source .venv/bin/activate
$ pip install -e ".[dev]"
$ ruff check . && pytest -q       # what CI runs
```

Running the agent (`fisicai`, `hepabench run`) needs Claude Code credentials
(`claude` CLI login or `ANTHROPIC_API_KEY`). Everything else — the tests, the scorer,
`hepabench validate` — is offline and free.

## Adding a HEPAbench task

A task is one YAML file in `src/fisicai/hepabench/tasks/` with a prompt and a
**published reference answer**:

```yaml
id: my_task
title: One-line description
network: false            # true if the task needs INSPIRE/HEPData/arXiv access
assets: my_task           # optional: dir under hepabench/data/ copied into the workdir
tags: [statistics, pyhf, offline]
prompt: |
  Self-contained instructions. State units, conventions (CLs, 95% CL, qtilde),
  and exactly what to compute.
answer_keys: [cls_obs]
reference:
  cls_obs: {value: 0.0525, abs_tol: 0.003}
```

Ground rules:

- **The reference must be citable**: a PDG value, a number in a published paper,
  a value reproducible from a published statistical model. Never "what the agent
  happened to output".
- Tolerances should reflect the physics (statistical precision of the reference),
  not the agent's current ability.
- Offline tasks (small committed assets, like the 3.7 MB Z→μμ skim) are the most
  valuable: everyone can run them, including CI.
- If you also run an agent on your task, commit its `answer.json` under
  `hepabench_results/<task_id>/` and add a row to the table there.

Tasks that current agents fail are *especially* welcome — that's the frontier the
benchmark exists to map.

## Writing a skill

Skills live in `src/fisicai/skills/*.md` and are appended to the agent's system prompt.
A good skill reads like instructions to a new grad student: the workflow, the checks,
the conventions, the failure modes. See `reinterpretation.md` for the tone. Keep it
under ~100 lines; link to papers rather than reproducing them.

## Analysis bundles

If you touch the bundle machinery (`fisicai analyze`, `fisicai.writeup`,
`hepabench validate`), the invariant to preserve is: **the note cannot drift from the
code**. Numbers flow results.json → generated macros → note; citations come from
INSPIRE BibTeX; `hepabench validate <bundle>` must pass on the shipped bundle
(CI enforces this).

## Pull requests

- One logical change per PR; include tests for new code paths.
- `ruff check .` and `pytest -q` must pass.
- For physics-affecting changes, say in the PR what you validated against
  (published value, pyhf reference, independent calculation).
