"""Integration tests for the evaluate pipeline (:func:`kibad_llm.evaluate.evaluate`).

Parametrized over all metric configs found in ``configs/metric/`` (excluding helper
configs prefixed with ``_``).  For each metric the test instantiates a Hydra config,
runs the full evaluation against a stored predictions fixture, and asserts exact
numeric output values.
"""

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


@pytest.fixture(scope="function", params=AVAILABLE_METRICS)
def metric_name(request) -> str:
    return request.param


@pytest.fixture(scope="function")
def cfg_evaluate(tmp_path, metric_name) -> DictConfig:  # type: ignore
    overrides = [f"metric={metric_name}"]
    if metric_name == "prediction_errors":
        # for this metric, we need to set a specific dataset that does not strip errors
        overrides.append("dataset=predictions_only")
    cfg = cfg_global(out_dir=tmp_path, config_name="evaluate.yaml", overrides=overrides)

    with open_dict(cfg):
        cfg.dataset.predictions.file = str(PREDICTIONS_FILE)
        # this produces non-zero results
        if metric_name in ["confusion_matrix", "f1_micro_single_field"]:
            cfg.metric.field = "habitat"
        elif metric_name == "f1_micro":
            cfg.metric.fields = ["habitat", "landuse"]
        elif metric_name == "prediction_errors":
            pass  # no extra config needed
        else:
            raise ValueError(
                f"Unexpected metric name: {metric_name}. Please update the test case."
            )

    yield cfg

    GlobalHydra.instance().clear()


def test_evaluate(tmp_path, cfg_evaluate, metric_name):
    """For now, this is primarily to test that the evaluation runs end-to-end without errors."""

    HydraConfig().set_config(cfg_evaluate)
    metric_scores = evaluate(cfg_evaluate)

    if metric_name == "f1_micro_single_field":
        assert metric_scores == pytest.approx(
            {"f1": 2 * ((3 / 8) / (1 + (3 / 8))), "precision": 3 / 8, "recall": 1, "support": 3}
        )
    elif metric_name == "confusion_matrix":
        assert metric_scores == {
            "Agrar- und Offenland": {"Agrar- und Offenland": 1},
            "Küsten und Küstengewässer": {"Küsten und Küstengewässer": 2},
            "UNASSIGNABLE": {
                "Agrar- und Offenland": 1,
                "Binnengewässer und Auen": 2,
                "Boden": 1,
                "Wald": 1,
            },
        }
    elif metric_name == "f1_micro":
        assert metric_scores == {
            "habitat": {
                "f1": pytest.approx(0.545454545),
                "precision": 0.375,
                "recall": 1.0,
                "support": 3,
            },
            "landuse": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1},
            "AVG": {
                "f1": pytest.approx(0.272727272),
                "precision": 0.1875,
                "recall": 0.5,
                "support": 2,
            },
            "ALL": {
                "f1": pytest.approx(0.28571428),
                "precision": pytest.approx(0.17647058823),
                "recall": 0.75,
                "support": 4,
            },
        }
    elif metric_name == "prediction_errors":
        # we don't have any errors in the predictions file
        assert metric_scores == {"no_error": 4}
    else:
        raise ValueError(f"Unexpected metric name: {metric_name}. Please update the test case.")
