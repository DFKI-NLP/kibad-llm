"""Integration tests for the evaluation entry point and metric configurations."""

from collections.abc import Iterator
import os

from hydra.core.global_hydra import GlobalHydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, open_dict
import pytest

from kibad_llm.config import PROJ_ROOT
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
def metric_name(request: pytest.FixtureRequest) -> str:
    """Return one metric config name for the parametrized evaluation tests."""
    return request.param


@pytest.fixture(scope="function")
def cfg_evaluate(tmp_path, metric_name) -> Iterator[DictConfig]:
    """Build an evaluation config tailored to the parametrized metric under test."""
    overrides = [f"metric={metric_name}"]
    if metric_name == "prediction_errors":
        # for this metric, we need to set a specific dataset that does not strip errors
        overrides.append("dataset=predictions_only")
    cfg = cfg_global(out_dir=tmp_path, config_name="evaluate.yaml", overrides=overrides)

    with open_dict(cfg):
        cfg.dataset.predictions.file = str(PREDICTIONS_FILE)
        # this produces non-zero results
        if metric_name in ["confusion_matrix", "f1_micro_single_field", "tpfpfn_single_field"]:
            cfg.metric.field = "habitat"
        elif metric_name in [
            "confusion_matrix_multiple_fields",
            "f1_micro",
            "tpfpfn_multiple_fields",
        ]:
            cfg.metric.fields = ["habitat", "landuse"]
        elif metric_name == "prediction_errors":
            pass  # no extra config needed
        else:
            raise ValueError(
                f"Unexpected metric name: {metric_name}. Please update the test case."
            )

    yield cfg

    GlobalHydra.instance().clear()


def test_evaluate(tmp_path, cfg_evaluate: DictConfig, metric_name: str) -> None:
    """For now, this is primarily to test that the evaluation runs end-to-end without errors."""

    HydraConfig().set_config(cfg_evaluate)
    job_result = evaluate(cfg_evaluate)
    assert set(job_result) == {"version", "type", "data"}
    metric_type = job_result["type"]
    assert job_result["version"] == 2
    metric_scores = job_result["data"]

    if metric_name == "f1_micro_single_field":
        assert metric_type == "F1MicroSingleFieldMetric"
        assert metric_scores == pytest.approx(
            {
                "f1": 2 * ((3 / 8) / (1 + (3 / 8))),
                "precision": 3 / 8,
                "recall": 1,
                "support": 3,
            }
        )
    elif metric_name == "confusion_matrix":
        assert metric_type == "ConfusionMatrix"
        assert metric_scores == {
            "Agrar- und Offenland": {"Agrar- und Offenland": 1.0, "Wald": 0.5},
            "Küsten und Küstengewässer": {
                "Binnengewässer und Auen": 1.0,
                "Küsten und Küstengewässer": 2.0,
            },
            "UNASSIGNABLE": {
                "Agrar- und Offenland": 1.0,
                "Binnengewässer und Auen": 1.0,
                "Boden": 1.0,
                "Wald": 0.5,
            },
        }
    elif metric_name == "confusion_matrix_multiple_fields":
        assert metric_type == "ConfusionMatrixCollection"
        assert metric_scores == {
            "habitat": {
                "Agrar- und Offenland": {"Agrar- und Offenland": 1.0, "Wald": 0.5},
                "Küsten und Küstengewässer": {
                    "Binnengewässer und Auen": 1.0,
                    "Küsten und Küstengewässer": 2.0,
                },
                "UNASSIGNABLE": {
                    "Agrar- und Offenland": 1.0,
                    "Binnengewässer und Auen": 1.0,
                    "Boden": 1.0,
                    "Wald": 0.5,
                },
            },
            "landuse": {
                "Naturnahe und natürliche Flächen, die nicht genutzt werden": {
                    "Landwirtschaft": 0.3333333333333333,
                    "UNDETECTED": 0.3333333333333333,
                    "Verkehr, Kommunikationsnetzwerke, Lagerung, Schutzwälle": 0.3333333333333333,
                },
                "UNASSIGNABLE": {
                    "Bau": 1.0,
                    "Energieproduktion": 1.0,
                    "Erholung, Freizeit, Sport": 1.0,
                    "Fischerei und Aquakultur": 1.0,
                    "Industrie und Fertigung": 1.0,
                    "Landwirtschaft": 2.0,
                    "Verkehr, Kommunikationsnetzwerke, Lagerung, Schutzwälle": 1.0,
                    "Wohngebiete": 1.0,
                },
            },
        }
    elif metric_name == "f1_micro":
        assert metric_type == "F1MicroMultipleFieldsMetric"
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
        assert metric_type == "ErrorCollector"
        # we don't have any errors in the predictions file
        assert metric_scores == {"no_error": 4}
    elif metric_name == "tpfpfn_single_field":
        assert metric_type == "TpFpFnCollector"
        assert metric_scores == {
            "25ABQZIH": {"fn": [], "fp": ["Agrar- und Offenland", "Boden"], "tp": []},
            "25RIYD2C": {"fn": [], "fp": ["Wald"], "tp": ["Agrar- und Offenland"]},
            "7T8NZA5Q": {
                "fn": [],
                "fp": ["Binnengewässer und Auen"],
                "tp": ["Küsten und Küstengewässer"],
            },
            "BBDCY7DW": {
                "fn": [],
                "fp": ["Binnengewässer und Auen"],
                "tp": ["Küsten und Küstengewässer"],
            },
        }
    elif metric_name == "tpfpfn_multiple_fields":
        assert metric_type == "TpFpFnCollectorCollection"
        assert metric_scores == {
            "habitat": {
                "25ABQZIH": {
                    "fn": [],
                    "fp": ["Agrar- und Offenland", "Boden"],
                    "tp": [],
                },
                "25RIYD2C": {
                    "fn": [],
                    "fp": ["Wald"],
                    "tp": ["Agrar- und Offenland"],
                },
                "7T8NZA5Q": {
                    "fn": [],
                    "fp": ["Binnengewässer und Auen"],
                    "tp": ["Küsten und Küstengewässer"],
                },
                "BBDCY7DW": {
                    "fn": [],
                    "fp": ["Binnengewässer und Auen"],
                    "tp": ["Küsten und Küstengewässer"],
                },
            },
            "landuse": {
                "25ABQZIH": {
                    "fn": [],
                    "fp": ["Bau", "Energieproduktion", "Landwirtschaft"],
                    "tp": [],
                },
                "25RIYD2C": {
                    "fn": ["Naturnahe und natürliche Flächen, die nicht genutzt werden"],
                    "fp": [
                        "Landwirtschaft",
                        "Verkehr, Kommunikationsnetzwerke, Lagerung, Schutzwälle",
                    ],
                    "tp": [],
                },
                "7T8NZA5Q": {
                    "fn": [],
                    "fp": ["Erholung, Freizeit, Sport", "Fischerei und Aquakultur"],
                    "tp": [],
                },
                "BBDCY7DW": {
                    "fn": [],
                    "fp": ["Industrie und Fertigung", "Wohngebiete"],
                    "tp": [],
                },
            },
        }
    else:
        raise ValueError(f"Unexpected metric name: {metric_name}. Please update the test case.")
