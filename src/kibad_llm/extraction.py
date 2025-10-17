from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for as _validator_for
from llama_index.core import Settings
from llama_index.core.llms import LLM, ChatMessage, MessageRole

from kibad_llm.schema.utils import build_schema_description

logger = logging.getLogger(__name__)


def extract_from_text(
    text: str,
    text_id: str,
    system_message: str,
    user_message: str | None = None,
    schema: dict[str, Any] | None = None,
    system_message_requires_schema_description: bool = False,
    model: LLM | None = None,
) -> dict:
    """Extract structured information from text using an LLM.

    Given a chat model (per default, uses Settings.llm from llama-index), composes system
    and user messages, and invokes the model. When a schema is provided, it is used to enforce
    guided decoding. The output is parsed as JSON and validated against the schema if provided.

    Args:
        text: The text to process.
        text_id: Text identifier for logging and seeding.
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
    user = user_message.format(document=text) if user_message else text
    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system),
        ChatMessage(role=MessageRole.USER, content=user),
    ]

    # Determinism knobs (standard args stay top-level; vendor extras go in extra_body)
    seed_src = f"{text_id or ''}\n{user}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)

    vllm_extras: dict[str, Any] = {"seed": seed, "top_k": -1}  # vendor-specific → extra_body

    if schema is not None:
        vllm_extras["guided_json"] = schema
        vllm_extras["guided_decoding_backend"] = "lm-format-enforcer"

    # Chat call (reasoning kept separate by server; final JSON is in message.content)
    resp = model.chat(messages, extra_body=vllm_extras)

    response_content = getattr(resp.message, "content", "") or ""
    out: dict[str, Any | None] = {"response_content": response_content, "structured": None}

    # Parse & validate (schema optional)
    try:
        data = json.loads(response_content)
        if schema is not None:
            validator_cls = _validator_for(schema)
            validator_cls.check_schema(schema)
            validator = validator_cls(schema)
            validator.validate(data)
        out["structured"] = data
    except (json.JSONDecodeError, ValidationError):
        logger.warning(f"Failed to obtain/validate structured output for document {text_id}")

    return out
