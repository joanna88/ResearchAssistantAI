from rag.europepmc import search_europepmc
from rag.store import add_papers, search_papers


def ingest_literature(query: str, limit: int = 10) -> dict:
    """Retrieve scientific publications from Europe PMC and store them locally.

    Searches Europe PMC for publications matching the query and stores their
    embeddings and metadata in the persistent ChromaDB collection. Publications
    without abstracts are skipped, and previously stored papers are not duplicated.

    Use this tool to populate the local literature store before performing
    semantic searches with `search_literature`. Successful ingestion does not
    establish that the retrieved papers support a specific scientific claim.

    Args:
        query: Scientific literature search query, e.g. "KRAS G12C inhibitors".
            Supports Europe PMC search syntax.
        limit: Maximum number of publication records to retrieve (1-25).
            Defaults to 10.

    Returns:
        dict: Operation status and ingestion summary, including:
            - status: "success", "not_found", or "error".
            - query: Original literature search query.
            - found: Number of retrieved publications with abstracts.
            - skipped_no_abstract: Number of excluded publications.
            - added: Number of newly stored papers.
            - already_stored: Number of previously stored papers.
            - total_in_store: Total number of papers in the collection.
            - papers: List of retrieved publication IDs, titles, and years.
            - error_message: Description of the issue when applicable.
    """

    result = search_europepmc(query, limit)

    if result["status"] != "success":
        return result

    if result["count"] == 0:
        return {
            "status": "not_found",
            "query": query,
            "error_message": f"Europe PMC found {result['skipped_no_abstract']} papers, but none had an abstract.",
        }

    try:
        stored = add_papers(result["papers"])
        if stored["status"] != "success":
            return stored
        return {
            "status": "success",
            "query": query,
            "found": result["count"],
            "skipped_no_abstract": result["skipped_no_abstract"],
            "added": stored["added"],
            "already_stored": stored["already_stored"],
            "total_in_store": stored["total_in_store"],
            "papers": [
                {"pub_id": p["pub_id"], "title": p["title"], "year": p["year"]}
                for p in result["papers"]
            ],
        }

    except Exception as e:
        return {"status": "error", "error_message": f"Could not store papers: {e}"}


def search_literature(question: str, k: int = 5) -> dict:
    """Retrieve relevant scientific papers from the local literature store.

    Performs semantic similarity search over publications previously ingested
    from Europe PMC. Results are ranked by similarity between the question
    embedding and stored publication embeddings.

    Use this tool to retrieve literature supporting biomedical, pharmacological,
    or chemical research questions. Only cite publications returned by this tool.
    Never invent or modify bibliographic metadata, publication identifiers,
    or source URLs.

    Retrieved papers are candidates for supporting evidence, not verified
    sources for every scientific claim. Examine the available abstracts before
    drawing conclusions. Semantic similarity does not establish factual support.
    Do not claim to have read full-text articles when only abstracts are stored.

    If retrieval fails, the collection is empty, or the returned abstracts do
    not support the question, acknowledge the limitation rather than generating
    unsupported citations.

    Args:
        question: Natural-language research question, e.g.
            "What mechanisms drive resistance to KRAS G12C inhibitors?"
        k: Maximum number of papers to retrieve (1-10). Defaults to 5.

    Returns:
        dict: Search status and retrieved literature, including:
            - status: "success", "not_found", or "error".
            - question: Original research question.
            - count: Number of retrieved papers.
            - papers: List of publications with IDs, titles, authors, journals,
              publication years, PMIDs, DOIs, URLs, abstracts, and similarity scores.
            - error_message: Description of the issue when applicable.

    Notes:
        - Searches the local ChromaDB collection, not the live Europe PMC API.
        - Similarity scores reflect semantic relevance, not evidence quality.
        - Only previously ingested publications can be retrieved.
    """

    try:
        papers = search_papers(question, k)
        return papers
    except Exception as e:
        return {"status": "error", "error_message": f"Could not search papers: {e}"}
