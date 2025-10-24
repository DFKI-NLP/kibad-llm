from __future__ import annotations

import logging
import os
from pathlib import Path

import hydra
from datasets import Dataset
from hydra.utils import instantiate
from llama_index.core import set_global_handler
from omegaconf import DictConfig

from kibad_llm.config import PROJ_ROOT
from kibad_llm.utils.datasets import wrap_map_func

logger = logging.getLogger(__name__)


def _file_name_generator(file_names: list[str]):
    for file_name in file_names:
        yield {"file_name": file_name}


def predict(cfg: DictConfig) -> None:
    """Run classification based information extraction on PDF files.

    Reads all PDF files from cfg.pdf_directory, converts them to markdown,
    extracts structured information using an LLM model and a prompt template,
    and writes the results to cfg.output_file in JSON lines format. Caches
    intermediate results by using map from the datasets library.

    Args:
        cfg: OmegaConf configuration. See configs/predict.yaml for details.
    """

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
            f"fast_dev_run is set: only processing the first PDF file ({dataset[0]['file_name']}) but show extended logging ..."
        )
        dataset = dataset.take(1)
        set_global_handler("simple")

    if cfg.get("disable_extraction_caching", False):
        # disable caching for the extraction step
        extraction_new_fingerprint = str(os.urandom(16).hex())
    else:
        extraction_new_fingerprint = None

    logger.info("Converting PDF to markdown ...")
    logger.info(f"PDF reader config: {dict(cfg.pdf_reader)}")
    pdf_reader = instantiate(cfg.pdf_reader, _convert_="all")
    pdf_reader_wrapped = wrap_map_func(func=pdf_reader, result_key="text")
    dataset = dataset.map(
        function=pdf_reader_wrapped,
        input_columns=["file_name"],
        fn_kwargs={"base_path": data_base_path},
    )

    logger.info("Instantiating Extractor ...")
    logger.info(f"Extractor config: {dict(cfg.extractor)}")
    extractor = instantiate(cfg.extractor, _convert_="all")

    logger.info("Extract information from markdown ...")
    dataset = dataset.map(
        function=extractor,
        input_columns=["text", "file_name"],
        new_fingerprint=extraction_new_fingerprint,
    )

    logger.info(f"Writing results to {cfg.output_file} ...")
    dataset.to_json(cfg.output_file, force_ascii=False)


@hydra.main(version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="predict.yaml")
def main(cfg: DictConfig) -> None:
    predict(cfg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
