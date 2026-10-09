import pytest
from rag import store


@pytest.fixture
def fake_store(monkeypatch, tmp_path):
    calls = []

    def fake_embed(texts, task_type):
        calls.append(texts)
        return [[float(len(t)), 1.0, 0.0] for t in texts]

    monkeypatch.setattr(store, "CHROMA_PATH", tmp_path / "chroma")
    monkeypatch.setattr(store, "_embed", fake_embed)
    return calls


def make_paper(pub_id, title="Some title", abstract="Some abstract."):
    return {
        "pub_id": pub_id,
        "title": title,
        "abstract": abstract,
        "authors": None,
        "journal": None,
        "year": "2024",
        "pmid": None,
        "doi": None,
        "link": None,
    }


def test_add_papers_empty_list(fake_store):
    result = store.add_papers([])

    assert result["status"] == "error"


def test_add_papers_stores_new_papers(fake_store):
    result = store.add_papers([make_paper("MED:1"), make_paper("MED:2")])

    assert result["status"] == "success"
    assert result["added"] == 2
    assert result["already_stored"] == 0
    assert result["total_in_store"] == 2
    assert len(fake_store) == 1


def test_add_papers_skips_already_stored(fake_store):
    papers = [make_paper("MED:1"), make_paper("MED:2")]
    store.add_papers(papers)              
    result = store.add_papers(papers)     

    assert result["added"] == 0
    assert result["already_stored"] == 2
    assert result["total_in_store"] == 2 
    assert len(fake_store) == 1           


def test_add_papers_partial_overlap(fake_store):
    store.add_papers([make_paper("MED:A"), make_paper("MED:B")])
    result = store.add_papers([make_paper("MED:B"), make_paper("MED:C")])

    assert result["added"] == 1          
    assert result["already_stored"] == 1  
    assert result["total_in_store"] == 3  


def test_search_papers_empty_store(fake_store):
    result = store.search_papers("KRAS G12C", k=3)

    assert result["status"] == "not_found"


def test_search_papers_returns_results(fake_store):
    store.add_papers([make_paper("MED:1", title="KRAS paper"),
                      make_paper("MED:2", title="EGFR paper")])

    result = store.search_papers("anything", k=1)

    assert result["status"] == "success"
    assert result["count"] == 1
    paper = result["papers"][0]
    assert paper["pub_id"] in {"MED:1", "MED:2"}
    assert paper["title"] in {"KRAS paper", "EGFR paper"}
    assert "similarity" in paper


@pytest.mark.parametrize("question, k", [("", 3), ("   ", 3), ("KRAS", 0), ("KRAS", 11)])
def test_search_papers_invalid_input(fake_store, question, k):
    result = store.search_papers(question, k)

    assert result["status"] == "error"
