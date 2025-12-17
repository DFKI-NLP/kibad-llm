from __future__ import annotations

import logging
import os
from typing import Any

import hydra
from hydra.utils import instantiate
from omegaconf import DictConfig, OmegaConf

from kibad_llm.config import PROJ_ROOT
from kibad_llm.dataset.prediction import DictWithMetadata
from kibad_llm.metric import Metric

logger = logging.getLogger(__name__)


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
        metric_dict.update(dataset.metadata)

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
