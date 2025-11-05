from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import INTERIM_DATA_DIR, PROJ_ROOT
from kibad_llm.evaluate import evaluate
from tests.conftest import cfg_global

# This was produced with the default pipeline configuration on the PDFs in tests/fixtures/pdfs
PREDICTIONS_FILE = PROJ_ROOT / "tests" / "fixtures" / "evaluation" / "predictions.jsonl"
# This was produced by converting the Faktencheck-DB via the script in src/kibad_llm/data_integration/db_converter.py
REFERENCES_FILE = INTERIM_DATA_DIR / "faktencheck-db" / "faktencheck-db-converted_2025-11-05.jsonl"


@pytest.fixture(scope="function")
def cfg_evaluate(tmp_path) -> DictConfig:  # type: ignore
    cfg = cfg_global(out_dir=tmp_path, config_name="evaluate.yaml")

    with open_dict(cfg):
        cfg.predictions_file = str(PREDICTIONS_FILE)
        cfg.references_file = str(REFERENCES_FILE)
        # this produces non-zero results
        cfg.metric.field = "habitat"

    yield cfg

    GlobalHydra.instance().clear()


def test_evaluate(tmp_path, cfg_evaluate):
    """For now, this is primarily to test that the evaluation runs end-to-end without errors."""

    HydraConfig().set_config(cfg_evaluate)
    metric_scores = evaluate(cfg_evaluate)

    assert metric_scores == pytest.approx(
        {"f1": 2 * ((3 / 8) / (1 + (3 / 8))), "precision": 3 / 8, "recall": 1}
    )
