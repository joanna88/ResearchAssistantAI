import httpx
import re
import html


def _clean_text(text):
    """Remove HTML tags and normalize whitespace in text.

    Args:
        text (str): Input text to clean.

    Returns:
        str: Text with HTML tags removed and consecutive whitespace
        collapsed into single spaces.
    """

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = " ".join(text.split())

    return text


def search_europepmc(query: str, limit: int = 10) -> dict:
    """Search Europe PMC for scientific publications matching a query.

    Queries the Europe PMC REST API and retrieves publication metadata using
    the `core` result type. Results are parsed into a simplified dictionary
    containing bibliographic information, abstracts, and publication URLs.

    Publications without an available abstract are excluded from the results
    and counted in `skipped_no_abstract`. The number of returned publications
    may therefore be smaller than the requested limit.

    Args:
        query: Literature search query. Supports Europe PMC search syntax,
            including keywords, Boolean operators, and field-specific searches.
        limit: Maximum number of records to retrieve from the API (1-25).
            Defaults to 10.

    Returns:
        dict: Dictionary containing:
            - status: "success", "not_found", or "error".
            - source: Data source ("Europe PMC") on successful retrieval.
            - query: Original search query.
            - count: Number of returned publications with abstracts.
            - skipped_no_abstract: Number of retrieved records excluded
                because their abstracts were missing.
            - papers: List of publication dictionaries containing IDs,
            source, PMID, PMCID, DOI, title, authors, journal, publication
            year, citation count, abstract, and URL.
            - error_message: Description of the failure when applicable.

    Notes:
        - Makes a synchronous HTTP GET request with a 30-second timeout.
        - Publication metadata is extracted directly from the API response.
        - Missing optional metadata fields are returned as None.
        - Results are not paginated beyond the requested page size.
        - HTTP, connection, and unexpected response errors are returned
            as structured dictionaries rather than raised as exceptions.
    """

    if not query.strip():
        return {
            "status": "error",
            "query": query,
            "error_message": "Query cannot be empty.",
        }

    if limit < 1 or limit > 25:
        return {
            "status": "error",
            "query": query,
            "error_message": "Limit must be between 1 and 25.",
        }

    url = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"

    try:
        response = httpx.get(
            url,
            params={
                "query": query,
                "format": "json",
                "resultType": "core",
                "pageSize": limit,
            },
            timeout=30,
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "query": query,
                "error_message": f"Europe PMC returned HTTP {response.status_code}.",
            }

        data = response.json()
        results = data["resultList"]["result"]

        if not results:
            return {
                "status": "not_found",
                "query": query,
                "error_message": "No publications found in Europe PMC.",
            }

        results_list = []
        skipped_no_abstract = 0

        for result in results:
            if not result.get("abstractText"):
                skipped_no_abstract += 1
                continue

            pub_id = result["id"]
            source = result.get("source")

            pmid = result.get("pmid")
            pmcid = result.get("pmcid")
            doi = result.get("doi")

            if pmid:
                link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            elif doi:
                link = f"https://doi.org/{doi}"
            else:
                link = None

            results_list.append(
                {
                    "pub_id": f"{source}:{pub_id}",
                    "source": source,
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "doi": doi,
                    "title": _clean_text(result.get("title") or ""),
                    "authors": result.get("authorString"),
                    "journal": (result.get("journalInfo") or {})
                    .get("journal", {})
                    .get("title"),
                    "year": result.get("pubYear"),
                    "cited_by": result.get("citedByCount"),
                    "link": link,
                    "abstract": _clean_text(result.get("abstractText")),
                }
            )

        return {
            "status": "success",
            "source": "Europe PMC",
            "query": query,
            "count": len(results_list),
            "skipped_no_abstract": skipped_no_abstract,
            "papers": results_list,
        }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "query": query,
            "error_message": f"Could not connect to Europe PMC: {e}",
        }

    except (KeyError, IndexError, TypeError, ValueError):
        return {
            "status": "error",
            "query": query,
            "error_message": "Unexpected response from Europe PMC.",
        }
