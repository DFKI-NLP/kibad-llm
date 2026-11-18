"""Opt-in prediction smoke test using a real tiny in-process vLLM model."""

import json
from pathlib import Path

from hydra.core.hydra_config import HydraConfig
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.predict import predict
from tests.conftest import cfg_global


@pytest.mark.slow
def test_micro_llm_prediction(tmp_path):
    """Predict all four complete fixture PDFs without replaying LLM responses."""
    cfg = cfg_global(
        overrides=["experiment/predict=micro_llm", "store_text_in_predictions=true"],
        out_dir=tmp_path,
    )
    HydraConfig().set_config(cfg)
    job = predict(cfg)
    rows = [
        json.loads(line) for line in Path(job["output_file_absolute"]).read_text().splitlines()
    ]

    expected_files = {path.name for path in (PROJ_ROOT / "tests/fixtures/pdfs").glob("*.pdf")}
    assert len(rows) == len(expected_files) == 4
    assert {row["file_name"] for row in rows} == expected_files
    for row in rows:
        assert row["errors_list"]
        assert all(not errors for errors in row["errors_list"]), row["file_name"]
        assert isinstance(row["structured"], dict)
        cursor = 0
        for start, end in zip(row["character_start_list"], row["character_end_list"]):
            assert not row["text"][cursor:start].strip()
            cursor = end
        assert not row["text"][cursor:].strip()
