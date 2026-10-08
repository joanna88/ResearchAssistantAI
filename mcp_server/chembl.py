import httpx
import re


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


def get_target_activities(target_chembl_id: str, limit: int = 10) -> dict:
    """Retrieve compounds with reported activities for a ChEMBL target.

    Use this tool after identifying a target with `search_targets`. Use only
    `target_chembl_id` values returned by `search_targets`; never invent, infer,
    modify, or guess a ChEMBL target ID.

    Results are ranked by the best reported pChEMBL value for each unique molecule.
    Multiple activity measurements may exist for the same molecule; the best single
    pChEMBL measurement is returned together with the number of measurements found
    in the retrieved activity records.

    Activity values may come from different assays and experimental conditions and
    are not necessarily directly comparable. Before making potency comparisons,
    consider the activity type, value, units, assay ID, and assay context. Pay
    particular attention to `mutation`: measurements against mutated or variant
    targets may not be comparable to measurements against the wild-type target.
    A higher pChEMBL value alone should not be treated as evidence that one compound
    is definitively more potent, selective, effective, or clinically useful than
    another.

    The returned `smiles` values come directly from ChEMBL and may be used as
    reliable SMILES inputs for `assess_druglikeness` and `tanimoto_similarity`.
    Use them exactly as returned; do not modify or reconstruct them.

    Args:
        target_chembl_id: ChEMBL target ID returned by `search_targets`,
                e.g. "CHEMBL203".
        limit: Maximum number of unique compounds to return (1-25).
            Defaults to 10.

    Returns:
        Search status and unique compounds associated with the target. Successful
        results contain compounds ranked by their best single pChEMBL value, with
        SMILES, activity type and value, units, assay ID, mutation information,
        publication year, and the number of measurements found in the retrieved
        activity records.
    """

    target_chembl_id = target_chembl_id.strip().upper()

    if not target_chembl_id:
        return {
            "status": "error",
            "query": target_chembl_id,
            "error_message": "target_chembl_id cannot be empty.",
        }

    if limit < 1 or limit > 25:
        return {
            "status": "error",
            "query": target_chembl_id,
            "error_message": "Limit must be between 1 and 25.",
        }

    if not re.fullmatch(r"CHEMBL\d+", target_chembl_id):
        return {
            "status": "error",
            "query": target_chembl_id,
            "error_message": "Invalid ChEMBL target ID format.",
        }

    url = "https://www.ebi.ac.uk/chembl/api/data/activity.json"

    params = {
        "target_chembl_id": target_chembl_id,
        "limit": limit * 10,
        "pchembl_value__isnull": "false",
        "order_by": "-pchembl_value",
        "only": (
            "molecule_chembl_id,"
            "molecule_pref_name,"
            "canonical_smiles,"
            "standard_type,"
            "standard_value,"
            "standard_units,"
            "pchembl_value,"
            "assay_chembl_id,"
            "assay_variant_mutation,"
            "document_year"
        ),
    }

    try:
        response = httpx.get(
            url,
            params=params,
            timeout=30,
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "query": target_chembl_id,
                "error_message": f"ChEMBL returned HTTP {response.status_code}.",
            }

        data = response.json()
        activities = data["activities"]

        if not activities:
            return {
                "status": "not_found",
                "query": target_chembl_id,
                "error_message": (
                    "No activities with pChEMBL values were found for this "
                    "ChEMBL target ID."
                ),
            }

        molecules = {}

        for activity in activities:
            molecule_chembl_id = activity.get("molecule_chembl_id")

            if not molecule_chembl_id:
                continue

            # Because the API results are ordered by descending pChEMBL,
            # the first measurement encountered is the best one.
            if molecule_chembl_id not in molecules:
                molecules[molecule_chembl_id] = {
                    "molecule_chembl_id": molecule_chembl_id,
                    "name": activity.get("molecule_pref_name"),
                    "smiles": activity.get("canonical_smiles"),
                    "pchembl": float(activity["pchembl_value"]),
                    "activity_type": activity.get("standard_type"),
                    "value": activity.get("standard_value"),
                    "units": activity.get("standard_units"),
                    "assay_chembl_id": activity.get("assay_chembl_id"),
                    "mutation": activity.get("assay_variant_mutation"),
                    "year": activity.get("document_year"),
                    "n_top_measurements": 1,
                    "link": (
                        "https://www.ebi.ac.uk/chembl/explore/compound/"
                        f"{molecule_chembl_id}"
                    ),
                }
            else:
                molecules[molecule_chembl_id]["n_top_measurements"] += 1

        results = list(molecules.values())[:limit]

        return {
            "status": "success",
            "source": "ChEMBL",
            "query": target_chembl_id,
            "count": len(results),
            "ranking": "best single pChEMBL per molecule",
            "compounds": results,
        }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "query": target_chembl_id,
            "error_message": f"Could not connect to ChEMBL: {e}",
        }

    except (KeyError, IndexError, TypeError, ValueError):
        return {
            "status": "error",
            "query": target_chembl_id,
            "error_message": "Unexpected response from ChEMBL.",
        }
