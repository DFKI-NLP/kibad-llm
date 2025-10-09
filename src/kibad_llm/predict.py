from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import hydra
from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
from omegaconf import DictConfig
import pymupdf4llm

from kibad_llm.config import PROJ_ROOT

logger = logging.getLogger(__name__)


def init_llm(model: str, api_base: str, api_key: str, temperature: float) -> None:
    """
    Configure the global LlamaIndex LLM for downstream calls.

    Args:
        model: OpenAI-compatible model name (e.g., 'gpt-4o-mini').
        api_base: Base URL of the OpenAI-compatible endpoint (e.g., 'http://localhost:8000/v1').
        api_key: API key (dummy is fine for local/self-hosted backends).
        temperature: Sampling temperature for generation.

    Side Effects:
        Sets `Settings.llm` globally.
    """

    # If you must use a non-OpenAI model name against OpenAI wrapper, disable the Responses API:
    Settings.llm = OpenAILike(
        model=model,
        api_base=api_base,
        api_key=api_key or "dummy",  # many self-hosted backends ignore this
        temperature=temperature,
    )


def extract_from_pdf(pdf_path: str | Path, prompt_questions: str) -> dict[str, Any]:
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

    prompt = f"{prompt_questions}\n\nDokument in Markdown Format:\n{md}"
    response = Settings.llm.complete(prompt)
    result = {
        "file_name": path.name,
        "raw": response.text
    }
    return result


def predict(cfg: DictConfig) -> None:

    init_llm(
        model=cfg.model_name,
        api_base=os.getenv("LLM_API_BASE", cfg.api_base),
        api_key=cfg.api_key,
        temperature=0.0,
    )
    result = extract_from_pdf(pdf_path=cfg.pdf_file, prompt_questions=cfg.template.questions)
    # write result to cfg.output_file
    output_path = Path(cfg.output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)


@hydra.main(version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="predict.yaml")
def main(cfg: DictConfig) -> None:
    predict(cfg)


if __name__ == "__main__":
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
