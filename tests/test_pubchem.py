import httpx
import pytest
from mcp_server import pubchem


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    def fail(*args, **kwargs):
        raise AssertionError("Unexpected real HTTP request in a test")

    monkeypatch.setattr(pubchem.httpx, "get", fail)


def test_lookup_success(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(
            200,
            json={
                "PropertyTable": {
                    "Properties": [
                        {
                            "CID": 702,
                            "SMILES": "CCO",
                            "MolecularFormula": "C2H6O",
                            "MolecularWeight": "46.07",
                            "IUPACName": "ethanol",
                        }
                    ]
                }
            },
        )

    monkeypatch.setattr(pubchem.httpx, "get", fake_get)

    result = pubchem.lookup_compound_by_name("ethanol")

    assert result["status"] == "success"
    assert result["cid"] == 702
    assert result["molecular_weight"] == 46.07
    assert result["smiles"] == "CCO"
    assert result["molecular_formula"] == "C2H6O"
    assert str(result["cid"]) in result["compound_url"]


def test_lookup_not_found(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(404)

    monkeypatch.setattr(pubchem.httpx, "get", fake_get)

    result = pubchem.lookup_compound_by_name("sotorasib")

    assert result["status"] == "not_found"


def test_lookup_error_500(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(500)

    monkeypatch.setattr(pubchem.httpx, "get", fake_get)

    result = pubchem.lookup_compound_by_name("sotorasib")

    assert result["status"] == "error"
    assert "500" in result["error_message"]


def test_lookup_error_timeout(monkeypatch):

    def fake_get(url, **kwargs):
        raise httpx.ConnectTimeout("timed out")

    monkeypatch.setattr(pubchem.httpx, "get", fake_get)

    result = pubchem.lookup_compound_by_name("sotorasib")

    assert result["status"] == "error"
    assert "Could not connect" in result["error_message"]


def test_lookup_unexpected_response(monkeypatch):

    def fake_get(url, **kwargs):
        return httpx.Response(200, json={"unexpected": "shape"})

    monkeypatch.setattr(pubchem.httpx, "get", fake_get)

    result = pubchem.lookup_compound_by_name("ethanol")

    assert result["status"] == "error"


def test_lookup_empty_query(monkeypatch):

    def fake_get(url, **kwargs):
        raise AssertionError("httpx.get should not be called for an empty name")

    monkeypatch.setattr(pubchem.httpx, "get", fake_get)

    result = pubchem.lookup_compound_by_name(" ")

    assert result["status"] == "error"
