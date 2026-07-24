import logging
from unittest.mock import Mock, call

import pytest
import requests

from kibad_llm.normalization.gbif import (
    GBIF_SPECIES_BATCH_MATCH_URL,
    GBIF_SPECIES_MATCH_URL,
    _normalize_names,
    _process_json_object,
    normalize_spezies,
    normalize_spezies_batch,
    process_json_lines_file,
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


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        (
            "Fagus sylvatica L.",
            ("normalized: Fagus sylvatica L.", 1, 1),
        ),
        (
            ["Abies alba Mill.", "Pinus sylvestris L."],
            (["normalized: Abies alba Mill.", None], 2, 1),
        ),
    ],
)
def test_normalize_names_returns_normalized_names_and_statistics(
    monkeypatch,
    name: str | list[str],
    expected: tuple[str | list[str | None], int, int],
) -> None:
    normalize = Mock(
        side_effect=lambda name, **_: (
            None if name == "Pinus sylvestris L." else f"normalized: {name}"
        )
    )
    monkeypatch.setattr("kibad_llm.normalization.gbif.normalize_spezies", normalize)

    assert _normalize_names(name) == expected


def test_process_json_object_rejects_non_string_list_entries() -> None:
    with pytest.raises(TypeError, match="Species name lists must contain only strings"):
        _process_json_object(
            {"species": ["Abies alba Mill.", {"species": "Pinus sylvestris L."}]},
            [],
            "species",
            "normalized_species",
        )


def test_process_json_object_normalizes_names_in_nested_dicts_and_lists(
    monkeypatch,
) -> None:
    json_object = {
        "groups": [
            {
                "observations": {
                    "entries": [
                        {"species": ["Abies alba Mill.", "Pinus sylvestris L."]},
                        {"species": "Fagus sylvatica L."},
                    ]
                }
            }
        ]
    }
    normalize = Mock(
        side_effect=lambda name, **_: (
            None if name == "Pinus sylvestris L." else f"normalized: {name}"
        )
    )
    monkeypatch.setattr("kibad_llm.normalization.gbif.normalize_spezies", normalize)

    assert _process_json_object(
        json_object,
        ["groups", "observations", "entries"],
        "species",
        "normalized_species",
    ) == (3, 2)

    assert json_object == {
        "groups": [
            {
                "observations": {
                    "entries": [
                        {
                            "species": ["Abies alba Mill.", "Pinus sylvestris L."],
                            "normalized_species": [
                                "normalized: Abies alba Mill.",
                                None,
                            ],
                        },
                        {
                            "species": "Fagus sylvatica L.",
                            "normalized_species": "normalized: Fagus sylvatica L.",
                        },
                    ]
                }
            }
        ]
    }
    assert normalize.call_args_list == [
        call("Abies alba Mill."),
        call("Pinus sylvestris L."),
        call("Fagus sylvatica L."),
    ]


def test_process_json_lines_file_writes_normalized_json_line_and_statistics(
    caplog,
    monkeypatch,
    tmp_path,
) -> None:
    input_path = tmp_path / "input.jsonl"
    output_path = tmp_path / "output.jsonl"
    input_path.write_text('{"species": "Abies alba Mill."}\n')
    caplog.set_level(logging.INFO, logger="kibad_llm.normalization.gbif")
    monkeypatch.setattr(
        "kibad_llm.normalization.gbif.normalize_spezies",
        Mock(return_value="Abies alba"),
    )

    process_json_lines_file(
        input_path=str(input_path),
        read_key="species",
        output_path=str(output_path),
        write_key="normalized_species",
    )

    assert (
        output_path.read_text()
        == '{"species": "Abies alba Mill.", "normalized_species": "Abies alba"}\n'
    )
    assert "Processed 1 lines, normalized 1 names out of 1 processed." in caplog.messages
