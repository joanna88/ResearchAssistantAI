from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors, Lipinski, QED


RDLogger.DisableLog("rdApp.*")

def calculate_lipinski_violations(mol_weight: float, logp: float, 
                                  h_donors: int, h_acceptors: int) -> dict:
    """Calculates Lipinski's Rule of Five violations."""

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
    """Assesses the druglikeness of an input list of SMILES strings."""

    if isinstance(smiles_list, str):
        smiles_list = [smiles_list]

    if len(smiles_list) == 0:
        return {
                "status": "error",
                "error_message": "Input list is empty."
                }
    elif len(smiles_list) > 50:
        return {
                "status": "error",
                "error_message": "Input list exceeds maximum length of 50."
                }

    out_list = []
    for smiles in smiles_list:
        if not smiles.strip():
            out_list.append({
                    "smiles": smiles,
                    "valid": False,
                    "error_message": f"Empty SMILES string: {smiles}"
                    })
            continue
            
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            out_list.append({
                    "smiles": smiles,
                    "valid": False,
                    "error_message": f"Invalid molecule from SMILES: {smiles}"
                    })
        else:
            mol_weight = Descriptors.MolWt(mol)
            clogp = Descriptors.MolLogP(mol)
            h_donors = Lipinski.NumHDonors(mol) # chemically precise definition of an H-bond donor
            h_acceptors = Lipinski.NumHAcceptors(mol) # chemically precise definition of an H-bond acceptor
            tpsa = Descriptors.TPSA(mol)
            rot_bonds = Lipinski.NumRotatableBonds(mol)
            qed_score = QED.qed(mol)
            violations = calculate_lipinski_violations(mol_weight, clogp, h_donors, h_acceptors)

            out_list.append({
                "smiles": smiles,
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
            