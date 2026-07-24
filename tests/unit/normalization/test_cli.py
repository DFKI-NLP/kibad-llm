import logging
import sys
from unittest.mock import Mock, call

import pytest

from kibad_llm.normalization.cli import (
    _normalize_names,
    _process_json_object,
    process_json_lines_file,
)


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
    name: str | list[str],
    expected: tuple[str | list[str | None], int, int],
) -> None:
    normalize = lambda name, **_: (
        None if name == "Pinus sylvestris L." else f"normalized: {name}"
    )
    assert _normalize_names(name, func=normalize) == expected


def test_process_json_object_rejects_non_string_list_entries() -> None:
    with pytest.raises(TypeError, match="Species name lists must contain only strings"):
        _process_json_object(
            {"species": ["Abies alba Mill.", {"species": "Pinus sylvestris L."}]},
            [],
            "species",
            "normalized_species",
            func=lambda name, **_: name,
        )


def test_process_json_object_normalizes_names_in_nested_dicts_and_lists() -> None:
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

    assert _process_json_object(
        json_object,
        ["groups", "observations", "entries"],
        "species",
        "normalized_species",
        func=normalize,
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
        call(
            "Abies alba Mill.",
            min_confidence=None,
            query_param="scientificName",
            response_field="canonicalName",
        ),
        call(
            "Pinus sylvestris L.",
            min_confidence=None,
            query_param="scientificName",
            response_field="canonicalName",
        ),
        call(
            "Fagus sylvatica L.",
            min_confidence=None,
            query_param="scientificName",
            response_field="canonicalName",
        ),
    ]


def test_process_json_lines_file_writes_normalized_json_line_and_statistics(
    caplog,
    # monkeypatch,
    tmp_path,
) -> None:
    input_path = tmp_path / "input.jsonl"
    output_path = tmp_path / "output.jsonl"
    input_path.write_text('{"species": "Abies alba Mill."}\n')
    caplog.set_level(logging.INFO, logger="kibad_llm.normalization.cli")

    process_json_lines_file(
        input_path=str(input_path),
        read_key="species",
        output_path=str(output_path),
        write_key="normalized_species",
        func=lambda name, **_: "Abies alba",
    )

    assert (
        output_path.read_text()
        == '{"species": "Abies alba Mill.", "normalized_species": "Abies alba"}\n'
    )
    assert "Processed 1 lines, normalized 1 names out of 1 processed." in caplog.messages


def test_process_json_lines_file_writes_default_jsonl_beside_input(tmp_path) -> None:
    input_path = tmp_path / "input.jsonl"
    input_path.write_text('{"species": "Abies alba Mill."}\n')

    process_json_lines_file(
        input_path=str(input_path),
        read_key="species",
        func=lambda name, **_: "Abies alba",
    )

    assert (tmp_path / "input_normalized_names.jsonl").read_text() == (
        '{"species": "Abies alba Mill.", "species_normalized": "Abies alba"}\n'
    )


def test_main_uses_gbif_default_options(monkeypatch, tmp_path) -> None:
    process = Mock()
    monkeypatch.setattr("kibad_llm.normalization.cli.process_json_lines_file", process)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "normalization",
            "--input-path",
            str(tmp_path / "input.jsonl"),
            "--read-key",
            "species",
        ],
    )

    from kibad_llm.normalization.cli import main

    main()

    process.assert_called_once_with(
        input_path=str(tmp_path / "input.jsonl"),
        read_key="species",
        output_path=None,
        write_key=None,
        parent_keys=[],
        min_confidence=None,
        query_param="scientificName",
        response_field="canonicalName",
    )
