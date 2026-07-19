# Recorded HEPAbench runs

Each directory holds the `answer.json` an agent actually produced for one HEPAbench
task, kept in-repo so the benchmark claims in the top-level README are auditable and
continuously re-scored in CI:

```console
$ hepabench score <task_id> hepabench_results/<task_id>/answer.json
```

These answers were produced by the fisicai agent (Claude Agent SDK harness,
model `claude-fable-5`, the package default) on 2026-07-18/19, with the agent
driven end-to-end by `hepabench run` — no human edits to the answers.

| Task | Answer | Reference |
|---|---|---|
| `toy_cls` | CLs = 0.05251 | 0.0525 (pyhf docs) |
| `literature_stop_4body` | arXiv:2301.08096 | exact match |
| `atlas_multib_cls` | CLs = 0.24444 | 0.24444 (ATLAS SUSY-2018-31 published likelihood) |
| `opendata_zmumu` | m_Z = 90.948 GeV | 91.1876 GeV (PDG; tolerance set by task) |

To add a run for a new task (or a new agent), commit its `answer.json` under
`hepabench_results/<task_id>/` and note the agent, model, and date here. Scoring is
harness-agnostic: any agent that writes an `answer.json` can be recorded.
