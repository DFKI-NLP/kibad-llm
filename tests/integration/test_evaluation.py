import os

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import INTERIM_DATA_DIR, PROJ_ROOT
from kibad_llm.evaluate import evaluate
from tests.conftest import cfg_global

# strip extension to have nicer logging output, e.g. tests/integration/test_evaluation.py::test_evaluate[f1]
# and exclude folders (without extension) and helper configs starting with "_"
AVAILABLE_METRICS = [
    os.path.splitext(config_yaml)[0]
    for config_yaml in os.listdir(PROJ_ROOT / "configs" / "metric")
    if os.path.splitext(config_yaml)[1] != "" and not config_yaml.startswith("_")
]


# This was produced with the default pipeline configuration on the PDFs in tests/fixtures/pdfs
PREDICTIONS_FILE = PROJ_ROOT / "tests" / "fixtures" / "evaluation" / "predictions.jsonl"
# This was produced by converting the Faktencheck-DB via the script in src/kibad_llm/data_integration/db_converter.py
REFERENCES_FILE = INTERIM_DATA_DIR / "faktencheck-db" / "faktencheck-db-converted_2025-08-19.jsonl"


@pytest.fixture(scope="function", params=AVAILABLE_METRICS)
def metric_name(request) -> str:
    return request.param


@pytest.fixture(scope="function")
def cfg_evaluate(tmp_path, metric_name) -> DictConfig:  # type: ignore
    cfg = cfg_global(
        out_dir=tmp_path, config_name="evaluate.yaml", overrides=[f"metric={metric_name}"]
    )

    with open_dict(cfg):
        cfg.predictions_file = str(PREDICTIONS_FILE)
        cfg.references_file = str(REFERENCES_FILE)
        # this produces non-zero results
        cfg.metric.field = "habitat"

    yield cfg

    GlobalHydra.instance().clear()


def test_evaluate(tmp_path, cfg_evaluate, metric_name):
    """For now, this is primarily to test that the evaluation runs end-to-end without errors."""

    HydraConfig().set_config(cfg_evaluate)
    metric_scores = evaluate(cfg_evaluate)

    if metric_name == "f1":
        assert metric_scores == pytest.approx(
            {"f1": 2 * ((3 / 8) / (1 + (3 / 8))), "precision": 3 / 8, "recall": 1}
        )
    elif metric_name == "confusion_matrix":
        assert metric_scores == {
            "Agrar- und Offenland": {"Agrar- und Offenland": 1},
            "Küsten und Küstengewässer": {"Küsten und Küstengewässer": 2},
            "UNASSIGNABLE": {
                "Agrar- und Offenland": 1,
                "Binnengewässer und Auen": 1,
                "Boden": 1,
                "Urbane Räume": 1,
                "Wald": 1,
            },
        }
    else:
        raise ValueError(f"Unexpected metric name: {metric_name}. Please update the test case.")
