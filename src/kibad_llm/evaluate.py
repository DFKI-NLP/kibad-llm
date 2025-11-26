from __future__ import annotations

import logging
import os
from typing import Any

import hydra
from hydra.utils import instantiate
from omegaconf import DictConfig

from kibad_llm.config import PROJ_ROOT
from kibad_llm.metric import Metric

logger = logging.getLogger(__name__)


def evaluate(cfg: DictConfig) -> dict[str, Any]:
    """Evaluate predictions against gold references using a specified metric and optional preprocessing
    of predictions and references.

    Args:
        cfg: OmegaConf configuration. See configs/evaluate.yaml for details.
    Returns:
        A dictionary with evaluation results.
    """
    logger.info("Loading dataset with predictions and references ...")
    dataset = instantiate(cfg.dataset, _convert_="all")

    logger.info("Instantiating metric ...")
    logger.info(f"Metric config: {dict(cfg.metric)}")
    metric: Metric = instantiate(cfg.metric, _convert_="all")

    logger.info("Computing metric ...")
    dataset.map(
        metric.update,
        input_columns=["prediction", "reference"],
        # disable caching since we are interested in the side effect of updating the metric,
        # not in the returned dataset
        load_from_cache_file=False,
    )
    metric_dict = metric.compute()

    metric.show_result(metric_dict)

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
