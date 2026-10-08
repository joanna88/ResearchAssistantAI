import httpx


def search_targets(query: str, limit: int = 10) -> dict:
    """Search for biological targets in ChEMBL matching a query.

    Use this tool to find ChEMBL targets from a target name, gene symbol, protein
    name, or other target-related search term. Search results are candidates and
    may include multiple targets. The first result is not necessarily the correct
    or intended target; consider the preferred name, target type, and organism
    when selecting a target.

    Never invent, infer, modify, or guess a ChEMBL target ID. Use only target IDs
    returned by this tool or otherwise obtained from an explicitly trusted source.

    Args:
        query: Target search term, such as a gene symbol, protein name, or target name.
        limit: Maximum number of matching targets to return (1-25). Defaults to 10.

    Returns:
        Search status and matching ChEMBL targets. Each result includes the ChEMBL
        target ID, preferred name, target type, organism, and ChEMBL URL. Multiple
        candidate targets may be returned for a query.
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

    url = "https://www.ebi.ac.uk/chembl/api/data/target/search.json"

    try:
        response = httpx.get(url, params={"q": query, "limit": limit}, timeout=30)

        if response.status_code != 200:
            return {
                "status": "error",
                "query": query,
                "error_message": f"ChEMBL returned HTTP {response.status_code}.",
            }

        data = response.json()
        targets = data["targets"]

        if len(targets) == 0:
            return {
                "status": "not_found",
                "query": query,
                "error_message": "Query not found in ChEMBL. "
                "Check the spelling of the provided name.",
            }

        results = []

        for target in targets:
            target_chembl_id = target["target_chembl_id"]

            results.append(
                {
                    "target_chembl_id": target_chembl_id,
                    "pref_name": target.get("pref_name"),
                    "target_type": target.get("target_type"),
                    "organism": target.get("organism"),
                    "link": (
                        "https://www.ebi.ac.uk/chembl/explore/target/"
                        f"{target_chembl_id}"
                    ),
                }
            )

        return {
            "status": "success",
            "source": "ChEMBL",
            "query": query,
            "count": len(results),
            "targets": results,
        }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "query": query,
            "error_message": f"Could not connect to ChEMBL: {e}",
        }

    except (KeyError, IndexError, TypeError, ValueError):
        return {
            "status": "error",
            "query": query,
            "error_message": "Unexpected response from ChEMBL.",
        }
