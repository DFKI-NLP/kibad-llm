from __future__ import annotations

import logging
import os
from typing import Any

import hydra
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

from kibad_llm.config import PROJ_ROOT, RESULT_FORMAT_VERSION_KEY
from kibad_llm.dataset.prediction import DictWithMetadata
from kibad_llm.metric import Metric
from kibad_llm.utils.path import get_directories_with_file

# This needs to be incremented when the format of the evaluation results changes in a non-backwards-compatible
# way, e.g. if we change the structure of the metric_dict returned by evaluate() or the expected metadata
# format. This allows us to keep track of which version of the evaluation results we are working with and
# handle them accordingly in downstream processing.
EVALUATE_VERSION = 1

logger = logging.getLogger(__name__)

# required when using predictions_multirun_logs, see configs/evaluate.yaml
OmegaConf.register_new_resolver(
    "get_directories_with_file",
    # join resulting list into a comma-separated string
    lambda paths, filename, leafs_only: ",".join(
        get_directories_with_file(paths, filename, leafs_only)
    ),
)


def evaluate(cfg: DictConfig) -> dict[str, Any]:
    """Evaluates a dataset containing predictions and references using a specified metric.

    Args:
        cfg: OmegaConf configuration. See configs/evaluate.yaml for details.
    Returns:
        A dictionary with evaluation results.
    """
    logger.info("Loading dataset with predictions and references ...")
    logger.info(f"Dataset config: {OmegaConf.to_container(cfg.dataset, resolve=True)}")
    dataset = instantiate(cfg.dataset, _convert_="all")

    logger.info("Instantiating metric ...")
    logger.info(f"Metric config: {OmegaConf.to_container(cfg.metric, resolve=True)}")
    metric: Metric = instantiate(cfg.metric, _convert_="all")

    logger.info("Computing metric ...")
    for record_id, example in dataset.items():
        metric.update(
            prediction=example["prediction"], reference=example["reference"], record_id=record_id
        )
    metric_dict = metric.compute()

    metric.show_result(metric_dict)

    if isinstance(dataset, DictWithMetadata):
        if "prediction" in metric_dict:
            raise ValueError(
                "Cannot attach metadata to 'prediction' key in metric_dict because it already "
                "exists as output from the metric computation. Please adjust the metric computation."
            )
        metric_dict["prediction"] = dataset.metadata

    if RESULT_FORMAT_VERSION_KEY in metric_dict:
        raise ValueError(
            "Cannot attach version to metric_dict because 'version' key already exists. "
            "Please adjust the metric computation."
        )

    metric_dict[RESULT_FORMAT_VERSION_KEY] = EVALUATE_VERSION

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
