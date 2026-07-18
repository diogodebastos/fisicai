"""Standalone MCP server exposing fisicai's HEP tools to any MCP client.

Run with `fisicai-mcp` (stdio transport). This uses the official `mcp` package, so it
works with Claude Code, Cursor, opencode, LangChain MCP adapters, or any other client —
no dependency on the fisicai harness.
"""

from mcp.server.fastmcp import FastMCP

from fisicai.tools import arxiv, hepdata, inspire, pyhf_tools

mcp = FastMCP(
    "fisicai",
    instructions=(
        "HEP-native tools: INSPIRE-HEP literature search, arXiv retrieval, HEPData "
        "records, published pyhf likelihood download, and CLs inference. Typical "
        "reinterpretation flow: inspire_search -> hepdata_get -> "
        "hepdata_download_likelihood -> pyhf_list_patches -> pyhf_cls."
    ),
)


@mcp.tool()
def inspire_search(query: str, size: int = 5, sort: str = "mostrecent") -> str:
    """Search the INSPIRE-HEP literature database for high-energy physics papers.

    Supports the full INSPIRE query syntax, e.g. 'title top squark and collaboration CMS',
    'a Witten and tc p', 'arxiv 2301.08096'. Returns titles, authors, arXiv ids, journal
    references, citation counts, abstracts, and INSPIRE record ids (needed for HEPData).
    """
    return inspire.search_inspire(query, size=size, sort=sort)


@mcp.tool()
def arxiv_fetch(arxiv_id: str, section: str = "abstract") -> str:
    """Fetch an arXiv paper.

    section='abstract' returns title, authors, and abstract; section='fulltext' returns
    the plain-text body from arXiv's HTML rendering (availability varies by paper).
    """
    if section.lower() == "fulltext":
        return arxiv.fetch_fulltext(arxiv_id)
    return arxiv.fetch_abstract(arxiv_id)


@mcp.tool()
def hepdata_get(inspire_id: str) -> str:
    """Fetch a HEPData record by INSPIRE record id (e.g. 1748602).

    Lists its data tables and additional resources, flagging ones that look like
    published statistical models (pyhf likelihoods).
    """
    return hepdata.get_record(inspire_id)


@mcp.tool()
def hepdata_download_likelihood(archive_url: str, output_dir: str) -> str:
    """Download and extract a published pyhf likelihood archive from HEPData.

    Pass the resource URL found via hepdata_get and a local output directory.
    """
    return hepdata.download_likelihood(archive_url, output_dir)


@mcp.tool()
def pyhf_list_patches(workspace_dir: str) -> str:
    """List the signal patches (model points) in a downloaded published-likelihood
    directory containing a patchset.json."""
    return pyhf_tools.list_patches(workspace_dir)


@mcp.tool()
def pyhf_cls(workspace_dir: str, patch_name: str = "", poi_value: float = 1.0) -> str:
    """Compute observed and expected CLs for a pyhf workspace at a given signal strength.

    Pass the directory containing the background-only workspace (and patchset.json), and
    optionally a patch_name selecting the signal point. CLs < 0.05 means excluded at
    95% CL. Runs a real maximum-likelihood fit; large workspaces can take minutes.
    """
    return pyhf_tools.compute_cls(
        workspace_dir, patch_name=patch_name or None, poi_value=poi_value
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
