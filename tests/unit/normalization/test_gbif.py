from unittest.mock import Mock

import pytest
import requests

from kibad_llm.normalization.gbif import (
    GBIF_SPECIES_BATCH_MATCH_URL,
    GBIF_SPECIES_MATCH_URL,
    NestedDict,
    _filter_nested_dict,
    normalize_spezies,
    normalize_spezies_batch,
)


def test_normalize_spezies_requests_and_filters_default_canonical_name(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {
        "usage": {"matchType": "EXACT", "canonicalName": "Abies alba"},
        "diagnostics": {"matchType": "EXACT"},
    }
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert normalize_spezies("Abies alba Mill.") == {
        "classification": {},
        "diagnostics": {"matchType": "EXACT"},
        "usage": {"canonicalName": "Abies alba", "matchType": "EXACT"},
    }
    request_get.assert_called_once_with(
        GBIF_SPECIES_MATCH_URL,
        params={"scientificName": "Abies alba Mill."},
        timeout=10,
    )
    response.raise_for_status.assert_called_once_with()


def test_normalize_spezies_supports_custom_query_parameter_and_response_fields(
    monkeypatch,
) -> None:
    response = Mock()
    response.json.return_value = {
        "usage": {"matchType": "EXACT", "normalizedName": "Abies alba"},
        "diagnostics": {"matchType": "EXACT"},
    }
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert normalize_spezies(
        "Abies alba Mill.",
        query_param="name",
        response_fields=["usage.normalizedName"],
    ) == {"usage": {"normalizedName": "Abies alba"}}
    request_get.assert_called_once_with(
        GBIF_SPECIES_MATCH_URL,
        params={"name": "Abies alba Mill."},
        timeout=10,
    )


def test_normalize_spezies_returns_none_below_minimum_confidence(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {
        "usage": {"canonicalName": "Abies alba"},
        "diagnostics": {"matchType": "EXACT", "confidence": 90},
    }
    request_get = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    assert normalize_spezies("Abies alba Mill.", min_confidence=95) is None


def test_normalize_spezies_returns_all_fields_and_normalizes_classification(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {
        "classification": [
            {"key": "6", "name": "Plantae", "rank": "KINGDOM"},
            {"key": "7707728", "name": "Pinopsida", "rank": "CLASS"},
        ],
        "diagnostics": {"matchType": "EXACT"},
        "usage": {"canonicalName": "Abies alba"},
    }
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", Mock(return_value=response))

    assert normalize_spezies("Abies alba Mill.", response_fields=None) == {
        "classification": {"KINGDOM": "Plantae", "CLASS": "Pinopsida"},
        "diagnostics": {"matchType": "EXACT"},
        "usage": {"canonicalName": "Abies alba"},
    }


def test_normalize_spezies_empty_or_no_response_field_list(
    monkeypatch,
) -> None:
    response = Mock()
    response.json.return_value = {
        "diagnostics": {"matchType": "EXACT"},
        "usage": {"canonicalName": "Abies alba"},
    }
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", Mock(return_value=response))

    # if no response_fields are specified, the entire response is returned
    assert normalize_spezies(
        "Abies alba Mill.", response_fields=None
    ) == response.json.return_value | {"classification": {}}

    # if an empty list of response_fields is specified, an empty dict is returned
    assert normalize_spezies("Abies alba Mill.", response_fields=[]) == {}


def test_normalize_spezies_returns_none_when_gbif_finds_no_match(monkeypatch) -> None:
    response = Mock()
    response.json.return_value = {"diagnostics": {"matchType": "NONE", "confidence": 100}}
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", Mock(return_value=response))

    assert normalize_spezies("not-a-real-species-xyzzy") is None


def test_normalize_spezies_propagates_gbif_request_errors(monkeypatch) -> None:
    request_get = Mock(side_effect=requests.ConnectionError)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.get", request_get)

    with pytest.raises(requests.ConnectionError):
        normalize_spezies("Abies alba Mill.")


@pytest.mark.parametrize("min_confidence", [-1, 101])
def test_normalize_spezies_rejects_out_of_range_minimum_confidence(
    min_confidence: int,
) -> None:
    with pytest.raises(ValueError, match="min_confidence must be between 0 and 100"):
        normalize_spezies("Abies alba Mill.", min_confidence=min_confidence)


def test_normalize_spezies_batch_posts_names_and_normalizes_results_in_input_order(
    monkeypatch,
) -> None:
    response = Mock()
    response.json.return_value = [
        {
            "usage": {"canonicalName": "Abies alba"},
            "diagnostics": {"matchType": "EXACT", "confidence": 100},
        },
        {"usage": {}, "diagnostics": {"matchType": "NONE", "confidence": 100}},
        {
            "usage": {"canonicalName": "Abies"},
            "diagnostics": {"matchType": "HIGHERRANK", "confidence": 94},
        },
    ]
    request_post = Mock(return_value=response)
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.post", request_post)

    assert normalize_spezies_batch(
        ["Abies alba Mill.", "not-a-real-species-xyzzy", "Abies albaa"],
        min_confidence=95,
    ) == [
        {
            "classification": {},
            "diagnostics": {"confidence": 100, "matchType": "EXACT"},
            "usage": {"canonicalName": "Abies alba"},
        },
        None,
        None,
    ]
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


def test_normalize_spezies_batch_rejects_more_than_one_thousand_names(monkeypatch) -> None:
    request_post = Mock()
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.post", request_post)

    with pytest.raises(ValueError, match="GBIF accepts up to 1,000 names"):
        normalize_spezies_batch(["Abies alba"] * 1001)

    request_post.assert_not_called()


@pytest.mark.parametrize("batch_response", [{}, [{}, {}]])
def test_normalize_spezies_batch_rejects_invalid_response_shape(
    monkeypatch, batch_response
) -> None:
    response = Mock()
    response.json.return_value = batch_response
    monkeypatch.setattr("kibad_llm.normalization.gbif.requests.post", Mock(return_value=response))

    with pytest.raises(ValueError, match="GBIF returned an invalid batch match response"):
        normalize_spezies_batch(["Abies alba"])


def test_filter_nested_dict_preserves_selected_common_prefixes_and_ignores_invalid_paths() -> None:
    response: NestedDict = {
        "diagnostics": {"confidence": 94, "matchType": "HIGHERRANK"},
        "usage": {"canonicalName": "Abies", "rank": "GENUS"},
    }

    assert _filter_nested_dict(
        response,
        ["usage.canonicalName", "usage.rank", "diagnostics.missing", "usage.rank.value", ""],
    ) == {"usage": {"canonicalName": "Abies", "rank": "GENUS"}}


@pytest.mark.slow
def test_normalize_spezies_live_gbif_endpoint() -> None:
    # set response_fields=None to get all available fields from the GBIF API
    # (remember that we restructure the classification field)
    result = normalize_spezies("Abies albaa", response_fields=None)
    assert result is not None
    # drop time related values since they are not deterministic
    result["diagnostics"].pop("timeTaken", None)
    result["diagnostics"].pop("timings", None)
    assert result == {
        "classification": {
            "CLASS": "Pinopsida",
            "FAMILY": "Pinaceae",
            "GENUS": "Abies",
            "KINGDOM": "Plantae",
            "ORDER": "Pinales",
            "PHYLUM": "Tracheophyta",
        },
        "diagnostics": {
            "confidence": 94,
            "matchType": "HIGHERRANK",
        },
        "left": 865764,
        "right": 865921,
        "synonym": False,
        "usage": {
            "authorship": "Mill.",
            "canonicalName": "Abies",
            "formattedName": "<i>Abies</i> Mill.",
            "key": "2684876",
            "name": "Abies Mill.",
            "rank": "GENUS",
            "status": "ACCEPTED",
            "type": "SCIENTIFIC",
        },
    }
