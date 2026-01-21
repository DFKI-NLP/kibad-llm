from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping
import dataclasses
from dataclasses import field
from functools import partial
import json
import logging
import re
import traceback
from typing import Any

from jsonschema.validators import validator_for
from llama_index.core.base.llms.types import ChatResponse

from kibad_llm.llms.base import LLM, MessageRole, SimpleChatMessage
from kibad_llm.schema.utils import (
    WRAPPED_CONTENT_KEY,
    build_schema_description,
    wrap_terminals_with_metadata,
)
from kibad_llm.utils.dictionary import FieldDict
from kibad_llm.utils.log import warn_once

logger = logging.getLogger(__name__)


@dataclasses.dataclass
class SingleExtractionResult(FieldDict):
    response_content: str | None = None
    structured: dict[str, Any] | list[Any] | None = None
    structured_with_metadata: dict[str, Any] | list[Any] | None = None
    reasoning_content: str | None = None
    messages: dict[str, str | None] | None = None
    messages_formatted: dict[str, str] | None = None
    errors: list[str] = field(default_factory=list)


def exception2error_msg(e: BaseException) -> str:
    """Return full traceback for the given exception."""
    e_with_traceback = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    return f"{type(e).__name__}: {e_with_traceback}"


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


def _is_wrapper_dict(d: Mapping[str, Any], content_key: str) -> bool:
    """Heuristic to detect whether a dict is a metadata wrapper around content."""
    return content_key in d and len(d) >= 2


def strip_metadata(data: Any, *, content_key: str) -> Any:
    """
    Strip metadata wrappers from a JSON-parsed result produced by `wrap_terminals_with_metadata`.

    The wrapped output encodes terminal values as objects like:
        {"<content_key>": <value>, "evidence_anchor": "...", ...}

    This function walks the parsed JSON (dict/list/scalars) and removes such wrappers by
    replacing the wrapper dict with its `<content_key>` value.

    Wrapper detection (heuristic):
      - a dict is treated as a wrapper if it has `content_key` AND at least one additional key.
        (We avoid unwrapping objects that only have `{"<content_key>": ...}`.)

    Notes:
      - This function does not validate that "other keys" are truly metadata. If your original
        extraction schema contains real objects that also have a `content_key` field and other
        fields, they may be unwrapped unintentionally. If that’s a concern, use a more unique
        `content_key` (e.g. "__content") in the schema wrapping step.
      - The input is not mutated; a transformed copy is returned.
    """

    def _strip(node: Any) -> Any:
        if isinstance(node, list):
            return [_strip(x) for x in node]

        if isinstance(node, Mapping):
            # If this dict is a wrapper, discard metadata and recurse into the content.
            if _is_wrapper_dict(d=node, content_key=content_key):
                return _strip(node.get(content_key))

            # Otherwise recurse into all values.
            return {k: _strip(v) for k, v in node.items()}

        # scalars (str/int/float/bool/None)
        return node

    return _strip(data)


def _snippet_for_span(
    start: int,
    end: int,
    text: str,
    token_spans: list[tuple[int, int]],
    token_margin: int = 5,
) -> str:
    """Extract a text snippet from `text` that spans `start` to `end` character offsets,
    extending `token_margin` tokens before and after the span.
    """
    if not token_spans:
        return ""

    # First token whose end is after the start (covers overlap/inside-token cases)
    start_i = None
    for i, (_s, e) in enumerate(token_spans):
        if e > start:
            start_i = i
            break
    if start_i is None:
        return ""

    # Last token whose start is before the end
    end_i = None
    for i in range(len(token_spans) - 1, -1, -1):
        s, _e = token_spans[i]
        if s < end:
            end_i = i
            break
    if end_i is None:
        return ""

    lo = max(0, start_i - token_margin)
    hi = min(len(token_spans) - 1, end_i + token_margin)

    # Slice original text to preserve whitespace exactly (including newlines, multiple spaces, etc.)
    snippet_start = token_spans[lo][0]
    snippet_end = token_spans[hi][1]
    return text[snippet_start:snippet_end]


def _strip_wrapping_quotes(s: str) -> str:
    """Strip common wrapping quotes from the beginning and end of a string."""
    # Common quote pairs: ASCII, German/typographic, and apostrophe-like quotes
    quote_pairs = [
        ('"', '"'),
        ("'", "'"),
        ("`", "`"),
        ("“", "”"),
        ("„", "“"),
        ("„", "”"),
        ("‘", "’"),
        ("‚", "‘"),
        ("«", "»"),
        ("‹", "›"),
    ]

    s2 = s.strip()
    for left, right in quote_pairs:
        if len(s2) >= 2 and s2.startswith(left) and s2.endswith(right):
            return s2[1:-1].strip()
    return s2


def _find_anchor_match_spans(text: str, anchor: str) -> list[tuple[int, int]]:
    """
    Find all character spans in `text` that match the given `anchor` string.
    The matching is whitespace-insensitive, meaning that any whitespace in the anchor
    can match any whitespace in the text (including different kinds of whitespace).
    Args:
        text: The original text to search within.
        anchor: The anchor string to search for.
    Returns:
        A list of (start_offset_in_text, end_offset_in_text) tuples for each match of the anchor.
    """

    # Preprocess anchor: strip wrapping quotes
    anchor = _strip_wrapping_quotes(anchor)

    # Guard: only search for non-empty string anchors.
    if not anchor:
        return []

    # Split the anchor on any whitespace. This lets us treat " " vs "\n" (or multiple spaces/tabs)
    # as equivalent when searching in the original text.
    # Example: "foo bar\nbaz" -> ["foo", "bar", "baz"]
    parts = re.split(r"\s+", anchor.strip())

    # If the anchor was only whitespace (or otherwise produced no meaningful parts), give up.
    if not parts or not any(parts):
        return []

    # Build a regex that matches the non-whitespace chunks in order, allowing *any* whitespace
    # between them in the text. We escape each chunk to avoid regex metacharacters being treated
    # specially (e.g., "." in the anchor should match a literal dot).
    # Example parts ["foo","bar"] -> pattern "foo\\s+bar"
    pattern = r"\s+".join(re.escape(p) for p in parts if p)

    # Find all non-overlapping matches of that pattern in the text and return their character spans.
    # Each span is (start_offset_in_text, end_offset_in_text).
    return [(m.start(), m.end()) for m in re.finditer(pattern, text)]


def augment_metadata_node_with_evidence(
    node: Mapping[str, Any],
    text: str,
    token_spans: list[tuple[int, int]],
    *,
    anchor_key: str = "evidence_anchor",
    num_matches_key: str = "evidence_num_matches",
    start_key: str = "first_evidence_start",
    end_key: str = "first_evidence_end",
    snippet_key: str = "first_evidence_snippet",
    snippet_margin: int = 10,
) -> dict[str, Any]:
    """
    Augment a single metadata wrapper dict with evidence location information.

    Given a wrapper object like:
        {"content": ..., "evidence_anchor": "...", ...}

    this function searches `text` for the anchor (via `_find_anchor_match_spans`). If at least
    one match is found, it adds:
      - `num_matches_key`: number of matches
      - `start_key` / `end_key`: character offsets of the first match
      - `snippet_key`: a substring of `text` spanning `snippet_margin` tokens around the match
        (whitespace preserved)

    If no anchor is present (or no matches exist), the wrapper is returned unchanged except for
    `num_matches_key` (only added when an anchor is a non-empty string).

    Args:
        node: The metadata wrapper dict to augment.
        text: The original text to search for evidence anchors.
        token_spans: Precomputed list of (start_offset, end_offset) tuples for each token in `text`.
        anchor_key: The key in wrapper dicts that holds the evidence anchor text.
        num_matches_key: The key to add for the number of matches of the anchor in the text.
        start_key: The key to add for the start character offset of the anchor.
        end_key: The key to add for the end character offset of the anchor.
        snippet_key: The key to add for the evidence snippet text.
        snippet_margin: Number of tokens to include before and after the anchor span
            in the snippet.
    Returns:
        The augmented metadata wrapper dict with evidence metadata added where applicable.
    """
    if snippet_margin < 0:
        raise ValueError("evidence snippet_margin must be >= 0")

    out: dict[str, Any] = dict(node)

    # do we have a non-empty evidence anchor?
    anchor = node.get(anchor_key)
    if isinstance(anchor, str) and anchor:
        anchor_matches = _find_anchor_match_spans(text=text, anchor=anchor)
        out[num_matches_key] = len(anchor_matches)
        if len(anchor_matches) > 0:
            # just take the first match
            start, end = anchor_matches[0]
            out[start_key] = start
            out[end_key] = end
            out[snippet_key] = _snippet_for_span(
                start,
                end,
                text=text,
                token_spans=token_spans,
                token_margin=snippet_margin,
            )

    return out


def augment_metadata(
    data: Any,
    *,
    text: str,
    content_key: str,
    **kwargs: Any,
) -> Any:
    """
    Recursively augment all metadata wrapper dicts in a JSON-parsed result with evidence info.

    Traversal:
      - walks `data` through nested dicts/lists
      - detects wrapper dicts via `_is_wrapper_dict(..., content_key=...)`
      - for each wrapper dict, calls `augment_metadata_node_with_evidence(...)`

    Keyword arguments:
      - kwargs are namespaced by prefix. Currently supported:
          * evidence_*  -> forwarded to `augment_metadata_node_with_evidence` (prefix stripped)
        Example: evidence_snippet_margin=10 sets `snippet_margin=10` for evidence augmentation.
      - unknown kwargs raise ValueError (fail fast).

    The returned structure mirrors the input but includes added evidence fields where applicable.
    """

    # split augmentation kwargs into those for evidence and others (future use)
    augmentation_kwargs: dict[str, dict[str, Any]] = defaultdict(dict)
    for k in list(kwargs.keys()):
        for prefix in ["evidence"]:
            if k.startswith(f"{prefix}_"):
                k_without_prefix = k[len(f"{prefix}_") :]
                augmentation_kwargs[prefix][k_without_prefix] = kwargs.pop(k)

    if len(kwargs) > 0:
        raise ValueError(f"Unknown augmentation kwargs: {list(kwargs.keys())}")

    # Precompute whitespace-token spans once for fast snippet lookup
    token_matches = list(re.finditer(r"\S+", text))
    token_spans = [(m.start(), m.end()) for m in token_matches]

    def _augment(node: Any) -> Any:
        if isinstance(node, list):
            return [_augment(x) for x in node]

        if isinstance(node, Mapping):
            # Recurse first (pure functional style)
            out: dict[str, Any] = {k: _augment(v) for k, v in node.items()}

            if _is_wrapper_dict(d=node, content_key=content_key):
                out = augment_metadata_node_with_evidence(
                    node=out,
                    text=text,
                    token_spans=token_spans,
                    **augmentation_kwargs.get("evidence", {}),
                )
            return out

        return node

    return _augment(data)


def add_response_content_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    llm: LLM,
) -> None:
    """Add `response_content` to output dictionary."""
    out.response_content = llm.get_response_content_from_chat_response(response=response)


def add_reasoning_content_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    llm: LLM,
) -> None:
    """Add `reasoning_content` to output dictionary."""
    out.reasoning_content = llm.get_reasoning_from_chat_response(response=response)


def add_structured_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    schema: dict[str, Any] | None,
    validate_with_schema: bool,
) -> None:
    """Add `structured` output to output dictionary based on response content."""
    # no-op if response content is None
    if out.response_content is not None:
        parsed = json.loads(out.response_content)
        if validate_with_schema and schema is not None:
            validator_cls = validator_for(schema)
            validator = validator_cls(schema)
            validator.validate(parsed)
        # set structured output just after successful validation so that the format is guaranteed
        # when validate_with_schema is True
        out.structured = parsed


def augment_and_strip_metadata_from_structured_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    schema: dict[str, Any] | None,
    original_schema: dict[str, Any] | None,
    text: str,
    validate_with_schema: bool,
    augment_metadata_kwargs: dict[str, Any] | None = None,
) -> None:
    """Augment metadata in `structured` output and save it as `structured_with_metadata`.
    Then, strip metadata and save the cleaned version back to `structured`.
    """
    # no-op if structured is None
    if out.structured is not None:

        # store original as structured_with_metadata and clear the structured field so
        # we don't accidentally use it later on
        structured_with_metadata = out.structured
        out.structured = None

        # augment metadata
        out.structured_with_metadata = augment_metadata(
            structured_with_metadata,
            text=text,
            content_key=WRAPPED_CONTENT_KEY,
            **(augment_metadata_kwargs or {}),
        )

        # strip metadata to get cleaned version
        structured = strip_metadata(out.structured_with_metadata, content_key=WRAPPED_CONTENT_KEY)

        # validate stripped version against original schema (if schema is not the original one)
        if validate_with_schema and original_schema is not None and schema != original_schema:
            validator_cls = validator_for(original_schema)
            validator_cls.check_schema(original_schema)
            validator = validator_cls(original_schema)
            validator.validate(structured)

        # set structured output just after successful validation so that the format is guaranteed
        # when validate_with_schema is True
        out.structured = structured


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
    adjust_schema_for_evidence_detection: bool = False,
    adjust_schema_description_for_evidence_detection: bool = False,
    evidence_anchor_description: str = "Verbatim excerpt from the source text supporting the extracted content.",
    wrapped_content_description: str | None = None,
    response_has_metadata: bool = False,
    augment_metadata_kwargs: dict[str, Any] | None = None,
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
        request_parameters: Additional parameters to pass to the LLM chat call.
        return_reasoning: Whether to return the reasoning done by the model.
        adjust_schema_for_evidence_detection: Whether to adjust the schema to wrap terminal values
            with metadata. If True, the schema is modified so that each terminal value is replaced
            with an object containing the original value under the key `content` plus a metadata field
            `evidence_anchor` (a verbatim quote from the input text supporting the
            extracted content). Requires a schema to be provided.
            Per default, the schema description is constructed from the original schema, so it is
            recommended to adjust the prompt_template accordingly (e.g., by adding instructions about
            evidence). But see `adjust_schema_description_for_detect_evidence` to switch this behavior.
        adjust_schema_description_for_evidence_detection: Whether to adjust the schema description
            when detect_evidence is True. If True, the schema description will mention that
            each value is accompanied by an evidence_anchor that is a "verbatim excerpt from the source
            text supporting the extracted content" (see METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND).
            Has only an effect if adjust_schema_for_detect_evidence is also True.
        evidence_anchor_description: Description for the evidence anchor field.
        wrapped_content_description: Optional description for the content field in the metadata wrapper.
        response_has_metadata: If True, the output is expected to have each leaf value wrapped in
            an object with `content` plus metadata fields. If so, the metadata is stripped and the cleaned
            output is returned under the "structured" key, while the raw output with metadata is returned
            under the "structured_with_metadata" key.
        augment_metadata_kwargs: Additional keyword arguments for augment_metadata.
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

    if adjust_schema_for_evidence_detection:
        if schema is None:
            raise ValueError(
                "adjust_schema_for_detect_evidence is True but no schema provided to adjust."
            )
        if not use_guided_decoding:
            warn_once(
                "adjust_schema_for_evidence_detection is True but use_guided_decoding is False. "
                "Enabling adjust_schema_for_evidence_detection adjusts the schema for guided decoding, "
                "so it is recommended to enable use_guided_decoding as well."
            )
        schema = wrap_terminals_with_metadata(
            schema,
            metadata_schema={
                "evidence_anchor": {
                    "type": "string",
                    "description": evidence_anchor_description,
                }
            },
            content_key=WRAPPED_CONTENT_KEY,
            content_description=wrapped_content_description,
        )
        # since we wrapped terminals with metadata, we expect metadata in the response
        response_has_metadata = True

        if adjust_schema_description_for_evidence_detection:
            schema_for_build_messages = schema

    messages = build_chat_messages(
        document=text,
        schema=schema_for_build_messages,
        _out=out,
        **build_messages_kwargs,
    )

    request_kwargs = request_parameters or {}

    if use_guided_decoding:
        if schema is None:
            raise ValueError(
                "use_guided_decoding is True but no json schema provided for guided decoding"
            )

    # only proceed if we have an llm
    if llm is not None:
        # setup postprocessing callbacks
        postprocessing_callbacks: list[Callable[[SingleExtractionResult, ChatResponse], None]] = []
        # 1) get response content
        postprocessing_callbacks.append(partial(add_response_content_callback, llm=llm))
        # 2) get reasoning if requested
        if return_reasoning:
            postprocessing_callbacks.append(partial(add_reasoning_content_callback, llm=llm))
        # 3) get structured output
        postprocessing_callbacks.append(
            partial(
                add_structured_callback, schema=schema, validate_with_schema=validate_with_schema
            )
        )
        # 4) handle structured with metadata if requested
        if response_has_metadata:
            postprocessing_callbacks.append(
                partial(
                    augment_and_strip_metadata_from_structured_callback,
                    schema=schema,
                    original_schema=original_schema,
                    text=text,
                    validate_with_schema=validate_with_schema,
                    augment_metadata_kwargs=augment_metadata_kwargs,
                )
            )

        # LLM chat call
        resp = llm.call_llm_chat_with_guided_decoding(
            messages=messages,
            json_schema=schema if use_guided_decoding else None,
            **request_kwargs,
        )

        # postprocessing: call each callback in order, but proceed if one fails
        for callback in postprocessing_callbacks:
            try:
                callback(out, resp)
            except Exception as e:
                error_msg = exception2error_msg(e)
                error_msg_flat = re.sub(r"\s+", " ", error_msg)
                show_msg = f"Failed to process document {text_id}: {error_msg_flat}"
                # if we have response content, include a snippet for better debugging
                if out.response_content is not None:
                    show_msg += f", response_content = '{out.response_content[:1500]}...'"
                out["errors"].append(error_msg)

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
        error_msg_flat = re.sub(r"\s+", " ", error_msg)
        logger.error(f"Error processing document {text_id}: {error_msg_flat}")
        return SingleExtractionResult(errors=[error_msg])
