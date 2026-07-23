from unittest.mock import Mock

import pytest
import requests

from kibad_llm.normalization.gbif import (
    GBIF_SPECIES_BATCH_MATCH_URL,
    GBIF_SPECIES_MATCH_URL,
    normalize_spezies,
    normalize_spezies_batch,
)


def test_normalize_spezies_returns_gbif_canonical_name(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {"matchType": "EXACT", "canonicalName": "Abies alba"}
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert normalize_spezies("Abies alba Mill.") == "Abies alba"
    request_get.assert_called_once_with(
        GBIF_SPECIES_MATCH_URL,
        params={"scientificName": "Abies alba Mill."},
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


def test_normalize_spezies_supports_custom_request_and_response_fields(
    monkeypatch,
) -> None:
    response = Mock()
    response.json.return_value = {"matchType": "EXACT", "normalizedName": "Abies alba"}
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert (
        normalize_spezies(
            "Abies alba Mill.",
            query_param="name",
            response_field="normalizedName",
        )
        == "Abies alba"
    )
    request_get.assert_called_once_with(
        GBIF_SPECIES_MATCH_URL,
        params={"name": "Abies alba Mill."},
        timeout=10,
    )


def test_normalize_spezies_returns_none_below_minimum_confidence(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {
        "matchType": "EXACT",
        "canonicalName": "Abies alba",
        "confidence": 90,
    }
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert normalize_spezies("Abies alba Mill.", min_confidence=95) is None


def test_normalize_spezies_batch_returns_normalized_names_in_input_order(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = [
        {"matchType": "EXACT", "canonicalName": "Abies alba", "confidence": 100},
        {"matchType": "NONE", "confidence": 100},
        {"matchType": "HIGHERRANK", "canonicalName": "Abies", "confidence": 94},
    ]
    request_post = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.post", request_post)

    assert normalize_spezies_batch(
        ["Abies alba Mill.", "not-a-real-species-xyzzy", "Abies albaa"],
        min_confidence=95,
    ) == ["Abies alba", None, None]
    request_post.assert_called_once_with(
        GBIF_SPECIES_BATCH_MATCH_URL,
        json=[
            {"scientificName": "Abies alba Mill."},
            {"scientificName": "not-a-real-species-xyzzy"},
            {"scientificName": "Abies albaa"},
        ],
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


@pytest.mark.parametrize("min_confidence", [-0.1, 100.1])
def test_normalize_spezies_rejects_out_of_range_minimum_confidence(
    min_confidence: float,
) -> None:
    with pytest.raises(ValueError, match="min_confidence must be between 0 and 100"):
        normalize_spezies("Abies alba Mill.", min_confidence=min_confidence)


def test_normalize_spezies_returns_none_when_gbif_finds_no_match(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {"matchType": "NONE", "confidence": 100}
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert normalize_spezies("not-a-real-species-xyzzy") is None


def test_normalize_spezies_propagates_gbif_request_errors(monkeypatch) -> None:
    request_get = Mock(side_effect=requests.ConnectionError)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    with pytest.raises(requests.ConnectionError):
        normalize_spezies("Abies alba Mill.")


@pytest.mark.slow
def test_normalize_spezies_queries_gbif() -> None:
    # returned confidence for this request is 94
    assert normalize_spezies("Abies albaa", min_confidence=90) == "Abies"


@pytest.mark.slow
def test_normalize_spezies_returns_none_when_gbif_confidence_is_too_low() -> None:
    # returned confidence for this request is 94
    assert normalize_spezies("Abies albaa", min_confidence=95) is None
