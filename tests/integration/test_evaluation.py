from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import INTERIM_DATA_DIR, PROJ_ROOT
from kibad_llm.evaluate import evaluate
from tests.conftest import cfg_global


@pytest.fixture(scope="function")
def cfg_evaluate(tmp_path) -> DictConfig:  # type: ignore
    cfg = cfg_global(out_dir=tmp_path, config_name="evaluate.yaml")

    with open_dict(cfg):
        cfg.predictions_file = str(
            PROJ_ROOT / "tests" / "fixtures" / "evaluation" / "predictions.jsonl"
        )
        cfg.references_file = str(
            INTERIM_DATA_DIR / "faktencheck-db" / "faktencheck-db-converted_2025-08-19.jsonl"
        )
        cfg.metric.field = "ecosystem_type/term"

    yield cfg

    GlobalHydra.instance().clear()


@pytest.mark.slow
def test_evaluate(tmp_path, cfg_evaluate):

    HydraConfig().set_config(cfg_evaluate)
    metric_scores = evaluate(cfg_evaluate)
    assert metric_scores == {"f1": 0.0, "precision": 0.0, "recall": 0.0}
