"""INSPIRE-HEP literature search."""

from typing import Any

import httpx
from claude_agent_sdk import tool

API_URL = "https://inspirehep.net/api/literature"
BIBTEX_RECORD_URL = "https://inspirehep.net/api/literature/{recid}"
BIBTEX_ARXIV_URL = "https://inspirehep.net/api/arxiv/{arxiv_id}"
USER_AGENT = "fisicai (https://github.com/diogodebastos/fisicai)"
FIELDS = (
    "titles,authors.full_name,collaborations,arxiv_eprints,abstracts,"
    "publication_info,citation_count,control_number"
)


def search_inspire(
    query: str,
    size: int = 5,
    sort: str = "mostrecent",
    client: httpx.Client | None = None,
) -> str:
    """Search INSPIRE-HEP and return a compact plain-text summary of the hits."""
    own_client = client is None
    client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
    try:
        resp = client.get(
            API_URL,
            params={"q": query, "size": size, "sort": sort, "fields": FIELDS},
        )
        resp.raise_for_status()
        hits = resp.json().get("hits", {}).get("hits", [])
    finally:
        if own_client:
            client.close()

    if not hits:
        return f"No INSPIRE-HEP results for query: {query!r}"

    lines = []
    for hit in hits:
        meta = hit.get("metadata", {})
        lines.append(_format_hit(meta))
    return "\n\n".join(lines)


def _format_hit(meta: dict[str, Any]) -> str:
    title = (meta.get("titles") or [{}])[0].get("title", "(untitled)")
    recid = meta.get("control_number", "?")

    collabs = [c.get("value") for c in meta.get("collaborations", []) if c.get("value")]
    authors = [a.get("full_name") for a in meta.get("authors", []) if a.get("full_name")]
    if collabs:
        byline = f"{', '.join(collabs)} Collaboration"
    elif authors:
        byline = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
    else:
        byline = "(unknown authors)"

    eprints = [e.get("value") for e in meta.get("arxiv_eprints", []) if e.get("value")]
    arxiv = f"arXiv:{eprints[0]}" if eprints else "no arXiv id"

    pub = ""
    for info in meta.get("publication_info", []):
        journal = info.get("journal_title")
        if journal:
            pub = f"{journal} {info.get('journal_volume', '')} ({info.get('year', '')})"
            break

    citations = meta.get("citation_count", 0)
    abstract = (meta.get("abstracts") or [{}])[0].get("value", "")
    if len(abstract) > 600:
        abstract = abstract[:600] + "…"

    header = f"[inspire:{recid}] {title}\n  {byline} — {arxiv}"
    if pub:
        header += f" — {pub}"
    header += f" — {citations} citations"
    return f"{header}\n  {abstract}" if abstract else header


def fetch_bibtex(identifier: str, client: httpx.Client | None = None) -> str:
    """Fetch the official INSPIRE BibTeX entry for a record id or arXiv id."""
    ident = identifier.strip().removeprefix("arXiv:").removeprefix("ins")
    if "." in ident or "/" in ident:
        url = BIBTEX_ARXIV_URL.format(arxiv_id=ident)
    else:
        url = BIBTEX_RECORD_URL.format(recid=ident)

    own_client = client is None
    client = client or httpx.Client(
        timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
    try:
        resp = client.get(url, params={"format": "bibtex"})
        if resp.status_code == 404:
            return f"No INSPIRE record found for identifier {identifier!r}"
        resp.raise_for_status()
        return resp.text.strip()
    finally:
        if own_client:
            client.close()


@tool(
    "inspire_search",
    "Search the INSPIRE-HEP literature database for high-energy physics papers. "
    "Supports the full INSPIRE query syntax, e.g. 'title top squark and collaboration CMS', "
    "'a Witten and tc p', 'arxiv 2301.08096'. Returns titles, authors, arXiv ids, journal "
    "references, citation counts, abstracts, and INSPIRE record ids (needed for HEPData lookups).",
    {"query": str, "size": int, "sort": str},
)
async def inspire_search(args: dict[str, Any]) -> dict[str, Any]:
    text = search_inspire(
        args["query"],
        size=int(args.get("size") or 5),
        sort=args.get("sort") or "mostrecent",
    )
    return {"content": [{"type": "text", "text": text}]}


@tool(
    "inspire_bibtex",
    "Fetch the official BibTeX entry for a paper from INSPIRE-HEP, by INSPIRE record id "
    "(e.g. 1748602) or arXiv id (e.g. 2301.08096). Always use this for references.bib "
    "entries — never write BibTeX by hand.",
    {"identifier": str},
)
async def inspire_bibtex(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": fetch_bibtex(args["identifier"])}]}


TOOLS = [inspire_search, inspire_bibtex]
