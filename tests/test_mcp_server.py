import asyncio

from fisicai.mcp_server import mcp

EXPECTED_TOOLS = {
    "inspire_search",
    "inspire_bibtex",
    "arxiv_fetch",
    "hepdata_get",
    "hepdata_download_likelihood",
    "pyhf_list_patches",
    "pyhf_cls",
}


def test_all_tools_registered():
    tools = asyncio.run(mcp.list_tools())
    assert {t.name for t in tools} == EXPECTED_TOOLS


def test_tools_have_descriptions_and_schemas():
    tools = asyncio.run(mcp.list_tools())
    for t in tools:
        assert t.description, f"{t.name} has no description"
        assert t.inputSchema.get("properties"), f"{t.name} has no input schema"
