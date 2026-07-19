import httpx

from fisicai.tools.inspire import search_inspire

FAKE_RESPONSE = {
    "hits": {
        "hits": [
            {
                "metadata": {
                    "control_number": 2624720,
                    "titles": [
                        {
                            "title": (
                                "Search for top squarks in the four-body decay mode with "
                                "single lepton final states in proton-proton collisions "
                                "at $\\sqrt{s}$ = 13 TeV"
                            )
                        }
                    ],
                    "collaborations": [{"value": "CMS"}],
                    "arxiv_eprints": [{"value": "2301.08096"}],
                    "abstracts": [{"value": "A search for top squark pair production…"}],
                    "publication_info": [
                        {"journal_title": "JHEP", "journal_volume": "06", "year": 2023}
                    ],
                    "citation_count": 42,
                }
            }
        ]
    }
}


def _mock_client(payload, status_code=200):
    def handler(request):
        assert request.url.host == "inspirehep.net"
        return httpx.Response(status_code, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_search_formats_hit():
    text = search_inspire("title top squark", client=_mock_client(FAKE_RESPONSE))
    assert "inspire:2624720" in text
    assert "CMS Collaboration" in text
    assert "arXiv:2301.08096" in text
    assert "JHEP 06 (2023)" in text
    assert "42 citations" in text


def test_search_no_results():
    text = search_inspire("gibberish", client=_mock_client({"hits": {"hits": []}}))
    assert "No INSPIRE-HEP results" in text


BIBTEX = "@article{CMS:2023ktc,\n  collaboration = {CMS},\n  year = {2023}\n}"


def test_fetch_bibtex_routes_arxiv_vs_recid():
    from fisicai.tools.inspire import fetch_bibtex

    def handler(request):
        if "api/arxiv/" in str(request.url):
            assert str(request.url.path).endswith("2301.08096")
        else:
            assert "api/literature/1748602" in str(request.url)
        assert request.url.params["format"] == "bibtex"
        return httpx.Response(200, text=BIBTEX)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_bibtex("arXiv:2301.08096", client=client).startswith("@article")
    assert fetch_bibtex("1748602", client=client).startswith("@article")


def test_fetch_bibtex_missing():
    from fisicai.tools.inspire import fetch_bibtex

    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))
    assert "No INSPIRE record" in fetch_bibtex("999999999", client=client)
