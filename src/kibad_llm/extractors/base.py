from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import logging
from typing import Any

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for
from llama_index.core import Settings
from llama_index.core.llms import LLM, ChatMessage, MessageRole

from kibad_llm.schema.utils import build_schema_description

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def warn_once(msg: str) -> None:
    """Log a warning message only once by caching the function call."""
    logger.warning(f"{msg} (this message will only be shown once)")


def extract_from_text(
    text: str,
    text_id: str,
    system_message: str,
    user_message: str | None = None,
    schema: dict[str, Any] | None = None,
    system_message_requires_schema_description: bool = False,
    schema_description_kwargs: dict[str, Any] | None = None,
    llm: LLM | None = None,
    return_reasoning: bool = False,
    return_messages: bool = False,
    return_messages_formatted: bool = False,
    truncate_user_message_formatted: int | None = 300,
) -> dict:
    """Extract structured information from text using an LLM.

    Given a chat llm (per default, uses Settings.llm from llama-index), composes system
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
        schema_description_kwargs: Optional kwargs for build_schema_description when generating
            the schema description.
        llm: The LLM model to use (defaults to Settings.llm). Must be a chat model (i.e. is_chat_model=True)
            and support extra_body parameters for guided decoding if schema is provided.
        return_reasoning: Whether to return the reasoning done by the model.
        return_messages: Whether to return the used prompt messages, but without input text and
            schema description.
        return_messages_formatted: Whether to return the used prompt messages formatted with
            input text and schema description.
        truncate_user_message_formatted: If return_messages_formatted is True, truncate the user message
            content to this many characters (to avoid huge outputs). Set to None to disable truncation.

    Returns:
        A dictionary with keys "text" (the raw LLM output) and "structured" (the parsed JSON or None).
    """
    # setting the log level on every query is suboptimal, but the simplest solution in our current architecture
    logging.getLogger("httpx").setLevel(logging.WARNING)

    out: dict[str, Any | None] = {
        "response_content": None,
        "structured": None,
        "reasoning_content": None,
        "messages": None,
        "messages_formatted": None,
        "error": None,
    }

    if return_messages:
        # return the prompt messages without input text and schema description
        out["messages"] = {
            "system": system_message,
            "user": user_message,
        }

    if llm is None:
        llm = Settings.llm

    # Build chat messages
    if schema is not None and system_message_requires_schema_description:
        schema_description = build_schema_description(
            schema=schema, **(schema_description_kwargs or {})
        )
        system = system_message.format(schema_description=schema_description)
    else:
        if system_message_requires_schema_description:
            raise ValueError(
                "system_message_requires_schema_description is True but no schema provided"
            )
        system = system_message
    user = user_message.format(document=text) if user_message else text

    if return_messages_formatted:
        messages_formatted = {"system": system, "user": user}
        if (
            truncate_user_message_formatted is not None
            and len(user) > truncate_user_message_formatted
        ):
            messages_formatted["user"] = (
                f"{user[:truncate_user_message_formatted]}... (truncated @ {truncate_user_message_formatted} chars)"
            )
        out["messages_formatted"] = messages_formatted

    messages = [
        ChatMessage(role=MessageRole.SYSTEM, content=system),
        ChatMessage(role=MessageRole.USER, content=user),
    ]

    # Determinism knobs (standard args stay top-level; vendor extras go in extra_body)
    seed_src = f"{text_id or ''}\n{user}"
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)

    vllm_extras: dict[str, Any] = {
        "seed": seed,
        "top_k": -1,
    }  # vendor-specific → extra_body

    if schema is not None:
        vllm_extras["guided_json"] = schema
        vllm_extras["guided_decoding_backend"] = "lm-format-enforcer"

    # Chat call (reasoning kept separate by server; final JSON is in message.content)
    resp = llm.chat(messages, extra_body=vllm_extras)

    response_content = getattr(resp.message, "content", "") or ""
    out["response_content"] = response_content

    if return_reasoning:
        # we need to get resp.raw.choices[0].message.reasoning_content,
        # but mypy doesn't permit it. so we:
        # 1: get resp.raw.choices[0]
        raw_first_choice = getattr(resp.raw, "choices", "")[0] or None
        # 2: get .message
        raw_message = getattr(raw_first_choice, "message", "") or None
        # 3: get .reasoning_content
        out["reasoning_content"] = getattr(raw_message, "reasoning_content", "") or None

    # Parse & validate (schema optional)
    try:
        data = json.loads(response_content)
        out["structured"] = data
        if schema is not None:
            validator_cls = validator_for(schema)
            validator_cls.check_schema(schema)
            validator = validator_cls(schema)
            validator.validate(data)
    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse JSON output for document {text_id}")
        out["error"] = f"JSONDecodeError: {str(e)}"
    except ValidationError as e:
        logger.warning(f"Failed to validate structured output for document {text_id}")
        out["error"] = f"ValidationError: {str(e)}"

    return out


def extract_from_text_lenient(text: str, text_id: str, **kwargs) -> dict:
    """Wrapper around extract_from_text that catches all exceptions.

    This is useful when processing multiple documents and we want to
    continue processing even if one document fails.

    Args:
        text: The text to process.
        text_id: Text identifier for logging.
        **kwargs: Keyword arguments for extract_from_text.
    Returns:
        A dictionary with keys "response_content" and "structured" or "error" in the case of failure.
    """

    try:
        return extract_from_text(text=text, text_id=text_id, **kwargs)
    except Exception as e:
        logger.error(f"Error processing document {text_id}: {e}")
        # needs to match the output of extract_from_text
        return {
            "response_content": None,
            "structured": None,
            "reasoning_content": None,
            "messages": None,
            "messages_formatted": None,
            "error": str(e),
        }
