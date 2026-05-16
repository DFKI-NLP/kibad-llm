"""Unit tests for :func:`kibad_llm.dataset.prediction.load_with_metadata`.

Verifies both loading modes: from a Hydra log directory (returns a
:class:`~kibad_llm.dataset.prediction.DictWithMetadata` with attached job-return
metadata) and from a direct JSONL file path (returns a plain dict without metadata).
"""

from kibad_llm.dataset.prediction import (
    DictWithMetadata,
    load_with_metadata,
)
from kibad_llm.utils.path import strip_filename_extension
from tests import FIXTURE_DATA_ROOT


def test_load_with_metadata():
    log = FIXTURE_DATA_ROOT / "dataset" / "load_with_metadata" / "logs" / "2025-12-16_17-14-35"
    # based on configs/dataset/predictions/extraction_result.yaml
    result = load_with_metadata(
        log=str(log),
        id_key="file_name",
        process_id=strip_filename_extension,
        preprocess=lambda x: x.get("structured", None),
    )
    assert isinstance(result, dict)
    assert len(result) == 4
    assert isinstance(result, DictWithMetadata)
    assert result.metadata == {
        "job_return_value": {
            "output_file": "tests/fixtures/dataset/load_with_metadata/predictions/2025-12-16_17-14-35/2025-12-16_17-14-35_389616/predictions.jsonl",
            "time_extraction": 41.152598176000026,
            "time_pdf_conversion": 0.0015077599999813174,
        },
        "overrides": [
            "pdf_directory=tests/fixtures/pdfs",
            "+request_parameters.extra_body.seed=42",
        ],
    }

    # test falling back to file loading
    file = (
        FIXTURE_DATA_ROOT
        / "dataset"
        / "load_with_metadata"
        / "predictions"
        / "2025-12-16_17-14-35"
        / "2025-12-16_17-14-35_389616"
        / "predictions.jsonl"
    )
    # based on configs/dataset/predictions/extraction_result.yaml
    result_fallback = load_with_metadata(
        file=str(file),
        id_key="file_name",
        process_id=strip_filename_extension,
        preprocess=lambda x: x.get("structured", None),
    )
    assert isinstance(result_fallback, dict)
    assert len(result_fallback) == 4
    assert not isinstance(result_fallback, DictWithMetadata)
    assert dict(result) == result_fallback
