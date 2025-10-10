from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import hydra
from hydra.utils import instantiate
from llama_index.core import Settings
from llama_index.core.llms.utils import LLMType
from omegaconf import DictConfig
import pymupdf4llm

from kibad_llm.config import PROJ_ROOT

logger = logging.getLogger(__name__)


def extract_from_pdf(pdf_path: str | Path, template: str) -> dict[str, Any]:
    """
    Extract requested fields from a PDF by prompting the LLM directly (no retrieval/index).

    Steps:
      1. Convert the PDF to Markdown via `pymupdf4llm`.
      2. Build a concise extraction prompt listing requested fields.
      3. Call `Settings.llm.complete` and coerce the output to JSON.

    Note:
        `top_k` is unused in this non-retrieval variant.

    Args:
        pdf_path: Path to a `.pdf` file.
        template: A prompt template with a `{document}` placeholder for the PDF content in Markdown.

    Returns:
        A dictionary containing extracted fields or a fallback with the raw model output.

    Raises:
        ValueError: If `pdf_path` does not point to a `.pdf`.
        TypeError: If `fields_csv` is not a `str` or `top_k` is not an `int`.

    Requirements:
        `Settings.llm` must be configured (see `init_llm`).
    """
    # Note: top_k unused when not doing retrieval.
    path = Path(pdf_path)
    if path.suffix.lower() != ".pdf":
        raise ValueError("Only PDF files are supported.")

    md = pymupdf4llm.to_markdown(str(path))

    prompt = template.format(document=md)
    response = Settings.llm.complete(prompt)
    result = {"file_name": path.name, "raw": response.text}
    return result


def predict_single(cfg: DictConfig) -> None:

    # setup the model interface
    model: LLMType = instantiate(cfg.model)
    Settings.llm = model

    # execute extraction
    result = extract_from_pdf(pdf_path=cfg.pdf_file, template=cfg.template.text)

    # write result to cfg.output_file
    output_path = Path(cfg.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)


@hydra.main(
    version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="predict_single.yaml"
)
def main(cfg: DictConfig) -> None:
    predict_single(cfg)


if __name__ == "__main__":
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
