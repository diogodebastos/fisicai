"""HEPData records and published-likelihood downloads."""

from pathlib import Path
from typing import Any

import httpx
from claude_agent_sdk import tool

RECORD_URL = "https://www.hepdata.net/record/ins{inspire_id}"
USER_AGENT = "fisicai (https://github.com/diogodebastos/fisicai)"


def get_record(inspire_id: str | int, client: httpx.Client | None = None) -> str:
    """Summarize a HEPData record: tables and additional resources (pyhf archives etc.)."""
    own_client = client is None
    client = client or httpx.Client(
        timeout=30, headers={"User-Agent": USER_AGENT}, follow_redirects=True
    )
    try:
        resp = client.get(
            RECORD_URL.format(inspire_id=str(inspire_id).removeprefix("ins")),
            params={"format": "json"},
        )
        resp.raise_for_status()
        record = resp.json()
    finally:
        if own_client:
            client.close()

    rec = record.get("record", {})
    title = rec.get("title", "(untitled)")
    lines = [f"HEPData record for INSPIRE {inspire_id}: {title}"]

    resources = rec.get("resources", [])
    if resources:
        lines.append("\nAdditional resources:")
        for res in resources:
            desc = res.get("description", "")
            url = res.get("url", "")
            marker = "  [likelihood?] " if _looks_like_likelihood(desc, url) else "  "
            lines.append(f"{marker}{desc}: {url}")

    tables = record.get("data_tables", [])
    if tables:
        lines.append(f"\nData tables ({len(tables)}):")
        for t in tables[:40]:
            lines.append(f"  {t.get('name', '?')}: {t.get('title', '')[:120]}")
        if len(tables) > 40:
            lines.append(f"  … and {len(tables) - 40} more")

    lines.append(
        "\nTo fetch a published pyhf likelihood, pass a resource URL "
        "(usually described as 'Likelihoods' or 'statistical models', a .tar.gz or .zip) "
        "to hepdata_download_likelihood."
    )
    return "\n".join(lines)


def _looks_like_likelihood(description: str, url: str) -> bool:
    text = f"{description} {url}".lower()
    return any(k in text for k in ("likelihood", "pyhf", "statistical model", "workspace"))


def download_likelihood(
    archive_url: str, output_dir: str, compress: bool = False
) -> str:
    """Download and extract a published likelihood archive via pyhf.contrib."""
    from pyhf.contrib.utils import download as pyhf_download

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    pyhf_download(archive_url, str(out), compress=compress)

    files = sorted(p for p in out.rglob("*") if p.is_file())
    listing = "\n".join(f"  {p.relative_to(out)} ({p.stat().st_size} bytes)" for p in files[:100])
    return (
        f"Downloaded and extracted {archive_url} to {out}.\n"
        f"Files:\n{listing}\n\n"
        "Typical layout: a background-only workspace (e.g. BkgOnly.json) plus a "
        "patchset.json of signal patches. Use pyhf_list_patches and pyhf_cls next."
    )


@tool(
    "hepdata_get",
    "Fetch a HEPData record by INSPIRE record id (e.g. 1748602). Lists its data tables and "
    "additional resources, flagging ones that look like published statistical models "
    "(pyhf likelihoods). Use inspire_search first to find the INSPIRE id of a paper.",
    {"inspire_id": str},
)
async def hepdata_get(args: dict[str, Any]) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": get_record(args["inspire_id"])}]}


@tool(
    "hepdata_download_likelihood",
    "Download and extract a published pyhf likelihood archive (tar.gz/zip) from HEPData into a "
    "local directory. Pass the resource URL found via hepdata_get and an output directory.",
    {"archive_url": str, "output_dir": str},
)
async def hepdata_download_likelihood(args: dict[str, Any]) -> dict[str, Any]:
    try:
        text = download_likelihood(args["archive_url"], args["output_dir"])
    except Exception as exc:  # surface the failure to the agent, not the user
        return {
            "content": [{"type": "text", "text": f"Download failed: {exc}"}],
            "is_error": True,
        }
    return {"content": [{"type": "text", "text": text}]}


TOOLS = [hepdata_get, hepdata_download_likelihood]
