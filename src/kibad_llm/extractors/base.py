from __future__ import annotations

from collections.abc import Mapping, MutableMapping
import dataclasses
import hashlib
import json
import logging
from typing import Any

from jsonschema.validators import validator_for

from kibad_llm.llms.base import LLM, MessageRole, SimpleChatMessage
from kibad_llm.schema.utils import (
    METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND,
    WRAPPED_CONTENT_KEY,
    build_schema_description,
    wrap_terminals_with_metadata,
)
from kibad_llm.utils.log import warn_once

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SingleExtractionResult(MutableMapping[str, Any]):
    """Dataclass to hold the result of a single extraction call. Acts like a TypedDict."""

    response_content: str | None = None
    structured: dict[str, Any] | list[Any] | None = None
    structured_with_metadata: dict[str, Any] | list[Any] | None = None
    reasoning_content: str | None = None
    messages: dict[str, str | None] | None = None
    messages_formatted: dict[str, str] | None = None
    error: str | None = None

    def __getitem__(self, key: str) -> Any:
        return dataclasses.asdict(self)[key]

    def __setitem__(self, key: str, value: Any) -> None:
        if key not in dataclasses.asdict(self):
            raise KeyError(f"Key '{key}' not found in SingleExtractionResult.")
        setattr(self, key, value)

    def __len__(self):
        return len(dataclasses.asdict(self))

    def __delitem__(self, key, /):
        raise NotImplementedError("Deletion of items is not supported in SingleExtractionResult.")

    def __iter__(self):
        return iter(dataclasses.asdict(self))


def exception2error_msg(e: Exception) -> str:
    """Convert an exception to a string with its type and message."""
    return f"{type(e).__name__}: {str(e)}"


def build_chat_message(
    message: str,
    role: MessageRole,
    document: str | None = None,
    document_placeholder: str = "document",
    schema: dict[str, Any] | None = None,
    schema_description_kwargs: dict[str, Any] | None = None,
    schema_description_placeholder: str = "schema_description",
) -> tuple[SimpleChatMessage, dict[str, bool]]:
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

    return SimpleChatMessage(role=role, content=content), {
        "has_schema_description": message_requires_schema_description,
        "has_document": message_requires_document,
    }


def build_chat_messages(
    system_message: str | None = None,
    user_message: str | None = None,
    schema_description_placeholder: str = "schema_description",
    document_placeholder: str = "document",
    schema: dict[str, Any] | None = None,
    history: list[SimpleChatMessage] | None = None,
    return_messages: bool = False,
    return_messages_formatted: bool = False,
    truncate_user_message_formatted: int | None = 300,
    _out: SingleExtractionResult | None = None,
    **build_messages_kwargs: Any,
) -> list[SimpleChatMessage]:
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


def strip_metadata(data: Any, *, content_key: str = "content") -> Any:
    """
    Strip metadata wrappers from a JSON-parsed result produced by `wrap_terminals_with_metadata`.

    The wrapped output encodes terminal values as objects like:
        {"<content_key>": <value>, "evidence_anchor": "...", ...}

    This function walks the parsed JSON (dict/list/scalars) and removes such wrappers by
    replacing the wrapper dict with its `<content_key>` value.

    Wrapper detection (heuristic):
      - a dict is treated as a wrapper if it has `content_key` AND at least one additional key.
        (We avoid unwrapping objects that only have `{"content": ...}`.)

    Notes:
      - This function does not validate that "other keys" are truly metadata. If your original
        extraction schema contains real objects that also have a `content_key` field and other
        fields, they may be unwrapped unintentionally. If that’s a concern, use a more unique
        `content_key` (e.g. "__content") in the schema wrapping step.
      - The input is not mutated; a transformed copy is returned.
    """

    def _is_wrapper_dict(d: Mapping[str, Any]) -> bool:
        return content_key in d and len(d) >= 2

    def _strip(node: Any) -> Any:
        if isinstance(node, list):
            return [_strip(x) for x in node]

        if isinstance(node, Mapping):
            # If this dict is a wrapper, discard metadata and recurse into the content.
            if _is_wrapper_dict(node):
                return _strip(node.get(content_key))

            # Otherwise recurse into all values.
            return {k: _strip(v) for k, v in node.items()}

        # scalars (str/int/float/bool/None)
        return node

    return _strip(data)


def extract_from_text(
    text: str,
    text_id: str,
    prompt_template: dict[str, str | None],
    schema: dict[str, Any] | None = None,
    use_guided_decoding: bool = True,
    validate_with_schema: bool = True,
    llm: LLM | None = None,
    request_parameters: dict[str, Any] | None = None,
    return_reasoning: bool = False,
    detect_evidence: bool = False,
    adjust_schema_for_detect_evidence: bool = False,
    adjust_schema_description_for_detect_evidence: bool = False,
    response_has_metadata: bool = False,
    # deprecated arguments
    user_message: str | None = None,
    system_message: str | None = None,
    schema_description_placeholder: str | None = None,
    document_placeholder: str | None = None,
    **build_messages_kwargs: Any,
) -> SingleExtractionResult:
    """Extract structured information from text using an LLM.

    Given a chat llm, composes system and user messages, and invokes the model.
    When a schema is provided, it is used to enforce guided decoding. The output
    is parsed as JSON and validated against the schema if provided.

    Args:
        text: The document text to process.
        text_id: Document text identifier for logging.
        prompt_template: A dictionary with at least one of 'system_message' and 'user_message'
            templates (or both).
        schema: Optional JSON schema for structured output.
        use_guided_decoding: Whether to use guided decoding.
        validate_with_schema: Whether to validate the output against the provided schema.
            IMPORTANT: Disabling validation may lead to invalid structured outputs and, thus,
            may break result serialization (since we use .map() and .to_json() from datasets).
        llm: The LLM model to use. Must be a chat model (i.e. is_chat_model=True) and support extra_body
            parameters for guided decoding if schema is provided. If None, no LLM call is made.
        request_parameters: Additional parameters to pass to the LLM chat call. If 'seed' is not provided,
            a seed is derived from the messages and added to request_parameters for determinism.
        return_reasoning: Whether to return the reasoning done by the model.
        detect_evidence: Shorthand to enable evidence detection via automatic schema adjustment
            (adjust_schema_for_detect_evidence=True) and expecting metadata in the response
            (see response_has_metadata=True). Per default, the schema description is constructed
            from the original schema, so it is recommended to adjust the prompt_template accordingly
            (e.g., by adding instructions about evidence). But see
            `adjust_schema_description_for_detect_evidence` to switch this behavior.
        adjust_schema_for_detect_evidence: Whether to adjust the schema to wrap terminal values
            with metadata. If True, the schema is modified so that each terminal value is replaced
            with an object containing the original value under the key `content` plus a metadata field
            `evidence_anchor` (a verbatim quote from the input text supporting the
            extracted content). Requires a schema to be provided.
        adjust_schema_description_for_detect_evidence: Whether to adjust the schema description
            when detect_evidence is True. If True, the schema description will mention that
            each value is accompanied by an evidence_anchor that is a "verbatim excerpt from the source
            text supporting the extracted content" (see METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND).
            Has only an effect if adjust_schema_for_detect_evidence is also True.
        response_has_metadata: If True, the output is expected to have each leaf value wrapped in
            an object with `content` plus metadata fields. If so, the metadata is stripped and the cleaned
            output is returned under the "structured" key, while the raw output with metadata is returned
            under the "structured_with_metadata" key.
        **build_messages_kwargs: Additional keyword arguments for build_chat_messages.

    Returns:
        A SingleExtractionResult object with the extraction result.
    """
    # setting the log level on every query is suboptimal, but the simplest solution in our current architecture
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if (
        system_message is not None
        or user_message is not None
        or schema_description_placeholder is not None
        or document_placeholder is not None
    ):
        # raise an error if deprecated arguments are used
        raise DeprecationWarning(
            "system_message, user_message, schema_description_placeholder, and document_placeholder "
            "are deprecated. Please provide a prompt_template dictionary containing 'system_message' and/or "
            "'user_message' (and optionally schema_description_placeholder and document_placeholder)"
            "instead."
        )
    build_messages_kwargs.update(prompt_template)

    out = SingleExtractionResult()

    original_schema = schema
    schema_for_build_messages = schema

    # shorthand for evidence detection
    if detect_evidence:
        if not use_guided_decoding:
            warn_once(
                "detect_evidence is True but use_guided_decoding is False. "
                "Enabling detect_evidence adjusts the schema for guided decoding, "
                "so it is recommended to enable use_guided_decoding as well."
            )
        adjust_schema_for_detect_evidence = True
        response_has_metadata = True

    if adjust_schema_for_detect_evidence:
        if schema is None:
            raise ValueError(
                "adjust_schema_for_detect_evidence is True but no schema provided to adjust."
            )
        schema = wrap_terminals_with_metadata(
            schema,
            metadata_schema=METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND,
            content_key=WRAPPED_CONTENT_KEY,
        )
        if adjust_schema_description_for_detect_evidence:
            schema_for_build_messages = schema

    messages = build_chat_messages(
        document=text,
        schema=schema_for_build_messages,
        _out=out,
        **build_messages_kwargs,
    )

    request_kwargs = request_parameters or {}

    if "seed" not in request_kwargs:
        # Determinism knob: derive seed from messages
        seed_src = str(messages)
        seed = int(hashlib.sha256(seed_src.encode("utf-8")).hexdigest()[:8], 16)
        request_kwargs["seed"] = seed

    if use_guided_decoding:
        if schema is None:
            raise ValueError(
                "use_guided_decoding is True but no json schema provided for guided decoding"
            )

    # only proceed if we have an llm
    if llm is not None:
        response_content = ""
        # Parse & validate (schema optional)
        try:
            # LLM chat call
            resp = llm.call_llm_chat_with_guided_decoding(
                messages=messages,
                json_schema=schema if use_guided_decoding else None,
                **request_kwargs,
            )

            if return_reasoning:
                out["reasoning_content"] = llm.get_reasoning_from_chat_response(response=resp)

            response_content = llm.get_response_content_from_chat_response(response=resp)
            out["response_content"] = response_content

            data = json.loads(response_content)
            if schema is not None and validate_with_schema:
                validator_cls = validator_for(schema)
                validator_cls.check_schema(schema)
                validator = validator_cls(schema)
                validator.validate(data)

            if response_has_metadata:
                out["structured_with_metadata"] = data
                data_without_metadata = strip_metadata(data, content_key=WRAPPED_CONTENT_KEY)
                # validate stripped version against original schema
                if validate_with_schema and original_schema is not None:
                    validator_cls = validator_for(original_schema)
                    validator_cls.check_schema(original_schema)
                    validator = validator_cls(original_schema)
                    validator.validate(data_without_metadata)
                data = data_without_metadata

            # just assign if we validated successfully
            out["structured"] = data

        except Exception as e:
            error_msg = exception2error_msg(e)
            logger.warning(
                f"Failed to process document {text_id}: {error_msg}, "
                f"response_content = '{response_content[:min(len(response_content), 1500)]}...'"
            )
            out["error"] = error_msg

    else:
        warn_once("No LLM provided for extraction, skipping LLM call.")

    return out


def extract_from_text_lenient(text: str, text_id: str, **kwargs) -> SingleExtractionResult:
    """Wrapper around extract_from_text that catches all exceptions.

    This is useful when processing multiple documents and we want to
    continue processing even if one document fails.

    Args:
        text: The text to process.
        text_id: Text identifier for logging.
        **kwargs: Keyword arguments for extract_from_text.
    Returns:
        A SingleExtractionResult object with the extraction result or error message.
    """

    try:
        return extract_from_text(text=text, text_id=text_id, **kwargs)
    except Exception as e:
        error_msg = exception2error_msg(e)
        logger.error(f"Error processing document {text_id}: {error_msg}")
        # needs to match the output of extract_from_text
        return SingleExtractionResult(error=error_msg)
