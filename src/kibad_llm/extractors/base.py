from __future__ import annotations

from functools import lru_cache
import hashlib
import json
import logging
from typing import Any

from jsonschema.validators import validator_for
from llama_index.core.llms import LLM, ChatMessage, MessageRole

from kibad_llm.schema.utils import build_schema_description

logger = logging.getLogger(__name__)


class ReasoningContentNotFoundError(Exception):
    """Raised when the reasoning content is not found in the LLM response."""

    ...


class MissingResponseContentError(Exception):
    """Raised when the LLM response message has no content."""

    ...


class EmptyResponseMessageError(Exception):
    """Raised when the LLM response message is empty."""

    ...


def exception2error_msg(e: Exception) -> str:
    """Convert an exception to a string with its type and message."""
    return f"{type(e).__name__}: {str(e)}"


@lru_cache(maxsize=None)
def warn_once(msg: str) -> None:
    """Log a warning message only once by caching the function call."""
    logger.warning(f"{msg} (this message will only be shown once)")


def build_chat_message(
    message: str,
    role: MessageRole,
    document: str | None = None,
    document_placeholder: str = "document",
    schema: dict[str, Any] | None = None,
    schema_description_kwargs: dict[str, Any] | None = None,
    schema_description_placeholder: str = "schema_description",
) -> tuple[ChatMessage, dict[str, bool]]:
    """Build a single chat message by inserting text and schema description
    if respective placeholders are present in the message template.

    Args:
        message: The message template.
        role: The role of the message (e.g., system, user).
        document: The document text to process.
        document_placeholder: The placeholder in the message template for the input text. If the
            placeholder is present in the message template, it will be replaced with the input text.
        schema: Optional JSON schema for structured output.
        schema_description_kwargs: Optional kwargs for build_schema_description when generating
            the schema description.
        schema_description_placeholder: The placeholder in the message template for the
            schema description. If the placeholder is present in the message template,
            the schema must be provided and the description will be generated and inserted.

    Returns:
        A tuple of ChatMessage and a metadata dictionary indicating whether schema description
        and text were inserted.
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

    # Check if input document is needed and insert it.
    message_requires_document = "{" + document_placeholder + "}" in content
    if message_requires_document:
        if document is None:
            raise ValueError(
                f"Document text must be provided if {role.name} message template requires "
                f"input text (it contains '{{{document_placeholder}}}')."
            )
        content = content.format(**{document_placeholder: document})

    return ChatMessage(role=role, content=content), {
        "has_schema_description": message_requires_schema_description,
        "has_document": message_requires_document,
    }


def build_chat_messages(
    system_message: str | None = None,
    user_message: str | None = None,
    schema_description_placeholder: str = "schema_description",
    document_placeholder: str = "document",
    schema: dict[str, Any] | None = None,
    history: list[ChatMessage] | None = None,
    return_messages: bool = False,
    return_messages_formatted: bool = False,
    truncate_user_message_formatted: int | None = 300,
    _out: dict[str, Any] | None = None,
    **build_messages_kwargs: Any,
) -> list[ChatMessage]:
    """Build chat messages for extraction. The document text and schema description may be inserted
    into the message templates, depending on the presence of the respective placeholders.

    Args:
        system_message: The system message template.
        user_message: The user message template.
        schema: Optional JSON schema for structured output.
        schema_description_placeholder: The placeholder in the message templates for the
            schema description. If the placeholder is present in the message templates,
            the schema must be provided and the description will be generated and inserted.
        document_placeholder: The placeholder in the message templates for the input text. If the
            placeholder is present in the message templates, it will be replaced with the input text.
        history: Optional list of ChatMessage objects representing the conversation history.
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

    messages = []
    metas = []
    for msg_str, role in [
        (system_message, MessageRole.SYSTEM),
        (user_message, MessageRole.USER),
    ]:
        if msg_str is not None:
            msg, meta = build_chat_message(
                message=msg_str,
                role=role,
                schema=schema,
                schema_description_placeholder=schema_description_placeholder,
                document_placeholder=document_placeholder,
                **build_messages_kwargs,
            )
            messages.append(msg)
            metas.append(meta)

    if len(messages) == 0:
        raise ValueError("At least one of system_message or user_message must be provided.")

    # Check if schema description was inserted. At least one message must have it (if schema provided).
    if not any(meta["has_schema_description"] for meta in metas) and schema is not None:
        warn_once(
            "Schema provided but message templates do not require schema description "
            f"(they do not contain '{{{schema_description_placeholder}}}')."
        )

    # Check where the input document was inserted. At least one message must have it (if history is not used).
    if not any(meta["has_document"] for meta in metas) and not history:
        raise ValueError(
            "At least one of the message templates must require the input text "
            f"(they must contain '{{{document_placeholder}}}')."
        )

    # return the prompt messages with input text and schema description formatted in
    if return_messages_formatted and _out is not None:
        messages_formatted = {msg.role.name.lower(): msg.content or "" for msg in messages}
        if (
            truncate_user_message_formatted is not None
            and "user" in messages_formatted
            and len(messages_formatted["user"]) > truncate_user_message_formatted
        ):
            messages_formatted["user"] = (
                f"{messages_formatted['user'][:truncate_user_message_formatted]}... "
                f"(truncated @ {truncate_user_message_formatted} chars)"
            )
        _out["messages_formatted"] = messages_formatted

    if history:
        messages = history + messages
    return messages


def extract_from_text(
    text: str,
    text_id: str,
    schema: dict[str, Any] | None = None,
    use_guided_decoding: bool = True,
    validate_with_schema: bool = True,
    llm: LLM | None = None,
    extra_body: dict[str, Any] | None = None,
    return_reasoning: bool = False,
    **build_messages_kwargs: Any,
) -> dict:
    """Extract structured information from text using an LLM.

    Given a chat llm, composes system and user messages, and invokes the model.
    When a schema is provided, it is used to enforce guided decoding. The output
    is parsed as JSON and validated against the schema if provided.

    Args:
        text: The document text to process.
        text_id: Document text identifier for logging.
        schema: Optional JSON schema for structured output.
        use_guided_decoding: Whether to use guided decoding.
        validate_with_schema: Whether to validate the output against the provided schema.
            IMPORTANT: Disabling validation may lead to invalid structured outputs and, thus,
            may break result serialization (since we use .map() and .to_json() from datasets).
        llm: The LLM model to use. Must be a chat model (i.e. is_chat_model=True) and support extra_body
            parameters for guided decoding if schema is provided. If None, no LLM call is made.
        extra_body: Additional parameters to pass to the LLM chat call. If 'seed' is not provided,
            a seed is derived from the messages and added to extra_body for determinism.
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
        document=text,
        schema=schema,
        _out=out,
        **build_messages_kwargs,
    )

    extra_body = extra_body or {}

    if "seed" not in extra_body:
        # Determinism knob: derive seed from messages
        seed_src = str(messages)
        seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)
        extra_body["seed"] = seed

    if use_guided_decoding:
        if schema is None:
            raise ValueError(
                "use_guided_decoding is True but no json schema provided for guided decoding"
            )
        extra_body["structured_outputs"] = {"json": schema}

    # only proceed if we have an llm
    if llm is not None:

        # Parse & validate (schema optional)
        try:
            # Chat call (reasoning kept separate by server; final JSON is in message.content)
            resp = llm.chat(messages, extra_body=extra_body)

            if return_reasoning:
                try:
                    # we need to get resp.raw.choices[0].message.reasoning_content,
                    # but mypy doesn't permit it. so we:
                    # 1: get resp.raw.choices[0] (may raise AttributeError or IndexError)
                    raw_first_choice = getattr(resp.raw, "choices")[0]
                    # 2: get .message (may raise AttributeError)
                    raw_message = getattr(raw_first_choice, "message")
                    # 3: get .reasoning_content (may raise AttributeError)
                    out["reasoning_content"] = getattr(raw_message, "reasoning_content")
                except (AttributeError, IndexError) as e:
                    raise ReasoningContentNotFoundError(
                        f"Failed to extract reasoning content: {str(e)}"
                    ) from e

            response_content = resp.message.content
            if response_content is None:
                raise MissingResponseContentError("LLM response is missing content.")
            if not response_content.strip():
                raise EmptyResponseMessageError("LLM returned an empty message.")
            out["response_content"] = response_content

            data = json.loads(response_content)
            if schema is not None and validate_with_schema:
                validator_cls = validator_for(schema)
                validator_cls.check_schema(schema)
                validator = validator_cls(schema)
                validator.validate(data)
            # just assign if we validated successfully
            out["structured"] = data

        except Exception as e:
            error_msg = exception2error_msg(e)
            logger.warning(f"Failed to process document {text_id}: {error_msg}")
            out["error"] = error_msg

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
        error_msg = exception2error_msg(e)
        logger.error(f"Error processing document {text_id}: {error_msg}")
        # needs to match the output of extract_from_text
        return {
            "response_content": None,
            "structured": None,
            "reasoning_content": None,
            "messages": None,
            "messages_formatted": None,
            "error": error_msg,
        }
