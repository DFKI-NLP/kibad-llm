from __future__ import annotations

import logging
import os
from pathlib import Path

import hydra
import pymupdf4llm
from datasets import Dataset
from hydra.utils import instantiate
from llama_index.core import Settings
from omegaconf import DictConfig

from kibad_llm.config import PROJ_ROOT

logger = logging.getLogger(__name__)


def read_pdf_as_markdown(file_name: str, base_path: Path) -> dict[str, str]:
    return {"markdown": pymupdf4llm.to_markdown(str(base_path / file_name))}


def extract_from_markdown(markdown: str, template: str) -> dict[str, str]:
    prompt = template.format(document=markdown)
    response = Settings.llm.complete(prompt)
    result = {"raw": response.text}
    return result


def predict(cfg: DictConfig) -> None:

    logger.info("Instantiating LLM model interface ...")
    Settings.llm = instantiate(cfg.model)

    data_base_path = Path(cfg.pdf_directory)

    dataset = Dataset.from_list([{"file_name": p.name} for p in data_base_path.glob("*.pdf")])
    logger.info(f"Processing {len(dataset)} PDF files from {cfg.pdf_directory} ...")
    if cfg.get("fast_dev_run", False) and len(dataset) > 0:
        logger.warning(
            f"fast_dev_run is set: only processing the first PDF file ({dataset[0]['file_name']}) ..."
        )
        dataset = dataset.take(1)

    logger.info("Converting PDF to markdown ...")
    dataset = dataset.map(
        function=read_pdf_as_markdown,
        input_columns=["file_name"],
        fn_kwargs={"base_path": data_base_path},
    )

    logger.info("Extracting information from markdown ...")
    dataset = dataset.map(
        function=extract_from_markdown,
        input_columns=["markdown"],
        fn_kwargs={"template": cfg.template.text},
    )

    logger.info(f"Writing results to {cfg.output_file} ...")
    dataset.to_json(cfg.output_file)


@hydra.main(version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="predict.yaml")
def main(cfg: DictConfig) -> None:
    predict(cfg)


if __name__ == "__main__":
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
