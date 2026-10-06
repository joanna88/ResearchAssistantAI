import pytest
from research_assistant.tools.chem_tools import assess_druglikeness, tanimoto_similarity


# tests for assess_druglikeness
def test_aspirin_properties():

    aspirin = "CC(=O)Oc1ccccc1C(=O)O"
    result = assess_druglikeness([aspirin])
    mol = result["all_results"][0]

    assert result["status"] == "success"
    assert mol["valid"] is True
    assert mol["molecular_weight"] == pytest.approx(180.16, abs=0.01)
    assert mol["logp"] == pytest.approx(1.31, abs=0.01)
    assert mol["tpsa"] == pytest.approx(63.6, abs=0.1)
    assert mol["rotatable_bonds"] == 2
    assert mol["qed_score"] == pytest.approx(0.55, abs=0.01)
    assert mol["lipinski_violations"] == 0
    assert mol["violated_rules"] == {}
    assert mol["h_donors"] == 1
    assert mol["h_acceptors"] == 3


def test_invalid_smiles():

    invalid_smiles = 'xyz'
    result = assess_druglikeness([invalid_smiles])
    mol = result["all_results"][0]

    assert result["status"] == "success"
    assert mol["valid"] is False
    assert "error_message" in mol


def test_order_of_results():

    smiles_list = ["CCO", "CC(=O)O", "C1CCCCC1", "xyz", ""]
    result = assess_druglikeness(smiles_list)
    

    assert result["status"] == "success"
    assert len(result["all_results"]) == 5
    assert [m["smiles"] for m in result["all_results"]] == smiles_list


def test_single_smiles_string():

    single_smiles = "CCO"
    result = assess_druglikeness(single_smiles)
    mol = result["all_results"][0]

    assert result["status"] == "success"
    assert mol["valid"] is True
    assert mol["smiles"] == single_smiles


@pytest.mark.parametrize("smiles", ["", " ", "   "])
def test_empty_smiles_is_invalid(smiles):

    result = assess_druglikeness([smiles])
    mol = result["all_results"][0]

    assert mol["valid"] is False
    assert "error_message" in mol
    assert len(result["all_results"]) == 1


def test_exceeding_max_length():

    long_list = ["CCO"] * 51
    result = assess_druglikeness(long_list)

    assert result["status"] == "error"
    assert "error_message" in result


def test_max_length_boundary():

    max_length_list = ["CCO"] * 50
    result = assess_druglikeness(max_length_list)

    assert result["status"] == "success"
    assert len(result["all_results"]) == 50


def test_lipinski_violations():

    smiles_list = ["C" * 41 + "C(=O)O"]
    result = assess_druglikeness(smiles_list)
    mol = result["all_results"][0]

    assert mol["valid"] is True
    assert mol["lipinski_violations"] == 2
    assert set(mol["violated_rules"]) == {"molecular_weight", "logp"}


@pytest.mark.parametrize("smiles", ['"CCO"', "'CCO'", " CCO ", "CCO,", "`CCO`"])
def test_delimiters_are_stripped(smiles):

    result = assess_druglikeness([smiles])
    mol = result["all_results"][0]

    assert mol["valid"] is True
    assert mol["smiles"] == "CCO"


@pytest.mark.parametrize("smiles", ["CCO c1ccccc1", "CCO,c1ccccc1", "CCO\tCC"])
def test_multiple_smiles_in_one_entry_rejected(smiles):
    
    result = assess_druglikeness([smiles])
    mol = result["all_results"][0]

    assert len(result["all_results"]) == 1
    assert mol["valid"] is False
    assert "error_message" in mol


# tests for tanimoto_similarity
def test_basic_correctness_tanimoto_similarity():

    mol1 = "CC(=O)Oc1ccccc1C(=O)O"
    mol2 = "CC(=O)Oc1ccccc1C(=O)O"

    result = tanimoto_similarity(mol1, [mol2])
    sim = result["results"][0]["similarity"]

    assert sim == 1.0
    assert len(result["results"]) == 1


def is_descending(values: list) -> bool:
    return all(values[i] >= values[i + 1] for i in range(len(values) - 1))


def test_sorting_tanimoto_similarity():

    mol1 = "CC(=O)Oc1ccccc1C(=O)O"
    smiles_list = ["CCO", "O=C(O)c1ccccc1O", "CC(=O)Oc1ccccc1C(=O)O"]

    results = tanimoto_similarity(mol1, smiles_list=smiles_list)
    result1 = results["results"][0]
    result2 = results["results"][1]
    result3 = results["results"][2]

    assert result1["input_index"] == 2
    assert result2["input_index"] == 1
    assert result3["input_index"] == 0

    assert is_descending([result1["similarity"], result2["similarity"], result3["similarity"]])


def test_invalid_entry_tanimoto_similarity():

    mol1 = "CC(=O)Oc1ccccc1C(=O)O"
    smiles_list = ["CCO", "O=C(O)c1ccccc1O", "xyz", "CC(=O)Oc1ccccc1C(=O)O"]

    results = tanimoto_similarity(mol1, smiles_list=smiles_list)

    assert len(results["results"]) == 3
    assert len(results["invalid"]) == 1

    assert results["invalid"][0]["smiles"] == "xyz"
    assert results["invalid"][0]["input_index"] == 2


def test_invalid_query_tanimoto_similarity():

    mol1 = "xyz"
    smiles_list = ["CCO"]

    results = tanimoto_similarity(mol1, smiles_list=smiles_list)

    assert results["status"] == "error"


def test_empty_list_tanimoto():

    mol1 = "CCO"
    mol2 = []

    results = tanimoto_similarity(mol1, mol2)

    assert results["status"] == "error"


def test_aspirin_salicylic_acid():

    mol1 = "CC(=O)Oc1ccccc1C(=O)O"
    mol2 = ["O=C(O)c1ccccc1O"]
    
    results = tanimoto_similarity(mol1, mol2)

    assert results["results"][0]["similarity"] == pytest.approx(0.45, abs=0.01)


def test_single_string_tanimoto():

    mol1 = "CC(=O)Oc1ccccc1C(=O)O"
    mol2 = "O=C(O)c1ccccc1O"
    
    results = tanimoto_similarity(mol1, mol2)

    assert results["status"] == "success"
    assert len(results["results"]) == 1