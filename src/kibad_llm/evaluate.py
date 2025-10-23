from __future__ import annotations

from collections.abc import Mapping
import json
import logging
import os
from typing import Any

from datasets import Dataset
import hydra
from hydra.utils import instantiate
from omegaconf import DictConfig

from kibad_llm.config import PROJ_ROOT
from kibad_llm.metric import Metric
from kibad_llm.utils.datasets import wrap_map_func

logger = logging.getLogger(__name__)


def _get_key_from_prediction(entry: Mapping[str, Any]) -> str:
    """Use the file name without extension as key for aligning predictions with references."""
    return os.path.splitext(entry["file_name"])[0]


def _get_key_from_reference(entry: Mapping[str, Any]) -> str:
    """Use the zotitem_ptr_id as key for aligning references with predictions."""
    return entry["zotitem_ptr_id"]


def _get_reference(prediction: Mapping[str, Any], references: dict[str, dict]) -> dict:
    """Get the corresponding reference for a prediction. Return as dict
    with single key to comply with datasets map function."""
    prediction_key = _get_key_from_prediction(prediction)
    return references[prediction_key]


def evaluate(cfg: DictConfig) -> dict[str, Any]:
    """Evaluate predictions against gold references using a specified metric.

    Args:
        cfg: OmegaConf configuration. See configs/evaluate.yaml for details.
    Returns:
        A dictionary with evaluation results.
    """

    logger.info(f"Loading predictions from {cfg.predictions_file} ...")
    predictions = Dataset.from_json(cfg.predictions_file)
    if cfg.get("preprocess_prediction"):
        logger.info(
            "Preprocess predictions for metric computation (e.g. map schema keys to json paths) ..."
        )
        prediction_preprocessor = instantiate(cfg.preprocess_prediction, _convert_="all")
        prediction_preprocessor_wrapped = wrap_map_func(
            func=prediction_preprocessor, result_key="prediction"
        )
        predictions = predictions.map(prediction_preprocessor_wrapped)

    logger.info(f"Loading gold references from {cfg.references_file} ...")
    references_dict = {}
    with open(cfg.references_file, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            references_dict[_get_key_from_reference(entry)] = entry

    logger.info("Aligning references with predictions ...")
    predictions = predictions.map(
        wrap_map_func(_get_reference, result_key="reference"),
        fn_kwargs={"references": references_dict},
    )
    if cfg.get("preprocess_reference"):
        logger.info("Preprocess references for metric computation (e.g. flatten dicts) ...")
        reference_preprocessor = instantiate(cfg.preprocess_reference, _convert_="all")
        reference_preprocessor_wrapped = wrap_map_func(
            func=reference_preprocessor, result_key="reference"
        )
        predictions = predictions.map(reference_preprocessor_wrapped, input_columns=["reference"])

    logger.info("Instantiating metric ...")
    logger.info(f"Metric config: {dict(cfg.metric)}")
    metric: Metric = instantiate(cfg.metric, _convert_="all")

    logger.info("Computing metric ...")
    predictions.map(
        metric.update,
        input_columns=["prediction", "reference"],
        # disable caching since we are interested in the side effect of updating the metric,
        # not in the returned dataset
        load_from_cache_file=False,
    )
    metric_dict = metric.compute()

    logger.info(f"Evaluation results:\n{json.dumps(metric_dict, indent=2)}")

    return metric_dict


@hydra.main(
    version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="evaluate.yaml"
)
def main(cfg: DictConfig) -> dict[str, Any]:
    return evaluate(cfg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
