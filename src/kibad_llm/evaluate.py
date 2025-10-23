from __future__ import annotations

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

logger = logging.getLogger(__name__)


def _get_key_from_prediction(entry: dict[str, Any]) -> str:
    """Use the file name without extension as key for aligning predictions with references."""
    return os.path.splitext(entry["file_name"])[0]


def _get_key_from_reference(entry: dict[str, Any]) -> str:
    """Use the zotitem_ptr_id as key for aligning references with predictions."""
    return entry["zotitem_ptr_id"]


def _get_and_add_reference(prediction: dict, references: dict[str, dict]) -> dict:
    """Get the corresponding reference for a prediction and flatten it. Return as dict
    with single key to comply with datasets map function."""
    prediction_key = _get_key_from_prediction(prediction)
    return {"reference": references[prediction_key]}


def flatten_dict_simple(d: dict[str, Any], sep: str = ".") -> dict[str, Any]:
    """Flatten a dictionary with simple rules:
    - Keep only non-empty primitive values (str, int, float, bool)
    - For lists of primitives, keep as is
    - For lists of dicts, create new keys by combining parent key and child keys,
      and aggregate values into lists (removing duplicates and sorting)

    IMPORTANT: This function does not handle nested dicts beyond one level inside lists.

    Args:
        d: The dictionary to flatten.
        sep: The separator to use when combining keys.
    Returns:
        A flattened dictionary.
    """
    result: dict[str, Any] = dict()
    for k, v in d.items():
        # remove empty values
        if v is None or (isinstance(v, str) and v.strip() == ""):
            pass
        elif isinstance(v, (str, int, float, bool)):
            result[k] = v
        elif isinstance(v, list):
            if all(isinstance(e, (str, int, float, bool)) for e in v):
                result[k] = v
            elif all(isinstance(e, dict) for e in v):
                current_keys = set()
                for e in v:
                    for k2, v2 in e.items():
                        if v2 is not None and not (isinstance(v2, str) and v2.strip() == ""):
                            (
                                result[f"{k}{sep}{k2}"].append(v2)
                                if f"{k}{sep}{k2}" in result
                                else result.setdefault(f"{k}{sep}{k2}", [v2])
                            )
                            current_keys.add(f"{k}{sep}{k2}")
                for k2 in current_keys:
                    result[k2] = sorted(set(result[k2]))
            else:
                raise ValueError(f"Cannot flatten list with mixed types: {v}")

    return result


def _prepare_reference(reference: dict[str, Any]) -> dict[str, Any]:
    reference_flat = flatten_dict_simple(reference, sep="/")
    return {"reference": reference_flat}


def _prepare_prediction(
    entry: dict[str, Any], json_paths_mapping: dict[str, str]
) -> dict[str, Any]:
    """Prepare prediction by taking only the structured part and mapping schema keys to
    json paths. Return as dict with single key to comply with datasets map function."""
    mapped = {json_paths_mapping[k]: v for k, v in entry["structured"].items()}
    return {"prediction": mapped}


def evaluate(cfg: DictConfig) -> dict[str, Any]:
    """Evaluate predictions against gold references using a specified metric.

    Args:
        cfg: OmegaConf configuration. See configs/evaluate.yaml for details.
    Returns:
        A dictionary with evaluation results.
    """

    logger.info(f"Loading predictions from {cfg.predictions_file} ...")
    predictions = Dataset.from_json(cfg.predictions_file)

    logger.info(f"Loading gold references from {cfg.references_file} ...")
    references_dict = {}
    with open(cfg.references_file, encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            references_dict[_get_key_from_reference(entry)] = entry

    logger.info("Aligning predictions with references ...")
    predictions = predictions.map(
        _get_and_add_reference, fn_kwargs={"references": references_dict}
    )
    logger.info("Preparing references for metric computation ...")
    predictions = predictions.map(_prepare_reference, input_columns=["reference"])
    logger.info("Preparing predictions for metric computation (map schema keys to json paths) ...")
    predictions = predictions.map(
        _prepare_prediction, fn_kwargs={"json_paths_mapping": cfg.json_paths_mapping}
    )

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
