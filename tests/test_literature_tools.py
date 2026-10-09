from research_assistant.tools import literature_tools as lt


def test_ingest_success(monkeypatch):
    def fake_search(query, limit):
        return {
            "status": "success",
            "count": 2,
            "skipped_no_abstract": 1,
            "papers": [
                {
                    "pub_id": "MED:1",
                    "title": "A",
                    "year": "2024",
                    "abstract": "long text",
                },
                {
                    "pub_id": "MED:2",
                    "title": "B",
                    "year": "2023",
                    "abstract": "long text",
                },
            ],
        }

    def fake_add(papers):
        return {
            "status": "success",
            "added": 2,
            "already_stored": 0,
            "total_in_store": 2,
        }

    monkeypatch.setattr(lt, "search_europepmc", fake_search)
    monkeypatch.setattr(lt, "add_papers", fake_add)

    result = lt.ingest_literature("KRAS")

    assert result["status"] == "success"
    assert (
        result["found"] == 2
        and result["skipped_no_abstract"] == 1
        and result["added"] == 2
    )
    assert [p["pub_id"] for p in result["papers"]] == ["MED:1", "MED:2"]
    assert all("abstract" not in p for p in result["papers"])


def test_ingest_search_not_successful(monkeypatch):
    def fake_search(query, limit):
        return {
            "status": "not_found",
            "query": query,
            "error_message": "No publications found in Europe PMC.",
        }

    def must_not_be_called(papers):
        raise AssertionError("add_papers should not be called")

    monkeypatch.setattr(lt, "search_europepmc", fake_search)
    monkeypatch.setattr(lt, "add_papers", must_not_be_called)

    result = lt.ingest_literature("nothing")

    assert result["status"] == "not_found"


def test_ingest_no_abstracts(monkeypatch):
    def fake_search(query, limit):
        return {"status": "success", "count": 0, "skipped_no_abstract": 3, "papers": []}

    def must_not_be_called(papers):
        raise AssertionError("add_papers should not be called")

    monkeypatch.setattr(lt, "search_europepmc", fake_search)
    monkeypatch.setattr(lt, "add_papers", must_not_be_called)

    result = lt.ingest_literature("KRAS")

    assert result["status"] == "not_found"
    assert "3" in result["error_message"]


def test_ingest_add_returns_error(monkeypatch):
    def fake_search(query, limit):
        return {
            "status": "success",
            "count": 1,
            "skipped_no_abstract": 0,
            "papers": [
                {"pub_id": "MED:1", "title": "A", "year": "2024", "abstract": "x"}
            ],
        }

    def fake_add(papers):
        return {"status": "error", "error_message": "No papers to add."}

    monkeypatch.setattr(lt, "search_europepmc", fake_search)
    monkeypatch.setattr(lt, "add_papers", fake_add)

    result = lt.ingest_literature("KRAS")

    assert result["status"] == "error"
    assert result["error_message"] == "No papers to add."


def test_ingest_add_crashes(monkeypatch):
    def fake_search(query, limit):
        return {
            "status": "success",
            "count": 1,
            "skipped_no_abstract": 0,
            "papers": [
                {"pub_id": "MED:1", "title": "A", "year": "2024", "abstract": "x"}
            ],
        }

    def fake_add(papers):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(lt, "search_europepmc", fake_search)
    monkeypatch.setattr(lt, "add_papers", fake_add)

    result = lt.ingest_literature("KRAS")

    assert result["status"] == "error"
    assert "Could not store papers" in result["error_message"]
    assert "quota exceeded" in result["error_message"]


def test_search_literature_passes_result(monkeypatch):
    expected = {"status": "success", "question": "q", "count": 0, "papers": []}

    monkeypatch.setattr(lt, "search_papers", lambda question, k: expected)

    assert lt.search_literature("q") == expected


def test_search_literature_error(monkeypatch):
    def fake_search_papers(question, k):
        raise RuntimeError("quota exceeded")

    monkeypatch.setattr(lt, "search_papers", fake_search_papers)

    result = lt.search_literature("q")

    assert result["status"] == "error"
    assert "Could not search" in result["error_message"]
