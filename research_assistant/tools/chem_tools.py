from rdkit import Chem, RDLogger, DataStructs
from rdkit.Chem import Descriptors, Lipinski, QED, rdFingerprintGenerator


RDLogger.DisableLog("rdApp.*")

# running fingerprint generator from the module level to create it only once
_MORGAN_GEN = rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)


def _check_smiles_length(smiles_list: list[str]) -> str | None:
    """Validate that the SMILES list contains between 1 and 50 entries.

    Args:
        smiles_list: List of SMILES strings to validate.

    Returns:
        Error message if the list size is invalid, otherwise None.
    """

    if len(smiles_list) == 0:
        return "Input list is empty."

    elif len(smiles_list) > 50:
        return "Input list exceeds maximum length of 50."

    return None


def _clean_smiles(smiles: str) -> str:
    """Remove surrounding whitespace and common punctuation delimiters from a SMILES string.
    
    Args:
        smiles: A SMILES string to clean.
        
    Returns:
        The cleaned SMILES string.
    """
    
    smiles = smiles.strip()

    delimiters = ('"', "'", ",", ";", "`")

    while smiles and smiles[0] in delimiters:
        smiles = smiles[1:].strip()

    while smiles and smiles[-1] in delimiters:
        smiles = smiles[:-1].strip()

    return smiles

def _parse_smiles(smiles: str) -> tuple[str, Chem.Mol | None, str | None]:
    """Parse a SMILES string and return the cleaned SMILES, RDKit Mol object, and any error message if invalid.
    
    Args:
        smiles: A SMILES string to parse.
    
    Returns:
        A tuple containing:
            - cleaned_smiles: The cleaned SMILES string.
            - mol: The RDKit Mol object if valid, otherwise None.
            - error: An error message if the SMILES is invalid, otherwise None."""
    
    cleaned_smiles = _clean_smiles(smiles)

    if not cleaned_smiles:
        return cleaned_smiles, None, f"Empty SMILES string: {cleaned_smiles}"

    elif ',' in cleaned_smiles:
        return cleaned_smiles, None, f"Invalid SMILES string (contains commas), which might indicate multiple SMILES entries parsed as one: {cleaned_smiles}. Try providing each SMILES as a separate entry in the list."

    elif any(ch.isspace() for ch in cleaned_smiles):
        return cleaned_smiles, None, f"Invalid SMILES string (contains whitespace), which might indicate multiple SMILES entries parsed as one: {cleaned_smiles}. Try providing each SMILES as a separate entry in the list."
            
    mol = Chem.MolFromSmiles(cleaned_smiles)

    if mol is None:
        return cleaned_smiles, None, f"Invalid molecule from SMILES: {cleaned_smiles}"

    return cleaned_smiles, mol, None


def _calculate_lipinski_violations(mol_weight: float, logp: float, 
                                  h_donors: int, h_acceptors: int) -> dict:
    """
    Helper function to calculate Lipinski's Rule of Five violations.
    
    Args:
        mol_weight: Molecular weight in Daltons.
        logp: LogP value (octanol-water partition coefficient).
        h_donors: Number of hydrogen bond donors.
        h_acceptors: Number of hydrogen bond acceptors.
        
    Returns:
        A dictionary containing the number of Lipinski violations and a dictionary of
        the specific rules that were violated."""

    violated_rules = {}

    if mol_weight > 500:
        violated_rules["molecular_weight"] = "MW > 500 Da"

    if logp > 5.0:
        violated_rules["logp"] = "LogP > 5"

    if h_donors > 5:
        violated_rules["h_donors"] = "HBD > 5"

    if h_acceptors > 10:
        violated_rules["h_acceptors"] = "HBA > 10"

    return {
        "lipinski_violations": len(violated_rules),
        "violated_rules": violated_rules
    }


def assess_druglikeness(smiles_list: list[str]) -> dict:
    """ 
    Calculate molecular properties and drug-likeness metrics from SMILES.
    
    Use this tool only when valid SMILES strings are provided or available from 
    a reliable source. Do not invent, infer, or guess SMILES. Only SMILES input 
    is accepted.

    Use this tool to calculate molecular weight (Da), LogP, chemically defined
    RDKit H-bond donor/acceptor counts, TPSA (Å²), rotatable bonds, QED (0-1, higher = 'more drug-like'),
    and Lipinski Rule of Five violations. Does not predict biological activity,
    toxicity, or clinical efficacy.

    Args:
        smiles_list: List of 1-50 SMILES strings. Process all available SMILES
        together in a single call.

    Returns:
        Results for each SMILES in the same order as the input list, with an overall
        status ("success" or "error"), calculated properties, validity, Lipinski
        violation count, and violated rules. Invalid SMILES are reported individually. """

    if isinstance(smiles_list, str):
        smiles_list = [smiles_list]

    length_error = _check_smiles_length(smiles_list)
    if length_error:
        return {
            "status": "error",
            "error_message": length_error
        }

    out_list = []
    for smiles in smiles_list:

        cleaned_smiles, mol, error = _parse_smiles(smiles)
        if error:
            out_list.append({
                "smiles": cleaned_smiles,
                "valid": False,
                "error_message": error
            })
            continue
        
        mol_weight = Descriptors.MolWt(mol)
        clogp = Descriptors.MolLogP(mol)
        h_donors = Lipinski.NumHDonors(mol) # chemically precise definition of an H-bond donor
        h_acceptors = Lipinski.NumHAcceptors(mol) # chemically precise definition of an H-bond acceptor
        tpsa = Descriptors.TPSA(mol)
        rot_bonds = Lipinski.NumRotatableBonds(mol)
        qed_score = QED.qed(mol)
        violations = _calculate_lipinski_violations(mol_weight, clogp, h_donors, h_acceptors)

        out_list.append({
                "smiles": cleaned_smiles,
                "valid": True,
                "molecular_weight": round(mol_weight, 2),
                "logp": round(clogp, 2),
                "h_donors": h_donors,
                "h_acceptors": h_acceptors,
                "tpsa": round(tpsa, 2),
                "rotatable_bonds": rot_bonds,
                "qed_score": round(qed_score, 2),
                **violations
            })

    return {
        "status": "success",
        "all_results": out_list
    }


def tanimoto_similarity(query_smiles: str, smiles_list: list[str]) -> dict:
    """Calculate fingerprint similarity between a query SMILES and 1-50 SMILES.

    Use this tool to compare molecular structures using Tanimoto similarity with
    Morgan fingerprints (radius 2, 2048 bits). Scores range from 0 to 1; higher
    values indicate greater fingerprint similarity. Keep in mind that there is no universal 
    threshold; structurally similar compounds can still differ greatly in activity.

    Do not use this tool to predict biological activity, efficacy, or other
    molecular properties. Do not invent, infer, or modify SMILES.

    Args:
        query_smiles: Query molecule as a SMILES string. 
        smiles_list: List of 1-50 SMILES strings to compare with the query. Process all available SMILES
        together in a single call.

    Returns:
        Valid results sorted by similarity from highest to lowest. "input_index"
        is the zero-based position (0, 1, 2, ...) of each SMILES in the original
        input list, not its similarity rank. Invalid SMILES are reported
        separately. An invalid query or input list returns an error.
    """

    cleaned_query, query_mol, error = _parse_smiles(query_smiles)
    if error:
        return {
            "status": "error",
            "error_message": f"Invalid query SMILES. {error}"
        }

    if isinstance(smiles_list, str):
        smiles_list = [smiles_list]

    length_error = _check_smiles_length(smiles_list)
    if length_error:
        return {
            "status": "error",
            "error_message": length_error
        }

    fp1 = _MORGAN_GEN.GetFingerprint(query_mol)

    out_list = []
    invalid = []
    for idx, smi in enumerate(smiles_list):

        cleaned_smi, mol, error = _parse_smiles(smi)

        if error:
            invalid.append({
                "input_index": idx,
                "smiles": cleaned_smi,
                "error_message": error
            })
            continue

        fp2 = _MORGAN_GEN.GetFingerprint(mol)
        similarity = DataStructs.TanimotoSimilarity(fp1, fp2)

        out_list.append({
            "input_index": idx,
            "smiles": cleaned_smi,
            "similarity": round(similarity, 2)
        })

    return {
        "status": "success",
        "query_smiles": cleaned_query,
        "fingerprint": "Morgan radius 2, 2048 bits",
        "results": sorted(out_list, key=lambda r: r["similarity"], reverse=True),
        "invalid": invalid
    }

  