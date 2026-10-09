import httpx
import pytest
from mcp_server import chembl


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Unexpected real HTTP request in a test")

    monkeypatch.setattr(chembl.httpx, "get", fail)


# testing search_target
def test_search_targets_success(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "targets": [
                    {
                        "target_chembl_id": "CHEMBL203",
                        "pref_name": "Epidermal growth factor receptor",
                        "target_type": "SINGLE PROTEIN",
                        "organism": "Homo sapiens",
                    }
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("EGFR")

    assert result["status"] == "success"
    assert result["source"] == "ChEMBL"
    assert result["count"] == 1
    assert result["targets"][0]["target_chembl_id"] == "CHEMBL203"
    assert result["targets"][0]["pref_name"] == "Epidermal growth factor receptor"
    assert result["targets"][0]["organism"] == "Homo sapiens"
    assert result["targets"][0]["link"].endswith("/CHEMBL203")


def test_search_targets_not_found(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"targets": []})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("nonexistent_target")

    assert result["status"] == "not_found"
    assert result["query"] == "nonexistent_target"


@pytest.mark.parametrize("query", ["", " ", "   "])
def test_search_targets_empty_query(query):

    result = chembl.search_targets(query)

    assert result["status"] == "error"
    assert result["error_message"] == "Query cannot be empty."


@pytest.mark.parametrize("limit", [0, -1, 26, 100])
def test_search_targets_invalid_limit(limit):

    result = chembl.search_targets("EGFR", limit=limit)

    assert result["status"] == "error"
    assert result["error_message"] == "Limit must be between 1 and 25."


def test_search_targets_http_error(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(503)

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("EGFR")

    assert result["status"] == "error"
    assert result["error_message"] == "ChEMBL returned HTTP 503."


def test_search_targets_connection_error(monkeypatch):

    def fake_get(url, **kwargs):
        raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("EGFR")

    assert result["status"] == "error"
    assert "Could not connect to ChEMBL" in result["error_message"]


def test_search_targets_unexpected_response(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"unexpected": "shape"})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("EGFR")

    assert result["status"] == "error"
    assert result["error_message"] == "Unexpected response from ChEMBL."


def test_search_targets_missing_target_id(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "targets": [
                    {
                        "pref_name": "Epidermal growth factor receptor",
                        "organism": "Homo sapiens",
                    }
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("EGFR")

    assert result["status"] == "error"
    assert result["error_message"] == "Unexpected response from ChEMBL."


def test_search_targets_request_parameters(monkeypatch):

    def fake_get(url, **kwargs):
        assert url == "https://www.ebi.ac.uk/chembl/api/data/target/search.json"
        assert kwargs["params"] == {"q": "KRAS", "limit": 5}
        assert kwargs["timeout"] == 30

        return httpx.Response(200, json={"targets": []})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.search_targets("KRAS", limit=5)

    assert result["status"] == "not_found"


# testing get_target_activities


# Helper function
def make_activity(mol_id, pchembl, mutation=None, smiles="CCO"):
    return {
        "molecule_chembl_id": mol_id,
        "molecule_pref_name": None,
        "canonical_smiles": smiles,
        "pchembl_value": str(pchembl),
        "standard_type": "IC50",
        "standard_value": "1.0",
        "standard_units": "nM",
        "assay_chembl_id": "CHEMBL1",
        "assay_variant_mutation": mutation,
        "document_year": 2020,
    }


def test_activities_success(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.0, "G12C", "CCO"),
                    make_activity("CHEMBL200", 8.0, None, "CCN"),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203", mutation="G12C")

    assert result["status"] == "success"
    assert result["source"] == "ChEMBL"
    assert result["query"] == "CHEMBL203"
    assert result["count"] == 2
    assert result["requested_mutation"] == "G12C"
    assert result["mutation_summary"] == (
        "1 of 2 results annotated with G12C (results are not filtered by mutation)"
    )

    first = result["compounds"][0]
    second = result["compounds"][1]

    assert first["molecule_chembl_id"] == "CHEMBL100"
    assert first["smiles"] == "CCO"
    assert first["pchembl"] == 9.0
    assert first["activity_type"] == "IC50"
    assert first["assay_chembl_id"] == "CHEMBL1"
    assert first["matches_mutation"] is True
    assert first["link"].endswith("/CHEMBL100")

    assert second["molecule_chembl_id"] == "CHEMBL200"
    assert second["matches_mutation"] is False


def test_activities_deduplication_and_ranking(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.5),
                    make_activity("CHEMBL200", 9.0),
                    make_activity("CHEMBL100", 8.0),
                    make_activity("CHEMBL300", 7.5),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "success"
    assert result["count"] == 3

    compounds = result["compounds"]

    assert [c["molecule_chembl_id"] for c in compounds] == [
        "CHEMBL100",
        "CHEMBL200",
        "CHEMBL300",
    ]
    assert compounds[0]["pchembl"] == 9.5
    assert compounds[0]["n_top_measurements"] == 2
    assert compounds[1]["n_top_measurements"] == 1


def test_activities_limit_applied_to_unique_compounds(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.0),
                    make_activity("CHEMBL100", 8.5),
                    make_activity("CHEMBL200", 8.0),
                    make_activity("CHEMBL300", 7.0),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203", limit=2)

    assert result["status"] == "success"
    assert result["count"] == 2
    assert len(result["compounds"]) == 2
    assert result["compounds"][0]["molecule_chembl_id"] == "CHEMBL100"
    assert result["compounds"][1]["molecule_chembl_id"] == "CHEMBL200"


def test_activities_mutation_case_insensitive(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.0, "p.G12C"),
                    make_activity("CHEMBL200", 8.0, "g12d"),
                    make_activity("CHEMBL300", 7.0, None),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203", mutation=" g12c ")

    assert result["status"] == "success"
    assert result["requested_mutation"] == "G12C"

    assert [c["matches_mutation"] for c in result["compounds"]] == [
        True,
        False,
        False,
    ]
    assert result["mutation_summary"].startswith("1 of 3")


def test_activities_mutation_does_not_filter_or_reorder(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.0, None),
                    make_activity("CHEMBL200", 8.0, "G12C"),
                    make_activity("CHEMBL300", 7.0, "G12D"),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203", mutation="G12C")

    assert result["status"] == "success"
    assert result["count"] == 3
    assert [c["molecule_chembl_id"] for c in result["compounds"]] == [
        "CHEMBL100",
        "CHEMBL200",
        "CHEMBL300",
    ]
    assert [c["matches_mutation"] for c in result["compounds"]] == [
        False,
        True,
        False,
    ]


def test_activities_mutation_matches_selected_measurement_only(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.0, None),
                    make_activity("CHEMBL100", 8.0, "G12C"),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203", mutation="G12C")

    assert result["status"] == "success"
    assert result["count"] == 1

    compound = result["compounds"][0]

    assert compound["pchembl"] == 9.0
    assert compound["mutation"] is None
    assert compound["matches_mutation"] is False
    assert compound["n_top_measurements"] == 2
    assert result["mutation_summary"].startswith("0 of 1")


def test_activities_without_mutation(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "activities": [
                    make_activity("CHEMBL100", 9.0, "G12C"),
                ]
            },
        )

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "success"
    assert result["requested_mutation"] is None
    assert result["mutation_summary"] is None
    assert result["compounds"][0]["matches_mutation"] is None


def test_activities_request_params(monkeypatch):
    captured = {}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["params"] = kwargs.get("params")
        captured["timeout"] = kwargs.get("timeout")
        return httpx.Response(200, json={"activities": []})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    chembl.get_target_activities("chembl203", limit=5, mutation="T790M")

    params = captured["params"]

    assert captured["url"] == ("https://www.ebi.ac.uk/chembl/api/data/activity.json")
    assert captured["timeout"] == 30
    assert params["target_chembl_id"] == "CHEMBL203"
    assert params["order_by"] == "-pchembl_value"
    assert params["limit"] == 50
    assert params["pchembl_value__isnull"] == "false"
    assert "assay_variant_mutation" in params["only"]

    assert "assay_variant_mutation" not in params
    assert "T790M" not in str(params).upper()


def test_activities_not_found(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"activities": []})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "not_found"
    assert result["query"] == "CHEMBL203"


@pytest.mark.parametrize("target_id", ["", " ", "   "])
def test_activities_empty_target_id(target_id):

    result = chembl.get_target_activities(target_id)

    assert result["status"] == "error"
    assert result["error_message"] == "target_chembl_id cannot be empty."


@pytest.mark.parametrize(
    "target_id",
    ["INVALID", "CHEMBL", "CHEMBLABC", "12345", "CHEMBL123X"],
)
def test_activities_invalid_target_id(target_id):

    result = chembl.get_target_activities(target_id)

    assert result["status"] == "error"
    assert result["error_message"] == "Invalid ChEMBL target ID format."


@pytest.mark.parametrize("limit", [0, -1, 26, 100])
def test_activities_invalid_limit(limit):

    result = chembl.get_target_activities("CHEMBL203", limit=limit)

    assert result["status"] == "error"
    assert result["error_message"] == "Limit must be between 1 and 25."


def test_activities_http_error(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(503)

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "error"
    assert result["error_message"] == "ChEMBL returned HTTP 503."


def test_activities_connection_error(monkeypatch):

    def fake_get(url, **kwargs):
        raise httpx.ConnectError("Connection failed")

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "error"
    assert "Could not connect to ChEMBL" in result["error_message"]


def test_activities_unexpected_response(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"unexpected": "shape"})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "error"
    assert result["error_message"] == "Unexpected response from ChEMBL."


def test_activities_invalid_pchembl(monkeypatch):

    def fake_get(url, **kwargs):
        activity = make_activity("CHEMBL100", 9.0)
        activity["pchembl_value"] = "invalid"

        return httpx.Response(200, json={"activities": [activity]})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "error"
    assert result["error_message"] == "Unexpected response from ChEMBL."


def test_activities_missing_molecule_id(monkeypatch):

    def fake_get(url, **kwargs):
        activity = make_activity("CHEMBL100", 9.0)
        activity.pop("molecule_chembl_id")

        return httpx.Response(200, json={"activities": [activity]})

    monkeypatch.setattr(chembl.httpx, "get", fake_get)

    result = chembl.get_target_activities("CHEMBL203")

    assert result["status"] == "success"
    assert result["count"] == 0
    assert result["compounds"] == []
