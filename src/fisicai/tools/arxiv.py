"""arXiv abstract and full-text retrieval."""

import re
import xml.etree.ElementTree as ET
from typing import Any

import httpx
from claude_agent_sdk import tool

EXPORT_URL = "https://export.arxiv.org/api/query"
HTML_URL = "https://arxiv.org/html/{arxiv_id}"
USER_AGENT = "fisicai (https://github.com/diogodebastos/fisicai)"
ATOM = "{http://www.w3.org/2005/Atom}"
MAX_FULLTEXT_CHARS = 60_000


def fetch_abstract(arxiv_id: str, client: httpx.Client | None = None) -> str:
    """Fetch title, authors, and abstract for an arXiv id via the export API."""
    own_client = client is None
    client = client or httpx.Client(timeout=30, headers={"User-Agent": USER_AGENT})
    try:
        resp = client.get(EXPORT_URL, params={"id_list": arxiv_id})
        resp.raise_for_status()
        root = ET.fromstring(resp.text)
    finally:
        if own_client:
            client.close()

    entry = root.find(f"{ATOM}entry")
    if entry is None:
        return f"No arXiv entry found for id {arxiv_id!r}"
    title = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM}title") or "").strip())
    summary = re.sub(r"\s+", " ", (entry.findtext(f"{ATOM}summary") or "").strip())
    authors = [
        a.findtext(f"{ATOM}name") or "" for a in entry.findall(f"{ATOM}author")
    ]
    byline = ", ".join(authors[:5]) + (" et al." if len(authors) > 5 else "")
    return f"arXiv:{arxiv_id}\n{title}\n{byline}\n\n{summary}"


def fetch_fulltext(arxiv_id: str, client: httpx.Client | None = None) -> str:
    """Fetch the paper's HTML rendering and strip it to plain text (best effort)."""
    own_client = client is None
    client = client or httpx.Client(
        timeout=60, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
    try:
        resp = client.get(HTML_URL.format(arxiv_id=arxiv_id))
        if resp.status_code != 200:
            return (
                f"No HTML full text available for arXiv:{arxiv_id} "
                f"(HTTP {resp.status_code}). Use the abstract, or fetch the PDF another way."
            )
        text = resp.text
    finally:
        if own_client:
            client.close()

    text = re.sub(r"(?is)<(script|style|head)[^>]*>.*?</\1>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) > MAX_FULLTEXT_CHARS:
        text = text[:MAX_FULLTEXT_CHARS] + "\n\n[…truncated…]"
    return text


@tool(
    "arxiv_fetch",
    "Fetch an arXiv paper. section='abstract' returns title, authors, and abstract; "
    "section='fulltext' returns the plain-text body from arXiv's HTML rendering "
    "(availability varies; older papers may not have HTML).",
    {"arxiv_id": str, "section": str},
)
async def arxiv_fetch(args: dict[str, Any]) -> dict[str, Any]:
    section = (args.get("section") or "abstract").lower()
    if section == "fulltext":
        text = fetch_fulltext(args["arxiv_id"])
    else:
        text = fetch_abstract(args["arxiv_id"])
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [arxiv_fetch]
