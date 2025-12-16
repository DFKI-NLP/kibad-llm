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
        strip_plus_from_keys=True,
        id_key="file_name",
        process_id=strip_filename_extension,
        preprocess=lambda x: x.get("structured", None),
    )
    assert isinstance(result, dict)
    assert len(result) == 4
    assert isinstance(result, DictWithMetadata)
    assert result.metadata == {
        "overrides": {
            "pdf_directory": "tests/fixtures/pdfs",
            "request_parameters.extra_body.seed": "42",
        }
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
