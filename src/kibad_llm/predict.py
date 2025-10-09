from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
import pymupdf4llm


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


def _coerce_json(text: str) -> dict[str, Any]:
    """
    Best-effort parsing of model output into JSON.

    Tries strict `json.loads`. If that fails, extracts the substring between the
    first '{' and the last '}' and tries again. Falls back to returning the raw text.

    Args:
        text: The raw model output.

    Returns:
        A dictionary parsed from JSON, or `{'raw': <text>}` if parsing fails.
    """
    try:
        return json.loads(text)
    except Exception:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        snippet = text[start : end + 1]
        try:
            return json.loads(snippet)
        except Exception:
            pass
    return {"raw": text.strip()}


def extract_from_pdf(pdf_path: str | Path, fields_csv: list[str], top_k: int) -> dict[str, Any]:
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
        fields_csv: Comma-separated field names to extract.
        top_k: Unused parameter kept for API compatibility.

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

    prompt = (
        "You are an information extraction assistant.\n"
        "Given the document content in markdown format, extract the following fields as a compact JSON object.\n"
        f"Fields: {', '.join(fields_csv)}\n"
        "Rules:\n"
        "- Return ONLY valid JSON.\n"
        "- If a field is missing, set it to null or an empty list.\n"
        "- Keep values concise.\n"
        "\n"
        "Document:\n"
        f"{md}"
    )

    response = Settings.llm.complete(prompt)
    return _coerce_json(response.text)
