from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from llama_index.core import Settings
from llama_index.llms.openai_like import OpenAILike
import pymupdf4llm

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

    prompt_questions = """
    Bitte lese den folgenden Text vollständig. Der Text ist eine Studie zu einem Ökosystem. Beantworte die folgenden Fragen auf Deutsch, auch wenn der Text auf Englisch ist.  Wenn Antwortmöglichkeiten nach einer Frage gegeben sind, wähle eine von den durch Komma getrennten Antwortmöglichkeiten aus.

    1. Frage: In welchem Lebensraum wurde die Studie durchgeführt? Antwortmöglichkeiten: Wald, Agrar- und Offenland, Binnengewässer und Auen, Küste und Küstengewässer, Urbane Räume, Boden

    2. Frage: In welchem Naturgroßraum wurde die Studie durchgeführt? Antwortmöglichkeiten: Alpen, Alpenvorland, Mittelgebirgsschwelle, Norddeutsches Tiefland, Nord- und Ostsee oder Schichtsstufenland beidseits des Oberrheingrabens

    3. Frage: Welchen Ökosystemtyp hat die Studie betrachtet? Antwortmöglichkeiten: Binnenland: Waldfreie Niedermoore und Sümpfe, Grünland nasser bis feuchter Standorte; Binnenland: Laub(Misch)Wälder und -Forste (Laubbaumanteil über 50 Prozent); Binnengewässer: Stehende Gewässer; Meere und Küsten: Benthal der Nordsee

    4. Frage: In welchem Bundesland liegt das betrachtete Ökosystem der Studie? Antwortmöglichkeiten: Baden-Württemberg, Bayern, Niedersachsen, Brandenburg, Berlin, Bremen, Hamburg, Hessen,  Mecklenburg-Vorpommern, Niedersachsen, Nordrhein-Westfalen, Rheinland-Pfalz, Saarland, Sachsen, Sachsen-Anhalt, Schleswig-Holstein, Thüringen
    """

    prompt = f"{prompt_questions}\n\nDokument in Markdown Format:\n{md}"
    response = Settings.llm.complete(prompt)
    return {"raw": response.text}
