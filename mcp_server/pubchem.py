import httpx
import urllib.parse


def lookup_compound_by_name(name: str) -> dict:
    """Look up a compound by name in PubChem.

    Use this tool to retrieve a trusted SMILES and basic compound information
    when the user provides a compound or drug name instead of a SMILES.
    Do not invent or infer a SMILES when this lookup can be used.

    A single compound name can be processed per tool call.

    Args:
        name: Compound or drug name to search in PubChem. 

    Returns:
        PubChem result containing CID, IUPAC name, SMILES, molecular formula,
        molecular weight (Da), and PubChem URL. Status is "success", "not_found",
        or "error". A failed lookup includes an error message.
    """

    if not name.strip():
        return {
            "status": "error",
            "query": name,
            "error_message": "Compound name cannot be empty.",
        }

    clean_name = urllib.parse.quote(name.strip(), safe="")
    pubchem_url = f'https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/{clean_name}/property/SMILES,MolecularFormula,MolecularWeight,IUPACName/JSON'

    try:
        response = httpx.get(pubchem_url, timeout=10)

        if response.status_code == 404:
            return {
                "status": "not_found",
                "query": name,
                "error_message": "Compound not found in PubChem. Check the spelling of the provided name.",
            }

        if response.status_code != 200:
            return {
                "status": "error",
                "query": name,
                "error_message": f"PubChem returned HTTP {response.status_code}.",
            }

        data = response.json()
        # retrieving only the first match from the pubchem database 
        compound = data["PropertyTable"]["Properties"][0]
        cid = compound.get("CID")

        return {
            "status": "success",
            "query": name,
            "source": "PubChem",
            "cid": cid,
            "iupac_name": compound.get("IUPACName"),
            "smiles": compound.get("SMILES"),
            "molecular_formula": compound.get("MolecularFormula"),
            "molecular_weight": float(compound.get("MolecularWeight")),
            "compound_url": f"https://pubchem.ncbi.nlm.nih.gov/compound/{cid}",
        }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "query": name,
            "error_message": f"Could not connect to PubChem: {e}",
        }

    except (KeyError, IndexError, TypeError, ValueError):
        return {
            "status": "error",
            "query": name,
            "error_message": "Unexpected response from PubChem.",
        }