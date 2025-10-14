from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from datasets import Dataset
import hydra
from hydra.utils import instantiate
from jsonschema import Draft202012Validator, validators
from llama_index.core import Settings, set_global_handler
from llama_index.core.llms import LLM
from omegaconf import DictConfig
from pydantic import ValidationError
import pymupdf4llm

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.types import EcosystemStudyFeatures

logger = logging.getLogger(__name__)


def _extend_with_default(validator_cls):
    validate_props = validator_cls.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        if isinstance(instance, dict):
            for prop, subschema in properties.items():
                if "default" in subschema and prop not in instance:
                    instance[prop] = subschema["default"]
        yield from validate_props(validator, properties, instance, schema)

    return validators.extend(validator_cls, {"properties": set_defaults})


DefaultingValidator = _extend_with_default(Draft202012Validator)


def read_pdf_as_markdown(file_name: str, base_path: Path) -> dict[str, str]:
    return {"markdown": pymupdf4llm.to_markdown(str(base_path / file_name))}


def extract_from_markdown(
    markdown: str,
    file_name: str | None = None,
    document_context: str | None = None,
    schema: dict[str, Any] | None = None,
    model: LLM | None = None,
) -> dict:
    """
    Extract structured information from markdown text using an LLM.

    Args:
        markdown (str): The markdown document to process.
        file_name (str | None): Optional name of the file being processed (for logging).
        document_context (str | None): Optional prompt template to provide context for the document. Needs to contain a `{document}` placeholder.
        schema (dict | None): Optional JSON schema to guide the LLM's output structure.
        model (LLM | None): Optional LLM model instance to use (primarily for testing).
            If None, uses the globally configured model.

    Returns:
        dict: A dictionary with keys:
            - "text": The raw text output from the LLM.
            - "structured": The structured data extracted, or None if extraction/validation failed.
    Example:
        result = extract_from_markdown(
            markdown="# Sample Document\nThis is a sample.",
            file_name="sample.md",
            document_context="Extract the following information from the document:\n{document}",
            schema={
                "title": "SampleSchema",
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "content_summary": {"type": "string"},
                },
                "required": ["title", "content_summary"],
            },
            model=my_llm_instance
        )

        print(result["text"])  # Raw LLM output
        print(result["structured"])  # Parsed structured data or None
    """

    if model is None:
        model = Settings.llm

    if schema is None and document_context is None:
        raise ValueError("At least one of schema or document_context must be provided")

    completion_kwargs: dict[str, Any] = {}

    if document_context is not None:
        prompt = document_context.format(document=markdown)
    else:
        prompt = markdown

    # Option A: OpenAI-style JSON Schema (if your vLLM build supports it)
    if schema is not None:
        rf = {
            "type": "json_schema",
            "strict": True,
            "json_schema": {"name": schema["title"], "schema": schema},
        }
        completion_kwargs["response_format"] = rf

    resp = model.complete(prompt, **completion_kwargs)

    # Option B (very compatible with vLLM): guided JSON
    # resp = model.complete(prompt, guided_json=schema)

    out: dict[str, Any | None] = {"text": resp.text, "structured": None}
    try:
        data = json.loads(resp.text)
        if schema is not None:
            DefaultingValidator(schema).validate(data)  # fills defaults + validates
        out["structured"] = data
    except (json.JSONDecodeError, ValidationError):
        logger.warning(f"Failed to obtain/validate structured output for document {file_name}")
    return out


def _file_name_generator(file_names: list[str]):
    for file_name in file_names:
        yield {"file_name": file_name}


def predict(cfg: DictConfig) -> None:

    logger.info("Instantiating LLM model interface ...")
    llm = instantiate(cfg.model)

    Settings.llm = llm  # llm.as_structured_llm(output_cls=BiodiversityFeatures)

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
    dataset = dataset.map(
        function=read_pdf_as_markdown,
        input_columns=["file_name"],
        fn_kwargs={"base_path": data_base_path},
    )

    logger.info("Extracting information from markdown ...")
    # the template may contain: document_context and schema; both are optional and can be instantiated objects
    template = instantiate(cfg.template, _convert_="all")
    dataset = dataset.map(
        function=extract_from_markdown,
        input_columns=["markdown", "file_name"],
        fn_kwargs=template,
        # use random fingerprint to always re-evaluate
        new_fingerprint=str(os.urandom(16).hex()),
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
