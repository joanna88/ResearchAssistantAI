import chromadb

from pathlib import Path
from google import genai
from google.genai import types


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_PATH = PROJECT_ROOT / "data" / "chroma_db"

EMBED_MODEL = "gemini-embedding-001"  # gemini-embedding-2
EMBED_DIM = 768


def _embed(texts: list[str], task_type: str) -> list[list[float]]:
    """Generate vector embeddings for a list of texts using the Gemini API.

    Args:
        texts: List of input texts to embed.
        task_type: Embedding task type, such as RETRIEVAL_DOCUMENT or RETRIEVAL_QUERY.

    Returns:
        list[list[float]]: Embedding vectors with dimensionality EMBED_DIM,
        in the same order as the input texts.
    """

    client = genai.Client()
    response = client.models.embed_content(
        model=EMBED_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type, output_dimensionality=EMBED_DIM
        ),
    )

    return [embedding.values for embedding in response.embeddings]


def _get_collection():
    """Get or create a persistent ChromaDB collection for storing papers.

    Uses cosine similarity and stores the embedding model and dimensionality
    in the collection metadata.

    Returns:
        chromadb.Collection: Persistent "papers" collection.
    """

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        "papers",
        metadata={
            "hnsw:space": "cosine",
            "embed_model": EMBED_MODEL,
            "embed_dim": EMBED_DIM,
        },
    )

    return collection


def add_papers(papers: list[dict]) -> dict:
    """Add new scientific papers to the persistent ChromaDB collection.

    Checks for existing publication IDs to avoid duplicates. New papers are
    embedded using their title and abstract, then stored with bibliographic
    metadata for subsequent semantic retrieval.

    Args:
        papers: List of publication dictionaries containing `pub_id`, `title`,
            `abstract`, and bibliographic metadata.

    Returns:
        dict: Operation status and storage statistics:
            - status: "success" or "error".
            - added: Number of newly stored papers.
            - already_stored: Number of existing publication IDs.
            - total_in_store: Total number of papers in the collection.
            - error_message: Description of the error for empty input.

    Notes:
        - Existing papers are skipped rather than updated.
        - Embeddings are generated using the RETRIEVAL_DOCUMENT task type.
        - Papers are identified by their `pub_id`.
    """

    if len(papers) == 0:
        return {"status": "error", "error_message": "No papers to add."}

    collection = _get_collection()

    ids = [p["pub_id"] for p in papers]
    existing = set(collection.get(ids=ids)["ids"])

    new_papers = [p for p in papers if p["pub_id"] not in existing]

    if len(new_papers) == 0:
        return {
            "status": "success",
            "added": 0,
            "already_stored": len(existing),
            "total_in_store": collection.count(),
        }

    texts = [f"{p['title']}\n\n{p['abstract']}" for p in new_papers]
    vectors = _embed(texts, "RETRIEVAL_DOCUMENT")
    new_ids = [p["pub_id"] for p in new_papers]
    abstracts = [p["abstract"] for p in new_papers]
    metadatas = [
        {
            "title": p["title"],
            "authors": p["authors"],
            "journal": p["journal"],
            "year": p["year"],
            "pmid": p["pmid"],
            "doi": p["doi"],
            "link": p["link"],
        }
        for p in new_papers
    ]

    collection.upsert(
        ids=new_ids, embeddings=vectors, documents=abstracts, metadatas=metadatas
    )

    return {
        "status": "success",
        "added": len(new_papers),
        "already_stored": len(existing),
        "total_in_store": collection.count(),
    }
