import logging
import sys
from unittest.mock import Mock, call

import pytest

from kibad_llm.normalization.cli import (
    _normalize_values,
    _process_json_object,
    main,
    process_json_lines_file,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (
            "Fagus sylvatica L.",
            ({"normalized": "Fagus sylvatica L."}, 1, 1),
        ),
        (
            ["Abies alba Mill.", "Pinus sylvestris L."],
            ([{"normalized": "Abies alba Mill."}, None], 2, 1),
        ),
    ],
)
def test_normalize_values_returns_normalized_values_and_statistics(
    value: str | list[str],
    expected: tuple[dict[str, str] | list[dict[str, str] | None], int, int],
) -> None:
    def normalize(name: str) -> dict[str, str] | None:
        return None if name == "Pinus sylvestris L." else {"normalized": name}

    assert _normalize_values(value, normalizer=normalize) == expected


def test_process_json_object_rejects_non_string_list_entries() -> None:
    with pytest.raises(TypeError, match="Values lists must contain only strings"):
        _process_json_object(
            {"species": ["Abies alba Mill.", {"species": "Pinus sylvestris L."}]},
            [],
            "species",
            "normalized_species",
            normalizer=lambda _: {},
        )


def test_process_json_object_normalizes_values_in_nested_dicts_and_lists() -> None:
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
        side_effect=lambda value, **_: (
            None if value == "Pinus sylvestris L." else {"normalized": value}
        )
    )

    assert _process_json_object(
        json_object,
        ["groups", "observations", "entries"],
        "species",
        "normalized_species",
        normalizer=normalize,
    ) == (3, 2)

    assert json_object == {
        "groups": [
            {
                "observations": {
                    "entries": [
                        {
                            "species": ["Abies alba Mill.", "Pinus sylvestris L."],
                            "normalized_species": [{"normalized": "Abies alba Mill."}, None],
                        },
                        {
                            "species": "Fagus sylvatica L.",
                            "normalized_species": {"normalized": "Fagus sylvatica L."},
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
    tmp_path,
) -> None:
    input_path = tmp_path / "input.jsonl"
    output_path = tmp_path / "output.jsonl"
    input_path.write_text('{"species": "Dörjes"}\n', encoding="utf-8")
    caplog.set_level(logging.INFO, logger="kibad_llm.normalization.cli")
    process_json_lines_file(
        input_path=input_path,
        output_path=output_path,
        read_key="species",
        write_key="normalized_species",
        normalizer=lambda value: {"normalized": value},
    )

    assert (
        output_path.read_text(encoding="utf-8")
        == '{"species": "Dörjes", "normalized_species": {"normalized": "Dörjes"}}\n'
    )
    assert "Processed 1 lines, normalized 1 values out of 1 processed." in caplog.messages


def test_process_json_lines_file_writes_default_jsonl_beside_input(tmp_path) -> None:
    input_path = tmp_path / "input.jsonl"
    input_path.write_text('{"species": "Abies alba Mill."}\n')
    output_path = tmp_path / "input_species_normalized.jsonl"

    process_json_lines_file(
        input_path=input_path,
        output_path=output_path,
        read_key="species",
        write_key="species_normalized",
        normalizer=lambda value: {"normalized": "Abies alba"},
    )

    assert output_path.read_text() == (
        '{"species": "Abies alba Mill.", "species_normalized": {"normalized": "Abies alba"}}\n'
    )


def test_main_creates_gbif_normalizer_with_default_options(monkeypatch, tmp_path) -> None:
    process = Mock()
    normalize = Mock(return_value={"usage": {"canonicalName": "Abies alba"}})
    monkeypatch.setattr("kibad_llm.normalization.cli.process_json_lines_file", process)
    monkeypatch.setattr("kibad_llm.normalization.gbif.normalize_spezies", normalize)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "normalization",
            "gbif",
            "--input-path",
            str(tmp_path / "input.jsonl"),
            "--read-key",
            "species",
        ],
    )

    main()

    process.assert_called_once()
    process_arguments = dict(process.call_args.kwargs)
    normalizer = process_arguments.pop("normalizer")
    assert process_arguments == {
        "input_path": tmp_path / "input.jsonl",
        "read_key": "species",
        "output_path": tmp_path / "input_species_normalized.jsonl",
        "write_key": "gbif_normalized",
        "parent_keys": [],
    }
    assert normalizer("Abies alba Mill.") == {"usage": {"canonicalName": "Abies alba"}}
    normalize.assert_called_once_with(
        "Abies alba Mill.",
        min_confidence=None,
        query_param="scientificName",
        response_fields=None,
    )
