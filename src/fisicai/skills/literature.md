**When to use:** the user asks about papers, results, limits, or the status of a search
program.

Guidelines:

- Search INSPIRE with its query syntax: `title X`, `a Lastname`, `collaboration CMS`,
  `arxiv NNNN.NNNNN`, `tc p` (published papers only), combined with `and`.
- For experimental results, prefer the latest full-luminosity (Run 2: 138–140 fb⁻¹, Run 3
  where available) publication over conference notes and superseded preliminary results.
- Quote exclusion limits precisely: which masses, which simplified model, which decay
  assumptions, observed vs expected. Small print matters — compressed-spectrum regions
  often have much weaker limits than the headline number.
- Always give the arXiv id and, when relevant, the INSPIRE record id (needed for HEPData).
- Use `arxiv_fetch` with section='fulltext' when the abstract is not enough; fall back to
  WebFetch on the arXiv abs page if HTML is unavailable.
