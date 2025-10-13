from __future__ import annotations

import logging
import os
from pathlib import Path

from datasets import Dataset
import hydra
from hydra.utils import instantiate
from llama_index.core import Settings
from llama_index.core.llms import LLM
from omegaconf import DictConfig
import pymupdf4llm

from kibad_llm.config import PROJ_ROOT

logger = logging.getLogger(__name__)


def read_pdf_as_markdown(file_name: str, base_path: Path) -> dict[str, str]:
    return {"markdown": pymupdf4llm.to_markdown(str(base_path / file_name))}


def extract_from_markdown(
    markdown: str, template: str, model: LLM | None = None
) -> dict[str, str]:
    if model is None:
        model = Settings.llm
    prompt = template.format(document=markdown)
    response = model.complete(prompt)
    result = {"raw": response.text}
    return result


def _file_name_generator(file_names: list[str]):
    for file_name in file_names:
        yield {"file_name": file_name}


def predict(cfg: DictConfig) -> None:

    logger.info("Instantiating LLM model interface ...")
    Settings.llm = instantiate(cfg.model)

    data_base_path = Path(cfg.pdf_directory)

    # Create the dataset based on the sorted file names. This will define the cache key.
    # IMPORTANT: This means the whole dataset will be re-processed if any file is added/removed!
    file_names = sorted(p.name for p in data_base_path.glob("*.pdf"))
    dataset = Dataset.from_generator(
        generator=_file_name_generator, gen_kwargs={"file_names": file_names}
    )
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
