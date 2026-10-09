import httpx
import pytest

from rag import europepmc


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Unexpected real HTTP request in a test")

    monkeypatch.setattr(europepmc.httpx, "get", fail)


@pytest.fixture
def mock_response(monkeypatch):
    def _mock(results):
        def fake_get(url, **kwargs):
            return httpx.Response(
                200,
                json={"resultList": {"result": results}},
                request=httpx.Request("GET", url),
            )

        monkeypatch.setattr(europepmc.httpx, "get", fake_get)

    return _mock


def make_paper(pub_id, **overrides):
    paper = {
        "id": pub_id,
        "source": "MED",
        "pmid": pub_id,
        "title": f"Paper {pub_id}",
        "abstractText": "Scientific abstract.",
        "pubYear": "2020",
    }
    paper.update(overrides)
    return paper


def test_two_papers_with_abstracts(mock_response):
    mock_response([make_paper("123"), make_paper("456")])

    result = europepmc.search_europepmc("KRAS G12C")

    assert result["status"] == "success"
    assert result["source"] == "Europe PMC"
    assert result["count"] == 2
    assert result["skipped_no_abstract"] == 0
    assert result["papers"][0]["pub_id"] == "MED:123"
    assert result["papers"][0]["link"] == "https://pubmed.ncbi.nlm.nih.gov/123/"
    assert result["papers"][1]["pub_id"] == "MED:456"


def test_skips_papers_without_abstract(mock_response):
    mock_response(
        [
            make_paper("123"),
            make_paper("456", abstractText=None),
            make_paper("789"),
        ]
    )

    result = europepmc.search_europepmc("KRAS")

    assert result["status"] == "success"
    assert result["count"] == 2
    assert result["skipped_no_abstract"] == 1
    assert len(result["papers"]) == 2
    assert all(p["pub_id"] != "MED:456" for p in result["papers"])


def test_doi_link_when_pmid_missing(mock_response):
    mock_response(
        [
            make_paper(
                "PREPRINT123",
                source="PPR",
                pmid=None,
                doi="10.1101/2024.01.01.123456",
            )
        ]
    )

    result = europepmc.search_europepmc("preprint")

    assert result["status"] == "success"
    assert result["papers"][0]["pub_id"] == "PPR:PREPRINT123"
    assert result["papers"][0]["link"] == ("https://doi.org/10.1101/2024.01.01.123456")


def test_empty_results(mock_response):
    mock_response([])

    result = europepmc.search_europepmc("nonexistent topic")

    assert result["status"] == "not_found"
    assert result["error_message"] == "No publications found in Europe PMC."


def test_request_parameters(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs["params"]
        captured["timeout"] = kwargs["timeout"]

        return httpx.Response(
            200,
            json={"resultList": {"result": []}},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(europepmc.httpx, "get", fake_get)

    europepmc.search_europepmc("KRAS G12C", limit=7)

    assert captured["url"] == (
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
    )
    assert captured["params"]["query"] == "KRAS G12C"
    assert captured["params"]["resultType"] == "core"
    assert captured["params"]["format"] == "json"
    assert captured["params"]["pageSize"] == 7
    assert "q" not in captured["params"]
    assert captured["timeout"] == 30


@pytest.mark.parametrize(
    "query, limit",
    [
        ("", 10),
        ("   ", 10),
        ("KRAS", 0),
        ("KRAS", 26),
    ],
)
def test_invalid_input_does_not_make_request(monkeypatch, query, limit):
    def blocked_get(*args, **kwargs):
        pytest.fail("HTTP request should not be made for invalid input")

    monkeypatch.setattr(europepmc.httpx, "get", blocked_get)

    result = europepmc.search_europepmc(query, limit)

    assert result["status"] == "error"
    assert result["query"] == query
    assert "error_message" in result


def test_timeout(monkeypatch):
    def fake_get(url, **kwargs):
        raise httpx.TimeoutException("Request timed out")

    monkeypatch.setattr(europepmc.httpx, "get", fake_get)

    result = europepmc.search_europepmc("KRAS")

    assert result["status"] == "error"
    assert "Could not connect to Europe PMC" in result["error_message"]
    assert "ChEMBL" not in result["error_message"]


def test_missing_title(mock_response):
    paper = make_paper("123")
    del paper["title"]

    mock_response([paper])

    result = europepmc.search_europepmc("KRAS")

    assert result["status"] == "success"
    assert result["count"] == 1
    assert result["papers"][0]["title"] == ""


# testing _clean_text function
@pytest.mark.parametrize(
    "raw, expected",
    [
        ("<b>Background</b><p>KRAS", "Background KRAS"),
        ("&lt;i&gt;KRAS&lt;/i&gt;", "KRAS"),
        ("A &amp; B", "A & B"),
        ("KRAS   G12C", "KRAS G12C"),
    ],
)
def test_clean_text(raw, expected):
    assert europepmc._clean_text(raw) == expected
