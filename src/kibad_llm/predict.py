from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import logging
import os
from pathlib import Path
import time
from typing import Any

from datasets import Dataset
import hydra
from hydra.utils import instantiate
from llama_index.core import set_global_handler
from omegaconf import DictConfig

from kibad_llm.config import PROJ_ROOT
from kibad_llm.utils.datasets import wrap_map_func

logger = logging.getLogger(__name__)


def _file_name_generator(file_names: list[str]):
    for file_name in file_names:
        yield {"file_name": file_name}


def predict(cfg: DictConfig) -> dict[str, Any]:
    """Run classification based information extraction on PDF files.

    Reads all PDF files from cfg.pdf_directory, converts them to markdown,
    extracts structured information using an LLM model and a prompt template,
    and writes the results to cfg.output_file in JSON lines format. Caches
    intermediate results by using map from the datasets library.

    Args:
        cfg: OmegaConf configuration. See configs/predict.yaml for details.
    """
    # use start time as part of output folder to avoid overwriting previous results
    formatted_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")

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

    logger.info("Converting PDF to markdown ...")
    logger.info(f"PDF reader config: {dict(cfg.pdf_reader)}")
    pdf_reader = instantiate(cfg.pdf_reader, _convert_="all")
    pdf_reader_wrapped = wrap_map_func(func=pdf_reader, result_key="text")
    t_start_pdf_conversion = time.perf_counter()
    dataset = dataset.map(
        function=pdf_reader_wrapped,
        input_columns=["file_name"],
        fn_kwargs={"base_path": data_base_path},
        num_proc=cfg.pdf_reader_num_proc,
    )
    t_delta_pdf_conversion = time.perf_counter() - t_start_pdf_conversion

    logger.info("Instantiating Extractor ...")
    logger.info(f"Extractor config: {dict(cfg.extractor)}")
    # The extractor gets the text and file_name as input
    # and should return a json serializable dictionary with the extracted information.
    extractor: Callable[[str, str], dict[str, Any]] = instantiate(cfg.extractor, _convert_="all")

    logger.info("Extract information from markdown ...")
    t_start_extraction = time.perf_counter()
    dataset = dataset.map(
        function=extractor,
        input_columns=["text", "file_name"],
        load_from_cache_file=cfg.get("extraction_caching", False),
    )
    t_delta_extraction = time.perf_counter() - t_start_extraction

    if not cfg.get("store_text_in_predictions", True):
        dataset = dataset.remove_columns("text")

    # use output dir with timestamp to avoid overwriting previous results
    output_file = os.path.join(cfg.output_dir, formatted_time, "predictions.jsonl")
    logger.info(f"Writing results to {output_file} ...")
    dataset.to_json(output_file, force_ascii=False)
    return {
        "output_file": output_file,
        "time_pdf_conversion": t_delta_pdf_conversion,
        "time_extraction": t_delta_extraction,
    }


@hydra.main(version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="predict.yaml")
def main(cfg: DictConfig) -> dict[str, Any]:
    return predict(cfg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
