from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import logging
from typing import Any

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validator_for
from llama_index.core.llms import LLM, ChatMessage, MessageRole

from kibad_llm.schema.utils import build_schema_description

logger = logging.getLogger(__name__)


@lru_cache(maxsize=None)
def warn_once(msg: str) -> None:
    """Log a warning message only once by caching the function call."""
    logger.warning(f"{msg} (this message will only be shown once)")


def build_chat_message(
    text: str,
    message: str,
    role: MessageRole,
    schema_description_placeholder: str = "schema_description",
    text_placeholder: str = "document",
    schema: dict[str, Any] | None = None,
    schema_description_kwargs: dict[str, Any] | None = None,
) -> tuple[ChatMessage, dict[str, bool]]:
    """Build a single chat message by inserting text and schema description.

    Args:
        text: The text to process.
        message: The message template.
        role: The role of the message (e.g., system, user).
        schema: Optional JSON schema for structured output.
        schema_description_kwargs: Optional kwargs for build_schema_description when generating
            the schema description.
        schema_description_placeholder: The placeholder in the message template for the
            schema description. If the placeholder is present in the message template,
            the schema must be provided and the description will be generated and inserted.
        text_placeholder: The placeholder in the message template for the input text. If the
            placeholder is present in the message template, it will be replaced with the input text.

    Returns:
        A tuple of (ChatMessage, message_requires_schema_description, message_requires_document).
    """
    content = message

    # Check if schema description is needed. If so, generate it and insert it.
    message_requires_schema_description = f"{{{schema_description_placeholder}}}" in content
    if message_requires_schema_description:
        if schema is None:
            raise ValueError(
                f"Schema must be provided if {role.name} message template requires schema "
                f"description (it contains '{{{schema_description_placeholder}}}')."
            )
        schema_description = build_schema_description(
            schema=schema, **(schema_description_kwargs or {})
        )
        content = content.format(**{schema_description_placeholder: schema_description})
    else:
        if schema is not None:
            warn_once(
                f"Schema provided but {role.name} message template does not require schema description "
                f"(it does not contain '{{{schema_description_placeholder}}}')."
            )

    # Check if input text is needed and insert it.
    message_requires_document = "{" + text_placeholder + "}" in content
    if message_requires_document:
        content = content.format(**{text_placeholder: text})

    return ChatMessage(role=role, content=content), {
        "has_schema_description": message_requires_schema_description,
        "has_document": message_requires_document,
    }


def build_chat_messages(
    system_message: str,
    user_message: str,
    schema_description_placeholder: str = "schema_description",
    text_placeholder: str = "document",
    schema: dict[str, Any] | None = None,
    schema_description_kwargs: dict[str, Any] | None = None,
    use_guided_decoding: bool = True,
    guided_decoding_backend: str | None = "lm-format-enforcer",
    validate_with_schema: bool = True,
    llm: LLM | None = None,
    return_reasoning: bool = False,
    return_messages: bool = False,
    return_messages_formatted: bool = False,
    truncate_user_message_formatted: int | None = 300,
    _out: dict[str, Any] | None = None,
    **build_messages_kwargs: Any,
) -> list[ChatMessage]:
    """Build chat messages for extraction.

    Args:
        system_message: The system message template.
        user_message: The user message template.
        schema: Optional JSON schema for structured output.
        schema_description_placeholder: The placeholder in the message templates for the
            schema description. If the placeholder is present in the message templates,
            the schema must be provided and the description will be generated and inserted.
        text_placeholder: The placeholder in the message templates for the input text. If the
            placeholder is present in the message templates, it will be replaced with the input text.
        use_guided_decoding: Whether to use guided decoding.
        guided_decoding_backend: The backend to use for guided decoding.
        validate_with_schema: Whether to validate the output against the provided schema.
            IMPORTANT: Disabling validation may lead to invalid structured outputs and, thus,
            may break result serialization (since we use .map() and .to_json() from datasets).
        llm: The LLM model to use. Must be a chat model (i.e. is_chat_model=True) and support extra_body
            parameters for guided decoding if schema is provided. If None, no LLM call is made.
        return_reasoning: Whether to return the reasoning done by the model.
        return_messages: Whether to return the used prompt messages, but without input text and
            schema description.
        return_messages_formatted: Whether to return the used prompt messages formatted with
            input text and schema description.
        truncate_user_message_formatted: If return_messages_formatted is True, truncate the user message
            content to this many characters (to avoid huge outputs). Set to None to disable truncation.
        _out: Optional output dictionary to store messages in (used internally).
        **build_messages_kwargs: Additional keyword arguments for build_chat_message.

    Returns:
        A list of ChatMessage objects.
    """

    # return the prompt messages without input text and schema description
    if return_messages and _out is not None:
        _out["messages"] = {
            "system": system_message,
            "user": user_message,
        }

    system, sys_meta = build_chat_message(
        message=system_message,
        role=MessageRole.SYSTEM,
        schema=schema,
        schema_description_placeholder=schema_description_placeholder,
        text_placeholder=text_placeholder,
        **build_messages_kwargs,
    )
    user, user_meta = build_chat_message(
        message=user_message,
        role=MessageRole.USER,
        schema=schema,
        schema_description_placeholder=schema_description_placeholder,
        text_placeholder=text_placeholder,
        **build_messages_kwargs,
    )

    # Check if schema description is needed. If not, but schema is provided, warn.
    if (
        not sys_meta["has_schema_description"]
        and not user_meta["has_schema_description"]
        and schema is not None
    ):
        warn_once(
            "Schema provided but message templates do not require schema description "
            f"(they do not contain '{{{schema_description_placeholder}}}')."
        )

    # Check where the input text is needed and insert it. At least one message must require it.
    if not sys_meta["has_document"] and not user_meta["has_document"]:
        raise ValueError(
            "At least one of the message templates must require the input text "
            f"(they must contain '{{{text_placeholder}}}')."
        )

    # return the prompt messages with input text and schema description formatted in
    if return_messages_formatted and _out is not None:
        messages_formatted = {"system": system.content or "", "user": user.content or ""}
        if (
            truncate_user_message_formatted is not None
            and len(messages_formatted["user"]) > truncate_user_message_formatted
        ):
            messages_formatted["user"] = (
                f"{messages_formatted['user'][:truncate_user_message_formatted]}... "
                f"(truncated @ {truncate_user_message_formatted} chars)"
            )
        _out["messages_formatted"] = messages_formatted

    messages = [system, user]

    return messages


def extract_from_text(
    text: str,
    text_id: str,
    schema: dict[str, Any] | None = None,
    llm: LLM | None = None,
    return_reasoning: bool = False,
    **build_messages_kwargs: Any,
) -> dict:
    """Extract structured information from text using an LLM.

    Given a chat llm, composes system and user messages, and invokes the model.
    When a schema is provided, it is used to enforce guided decoding. The output
    is parsed as JSON and validated against the schema if provided.

    Args:
        text: The text to process.
        text_id: Text identifier for logging and seeding.
        schema: Optional JSON schema for structured output.
        llm: The LLM model to use. Must be a chat model (i.e. is_chat_model=True) and support extra_body
            parameters for guided decoding if schema is provided. If None, no LLM call is made.
        return_reasoning: Whether to return the reasoning done by the model.
        **build_messages_kwargs: Additional keyword arguments for build_chat_messages.

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

    messages = build_chat_messages(
        text=text,
        schema=schema,
        _out=out,
        **build_messages_kwargs,
    )

    # Determinism knobs (standard args stay top-level; vendor extras go in extra_body)
    seed_src = str(messages)
    seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)

    vllm_extras: dict[str, Any] = {
        "seed": seed,
        "top_k": -1,
    }  # vendor-specific → extra_body

    if use_guided_decoding:
        if schema is None:
            raise ValueError(
                "use_guided_decoding is True but no json schema provided for guided decoding"
            )
        vllm_extras["guided_json"] = schema
        if guided_decoding_backend is not None:
            vllm_extras["guided_decoding_backend"] = guided_decoding_backend

    # only proceed if we have an llm
    if llm is not None:
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
            if schema is not None and validate_with_schema:
                validator_cls = validator_for(schema)
                validator_cls.check_schema(schema)
                validator = validator_cls(schema)
                validator.validate(data)
            # just assign if we validated successfully
            out["structured"] = data
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON output for document {text_id}")
            out["error"] = f"JSONDecodeError: {str(e)}"
        except ValidationError as e:
            logger.warning(f"Failed to validate structured output for document {text_id}")
            out["error"] = f"ValidationError: {str(e)}"

    else:
        warn_once("No LLM provided for extraction, skipping LLM call.")

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
