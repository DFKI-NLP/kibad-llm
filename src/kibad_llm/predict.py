from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

from datasets import Dataset
import hydra
from hydra.utils import instantiate
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for as _validator_for
from llama_index.core import Settings, set_global_handler
from llama_index.core.llms import LLM, ChatMessage, MessageRole
from omegaconf import DictConfig
import pymupdf4llm

from kibad_llm.config import PROJ_ROOT
from kibad_llm.schema.utils import build_schema_description

logger = logging.getLogger(__name__)


def read_pdf_as_markdown(file_name: str, base_path: Path) -> dict[str, str]:
    """Read a PDF file and convert it to markdown using pymupdf4llm.

    Args:
        file_name: The name of the PDF file to read.
        base_path: The base path where the PDF file is located.
    Returns:
        A dictionary with a single key "markdown" containing the markdown text.
    """
    return {"markdown": pymupdf4llm.to_markdown(str(base_path / file_name))}


def extract_from_markdown(
    # IMPORTANT: The order of the arguments depends on the order in the Dataset map input_columns!
    markdown: str,
    file_name: str,
    system_message: str,
    user_message: str | None = None,
    schema: dict[str, Any] | None = None,
    system_message_requires_schema_description: bool = False,
    model: LLM | None = None,
) -> dict:
    """Extract structured information from markdown text using an LLM.

    Args:
        markdown: The markdown text to process.
        file_name: File name for logging and seeding.
        system_message: The system message template (required). If system_message_requires_schema_description
            is True, it must contain a "{schema_description}" placeholder.
        user_message: The user message template (optional, defaults to just the markdown).
        schema: Optional JSON schema for structured output.
        system_message_requires_schema_description: Whether the system message template
            requires a schema description (will raise an error if True but no schema provided).
            The schema description will be built from the provided schema.
        model: The LLM model to use (defaults to Settings.llm). Must be a chat model (i.e. is_chat_model=True)
            and support extra_body parameters for guided decoding if schema is provided.

    Returns:
        A dictionary with keys "text" (the raw LLM output) and "structured" (the parsed JSON or None).
    """

    if model is None:
        model = Settings.llm

    # Build chat messages
    if schema is not None and system_message_requires_schema_description:
        schema_description = build_schema_description(schema=schema)
        system = system_message.format(schema_description=schema_description)
    else:
        if system_message_requires_schema_description:
            raise ValueError(
                "system_message_requires_schema_description is True but no schema provided"
            )
        system = system_message
    user = user_message.format(document=markdown) if user_message else markdown
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system),
        ChatMessage(role=MessageRole.USER, content=user),
    ]

    # Determinism knobs (standard args stay top-level; vendor extras go in extra_body)
    seed_src = f"{file_name or ''}\n{user}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)

    vllm_extras: dict[str, Any] = {"seed": seed, "top_k": -1}  # vendor-specific → extra_body

    if schema is not None:
        vllm_extras["guided_json"] = schema
        vllm_extras["guided_decoding_backend"] = "lm-format-enforcer"

    # Chat call (reasoning kept separate by server; final JSON is in message.content)
    resp = model.chat(messages, extra_body=vllm_extras)

    text = getattr(resp.message, "content", "") or ""
    out: dict[str, Any | None] = {"text": text, "structured": None}

    # Parse & validate (schema optional)
    try:
        data = json.loads(text)
        if schema is not None:
            validator_cls = _validator_for(schema)
            validator_cls.check_schema(schema)
            validator = validator_cls(schema)
            validator.validate(data)
        out["structured"] = data
    except (json.JSONDecodeError, ValidationError):
        logger.warning(f"Failed to obtain/validate structured output for document {file_name}")

    return out


def _file_name_generator(file_names: list[str]):
    for file_name in file_names:
        yield {"file_name": file_name}


def predict(cfg: DictConfig) -> None:

    logger.info("Instantiating LLM model interface ...")
    logger.info(f"LLM config: {dict(cfg.model)}")
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
    dataset = dataset.map(
        function=read_pdf_as_markdown,
        input_columns=["file_name"],
        fn_kwargs={"base_path": data_base_path},
    )

    logger.info("Extracting information from markdown ...")
    # the template needs to contain system_message and may contain user_message, schema and
    # system_message_requires_schema_description; all may be constructed from sub-configs
    template = instantiate(cfg.template, _convert_="all")
    dataset = dataset.map(
        function=extract_from_markdown,
        input_columns=["markdown", "file_name"],
        fn_kwargs=template,
        new_fingerprint=extraction_new_fingerprint,
    )

    logger.info(f"Writing results to {cfg.output_file} ...")
    dataset.to_json(cfg.output_file)


@hydra.main(version_base="1.3", config_path=str(PROJ_ROOT / "configs"), config_name="predict.yaml")
def main(cfg: DictConfig) -> None:
    predict(cfg)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    # set env var PROJECT_ROOT
    os.environ["PROJECT_ROOT"] = str(PROJ_ROOT)
    main()
