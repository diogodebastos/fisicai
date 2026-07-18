import httpx

from fisicai.tools.arxiv import fetch_abstract, fetch_fulltext

ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>Search for top squarks in the four-body decay mode</title>
    <summary>A search for top squark pair production is presented.</summary>
    <author><name>CMS Collaboration</name></author>
  </entry>
</feed>
"""


def _client(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_abstract():
    def handler(request):
        assert request.url.params["id_list"] == "2301.08096"
        return httpx.Response(200, text=ATOM_FEED)

    text = fetch_abstract("2301.08096", client=_client(handler))
    assert "top squarks" in text
    assert "CMS Collaboration" in text
    assert "pair production" in text


def test_fetch_fulltext_strips_html():
    html = "<html><head><style>x{}</style></head><body><p>Hello <b>physics</b></p></body></html>"
    text = fetch_fulltext("2301.08096", client=_client(lambda r: httpx.Response(200, text=html)))
    assert "Hello" in text and "physics" in text
    assert "<" not in text


def test_fetch_fulltext_missing():
    text = fetch_fulltext("hep-ph/9901234", client=_client(lambda r: httpx.Response(404)))
    assert "No HTML full text" in text
