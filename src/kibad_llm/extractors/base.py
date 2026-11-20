"""Core extraction function and supporting types for LLM-based structured extraction.

Classes:
    SingleExtractionResult: Result container for a single extraction call.
    TextOffsetValueError: Raised when character offset arguments are invalid.

Functions:
    extract_from_text: Extract structured output from text using an LLM.
    extract_from_text_lenient: Wrapper around [`extract_from_text`][.extract_from_text]
        that catches and records all exceptions instead of raising.
    strip_metadata: Strip metadata wrappers from a JSON-parsed result.
    augment_metadata: Recursively augment metadata wrapper dicts.
        Uses just [`augment_metadata_node_with_evidence`][.augment_metadata_node_with_evidence] for now.
    augment_metadata_node_with_evidence: Augment a single metadata wrapper dict with
        evidence location info.
    add_response_content_callback: Postprocessing callback to add response content to output.
    add_reasoning_content_callback: Postprocessing callback to add reasoning content to output.
    add_backend_metadata_callback: Postprocessing callback to preserve backend token usage.
    add_structured_callback: Postprocessing callback to parse and validate structured output.
    augment_and_strip_metadata_from_structured_callback: Postprocessing callback to augment
        metadata and strip it from structured output.
    exception2error_msg: Format an exception into short and long error message strings.
    check_utf8_encodable: Recursively check that all nested strings can be encoded to UTF-8.
"""

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

from kibad_llm.llms.base import LLM, prepare_request
from kibad_llm.llms.request import (
    SYSTEM_MESSAGE_KEY,
    USER_MESSAGE_KEY,
    SimpleChatMessage,
)
from kibad_llm.schema.utils import (
    WRAPPED_CONTENT_KEY,
    wrap_terminals_with_metadata,
)
from kibad_llm.utils.dictionary import FieldDict
from kibad_llm.utils.log import warn_once

logger = logging.getLogger(__name__)


class TextOffsetValueError(ValueError):
    """Raised when text offset is invalid."""

    pass


@dataclasses.dataclass
class SingleExtractionResult(FieldDict):
    """Stores one extraction result

    Attributes:
        character_start: Start index of the chunk of text that has been processed
        character_end: End index of the chunk of text that has been processed (exclusive)
        response_content: Response formatted as json
        structured: Parsed version of response_content. Possibly validated against a schema. - Internally may come with metadata.
        structured_with_metadata: Parsed version of response_content, with enriched metadata.
        reasoning_content: The LLMs reasoning output, as parsed by the api endpoint.
            (Usually output between <think> and </think> tokens)
        messages: Configured system and user templates before formatting.
        messages_formatted: Rendered messages in the current turn, keyed by role.
        errors: list of strings "error_name: error_message"
        errors_long: list of strings "error_name: error_message_and_traceback"
        backend_metadata: Backend-reported token usage for this call, or None if unavailable.
    """

    character_start: int
    character_end: int
    response_content: str | None = None
    structured: dict[str, Any] | list[Any] | None = None
    structured_with_metadata: dict[str, Any] | list[Any] | None = None
    reasoning_content: str | None = None
    messages: dict[str, str | None] | None = None
    messages_formatted: dict[str, str] | None = None
    errors: list[str] = field(default_factory=list)
    errors_long: list[str] = field(default_factory=list)
    backend_metadata: dict[str, Any] | None = None


def exception2error_msg(e: BaseException) -> tuple[str, str]:
    """Return short and long (including traceback) error messages for an exception.

    Args:
        e: Python exception object

    Returns:
        Tuple containing a short and a long version of the exception.
        The short version has the exception name and message,
        whilst the long version also comes with the entire traceback.

    """
    e_with_traceback = "".join(traceback.format_exception(type(e), e, e.__traceback__))
    return (
        f"{type(e).__name__}: {str(e)}",
        f"{type(e).__name__}: {e_with_traceback}",
    )


def check_utf8_encodable(data: Any) -> None:
    """Recursively check that every string in `data` can be encoded to UTF-8.

    Walks nested dicts/lists/tuples and encodes every string leaf. A lone (unpaired)
    surrogate is valid in a Python `str` but cannot be encoded to UTF-8, which is
    the reason `datasets`/`pyarrow` crash with an unhandled `UnicodeEncodeError`
    when writing out a batch that contains one. Encoding here, right when the
    offending string is produced, lets us attribute the failure to a single
    document instead of losing an entire batch's results.

    Args:
        data: Arbitrary nested data (e.g. a `SingleExtractionResult`) to check.

    Raises:
        UnicodeEncodeError: If any string in `data` cannot be encoded to UTF-8.
    """
    if isinstance(data, str):
        try:
            data.encode("utf-8")
        except UnicodeEncodeError as e:
            raise UnicodeEncodeError(
                e.encoding,
                e.object,
                e.start,
                e.end,
                f"{e.reason} (string: {repr(data)})",
            ) from e
    elif isinstance(data, Mapping):
        for value in data.values():
            check_utf8_encodable(value)
    elif isinstance(data, (list, tuple)):
        for value in data:
            check_utf8_encodable(value)


def _is_wrapper_dict(d: Mapping[str, Any], content_key: str) -> bool:
    """Heuristic to detect whether a dict is a metadata wrapper around content.

    Args:
        d: Dict to determine whether it is a metadata wrapper.
        content_key: String to check for whether its a key d.

    Returns:
        Whether d is a metadata wrapper.
    """
    return content_key in d and len(d) >= 2


def strip_metadata(data: Any, *, content_key: str) -> Any:
    """Strip metadata wrappers from a JSON-parsed result produced by `wrap_terminals_with_metadata`.

    The wrapped output encodes terminal values as objects like:
        `{"<content_key>": <value>, "evidence_anchor": "...", ...}`

    This function walks the parsed JSON (dict/list/scalars) and removes such wrappers by
    replacing the wrapper dict with its `<content_key>` value.

    Args:
        data: Parsed JSON with metadata wrappers.
        content_key: Key whose metadata wrappers to remove. - must be passed by keyword

    Returns:
        Parsed JSON without metadata wrappers around content_key.

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

    Args:
        start: Character index to get first token whose end is after the `start`.
        end: Character index to get last token whose start is before the `end`.
        text: Full text, from which the snippet is to be extracted.
        token_spans: Maps from tuple index to character boundaries of tokens.
        token_margin: Number of tokens of context to pad the snippet with.

    Returns:
        Text snippet with context padding.
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
    """Strip common wrapping quotes from the beginning and end of a string.

    Args:
        s: Text to strip wrapping quotes of.

    Returns:
        Text with the quotes stripped.
    """
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
    """Find all character spans in `text` that match the given `anchor` string.
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
    character_offset: int = 0,
) -> dict[str, Any]:
    """Augment a single metadata wrapper dict with evidence location information.

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
        character_offset: An optional offset to add to the start/end character positions
            (useful if the text is a chunk of a larger document).

    Returns:
        The augmented metadata wrapper dict with evidence metadata added where applicable.

    Raises:
        ValueError: If the snippet_margin is negative.
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
            out[start_key] = start + character_offset
            out[end_key] = end + character_offset
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
    """Recursively augment all metadata wrapper dicts in a JSON-parsed result.

    Currently, this does the following node processing:
    - evidence anchor handling using [augment_metadata_node_with_evidence][..augment_metadata_node_with_evidence]

    Traversal:
      - walks `data` through nested dicts/lists
      - detects wrapper dicts via `_is_wrapper_dict(..., content_key=...)`
      - for each wrapper dict, calls metadata node augmentation methods

    Args:
        data: JSON-parsed result with metadata
        text: Original input text to extract further information from - must be passed by keyword
        content_key: Key that must be in a mapping for it to be a wrapper_dict - must be passed by keyword

    Keyword Args:
        evidence_ (Any): `* evidence_*` -> forwarded to `augment_metadata_node_with_evidence` (prefix stripped)

    Keyword Args Notes:
      - kwargs are namespaced by prefix.
        Example: evidence_snippet_margin=10 sets `snippet_margin=10` for evidence augmentation.

    Returns:
        The data with the augmented metadata.
        The returned structure mirrors the input but includes added metadata fields where applicable.

    Raises:
      ValueError: unknown kwargs raise ValueError (fail fast).
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


def add_backend_metadata_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    llm: LLM,
) -> None:
    """Preserve backend metadata independently of response parsing and validation.

    Args:
        out: Extraction result to update in place.
        response: Response from the chat call.
        llm: Backend that extracts its metadata from the response.
    """
    out.backend_metadata = llm.get_backend_metadata_from_chat_response(response)


def add_response_content_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    llm: LLM,
) -> None:
    """Add `response_content` to output dictionary.

    Modifies `out` in place; does not return a value.

    Args:
        out: SingleExtractionResult to store the response_content in.
        response: ChatResponse that contains the response_content.
        llm: LLM object that extracts the response_content from response. - must be passed by keyword
    """
    out.response_content = llm.get_response_content_from_chat_response(response=response)


def add_reasoning_content_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    llm: LLM,
) -> None:
    """Add `reasoning_content` to output dictionary.

    Modifies `out` in place; does not return a value.

    Args:
        out: SingleExtractionResult to store the reasoning_content in.
        response: ChatResponse that contains the reasoning_content.
        llm: LLM object that extracts the reasoning_content from response. - must be passed by keyword
    """
    out.reasoning_content = llm.get_reasoning_from_chat_response(response=response)


def add_structured_callback(
    out: SingleExtractionResult,
    response: ChatResponse,
    *,
    schema: dict[str, Any] | None,
    validate_with_schema: bool,
) -> None:
    """Add `structured` output to output dictionary based on response content.

    Modifies `out` in place; does not return a value.
    This structured output may or may not contain metadata to some extent.

    Args:
        out: SingleExtractionResult to store the structured output in.
        response: Raw ChatResponse from the LLM call. - This exists for compatibility reasons and is not used here.
        schema: Schema to validate the response against. - must be passed by keyword
        validate_with_schema: Whether to validate response against schema. - must be passed by keyword
    """
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

    Modifies `out` in place; does not return a value.

    Args:
        out: An extraction result with `out.structured` populated with metadata
        response: Placeholder, because it gets passed to all functions in `postprocessing_callbacks`,
            but this one doesn't use it.
        schema: schema used in [`..extract_from_text`][] - may be modified for metadata - used to check against
            original_schema - must be passed by keyword
        original_schema: original schema that was passed to [`..extract_from_text`][] - without metadata - must be
            passed by keyword
        text: Original input text for information extraction - must be passed by keyword
        validate_with_schema: Whether to validate `out.structured` against the `original_schema` - must be passed by
            keyword
        augment_metadata_kwargs: Refer to [`..augment_metadata`][] - must be passed by keyword

    Warning:
        requires `out` to have `structured`, so run [`..add_structured_callback`][] first
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
    prompt_template: dict[str, Any],
    schema: dict[str, Any] | None = None,
    use_guided_decoding: bool = True,
    validate_with_schema: bool = True,
    llm: LLM | None = None,
    request_parameters: dict[str, Any] | None = None,
    return_reasoning: bool = False,
    include_evidence: bool = False,
    use_wrapped_schema_in_prompt: bool | None = None,
    evidence_anchor_description: str = "Verbatim excerpt from the source text supporting the extracted content.",
    wrapped_content_description: str | None = None,
    evidence_before_content: bool = False,
    response_has_metadata: bool = False,
    augment_metadata_kwargs: dict[str, Any] | None = None,
    character_start: int = 0,
    character_end: int | None = None,
    *,
    include_confidence: bool = False,
    confidence_description: str = "Integer from 1 (weak support) to 5 (explicit support).",
    history: list[SimpleChatMessage] | None = None,
    return_messages: bool = False,
    return_messages_formatted: bool = False,
    truncate_user_message_formatted: int | None = 300,
    adjust_schema_for_evidence_detection: bool | None = None,
    adjust_schema_description_for_evidence_detection: bool | None = None,
) -> SingleExtractionResult:
    """Extract structured information from text using an LLM.

    Given a chat llm, composes system and user messages, and invokes the model.
    When a schema is provided, it is used to enforce guided decoding. The output
    is parsed as JSON and validated against the schema if provided.

    Args:
        text: The document text to process.
        text_id: Document text identifier for logging.
        prompt_template: At least one of `system_message` and `user_message`, plus
            any per-template settings used by the selected backend.
        schema: Optional JSON schema for structured output.
        use_guided_decoding: Whether to use guided decoding.
        validate_with_schema: Whether to validate the output against the provided schema.
            IMPORTANT: Disabling validation may lead to invalid structured outputs and, thus,
            may break result serialization (since we use .map() and .to_json() from datasets).
        llm: The LLM model to use. Must be a chat model (i.e. is_chat_model=True) and support extra_body
            parameters for guided decoding if schema is provided. If None, no LLM call is made.
        request_parameters: Additional parameters to pass to the LLM chat call.
        return_reasoning: Whether to return the reasoning done by the model.
        include_evidence: Wrap each terminal value with an `evidence_anchor`, a verbatim quote
            from the input text supporting the extracted content. Requires an extraction schema.
        use_wrapped_schema_in_prompt: Select the wrapped schema for both schema placeholders when
            metadata is requested. If omitted, confidence scoring selects the wrapped schema and
            evidence alone uses the original schema. Guided decoding uses the wrapped schema in either case.
        evidence_anchor_description: Description for the evidence anchor field.
        wrapped_content_description: Optional description for the content field in the metadata wrapper.
        evidence_before_content: Whether to place `evidence_anchor` before `content` in the metadata
            wrapper. With guided decoding, the model then quotes the evidence before it commits to the
            extracted value. Applies when `include_evidence` is enabled.
        response_has_metadata: If True, the output is expected to have each leaf value wrapped in
            an object with `content` plus metadata fields. If so, the metadata is stripped and the cleaned
            output is returned under the "structured" key, while the raw output with metadata is returned
            under the "structured_with_metadata" key.
        augment_metadata_kwargs: Additional keyword arguments for augment_metadata.
        character_start: Optional character offsets to specify a substring of `text` to process.
            Defaults to 0 (process from the beginning of the text).
        character_end: Optional character offsets to specify a substring of `text` to process.
            If None (default), processes until the end of the text.
        include_confidence: Ask the model for an integer score from 1 to 5 for each extracted
            terminal value. Requires an unwrapped extraction schema. Scores are saved in
            `structured_with_metadata`.
        confidence_description: Description for the confidence field when confidence scoring is enabled.
        history: Previously rendered messages to prepend to the current turn.
        return_messages: Record the configured prompt templates.
        return_messages_formatted: Record the rendered messages from the current turn.
        truncate_user_message_formatted: Character limit for the recorded user message.
            Use None to keep the full message.
        adjust_schema_for_evidence_detection: Legacy alias for `include_evidence`. An explicit
            legacy value takes precedence so saved Hydra overrides still work.
        adjust_schema_description_for_evidence_detection: Legacy alias for
            `use_wrapped_schema_in_prompt` with the same precedence.

    Returns:
        A SingleExtractionResult object with the extraction result.

    Warns:
        UserWarning: When there is no LLM provided, the call to it is skipped.

    Raises:
        TextOffsetValueError: If character_start and/or character_end are set erroneously.
        ValueError: If guided decoding, evidence wrapping, or confidence is enabled without a schema.
    """
    # setting the log level on every query is suboptimal, but the simplest solution in our current architecture
    logging.getLogger("httpx").setLevel(logging.WARNING)

    if not (0 <= character_start <= len(text)):
        raise TextOffsetValueError(
            f"character_start must be between 0 and {len(text)} (inclusive), but is {character_start}"
        )
    if character_end is not None and not (character_start <= character_end):
        raise TextOffsetValueError(
            f"character_end must be greater than or equal to character_start ({character_start}), "
            + f"but is {character_end}"
        )

    out = SingleExtractionResult(
        character_start=character_start,
        character_end=character_end or len(text),
    )

    original_schema = schema
    prompt_schema = schema
    if adjust_schema_for_evidence_detection is not None:
        include_evidence = adjust_schema_for_evidence_detection
    if adjust_schema_description_for_evidence_detection is not None:
        use_wrapped_schema_in_prompt = adjust_schema_description_for_evidence_detection
    if use_wrapped_schema_in_prompt is None:
        use_wrapped_schema_in_prompt = include_confidence

    metadata_schema: dict[str, Any] = {}
    if include_evidence:
        metadata_schema["evidence_anchor"] = {
            "type": "string",
            "description": evidence_anchor_description,
        }
        if not use_guided_decoding:
            warn_once(
                "include_evidence is True but use_guided_decoding is False. "
                "Enable guided decoding to enforce the evidence schema."
            )
    if include_confidence:
        metadata_schema["confidence"] = {
            "type": "integer",
            "enum": [1, 2, 3, 4, 5],
            "description": confidence_description,
        }

    if metadata_schema:
        if schema is None:
            raise ValueError("A JSON schema is required to request evidence or confidence.")
        schema = wrap_terminals_with_metadata(
            schema,
            metadata_schema=metadata_schema,
            content_key=WRAPPED_CONTENT_KEY,
            content_description=wrapped_content_description,
            metadata_first=include_evidence and evidence_before_content,
        )
        # since we wrapped terminals with metadata, we expect metadata in the response
        response_has_metadata = True

        if use_wrapped_schema_in_prompt:
            prompt_schema = schema

    text_to_process = text[out.character_start : out.character_end]

    request_preparer = prepare_request if llm is None else llm.prepare_request
    request = request_preparer(
        prompt_template,
        document=text_to_process,
        schema=prompt_schema,
        history=history or (),
    )

    if return_messages:
        out.messages = {
            "system": prompt_template.get(SYSTEM_MESSAGE_KEY),
            "user": prompt_template.get(USER_MESSAGE_KEY),
        }

    if return_messages_formatted:
        messages_formatted = {
            message.role.name.lower(): message.content or ""
            for message in request.current_messages
        }
        user_message_formatted = messages_formatted.get("user")
        limit = truncate_user_message_formatted
        if (
            limit is not None
            and user_message_formatted is not None
            and len(user_message_formatted) > limit
        ):
            messages_formatted["user"] = (
                f"{user_message_formatted[:limit]}... (truncated @ {limit} chars)"
            )
        out.messages_formatted = messages_formatted

    if use_guided_decoding:
        if schema is None:
            raise ValueError(
                "use_guided_decoding is True but no json schema provided for guided decoding"
            )

    # only proceed if we have an llm
    if llm is not None:
        # setup postprocessing callbacks
        postprocessing_callbacks: list[Callable[[SingleExtractionResult, ChatResponse], None]] = [
            partial(add_backend_metadata_callback, llm=llm)
        ]
        # 1) get response content
        postprocessing_callbacks.append(partial(add_response_content_callback, llm=llm))
        # 2) get reasoning if requested
        if return_reasoning:
            postprocessing_callbacks.append(partial(add_reasoning_content_callback, llm=llm))
        # 3) get structured output
        postprocessing_callbacks.append(
            partial(
                add_structured_callback,
                schema=schema,
                validate_with_schema=validate_with_schema,
            )
        )
        # 4) handle structured with metadata if requested
        if response_has_metadata:
            # we need to pass the start offset to correctly calculate the evidence anchor positions
            if augment_metadata_kwargs is None:
                augment_metadata_kwargs = {}
            augment_metadata_kwargs["evidence_character_offset"] = character_start
            postprocessing_callbacks.append(
                partial(
                    augment_and_strip_metadata_from_structured_callback,
                    schema=schema,
                    original_schema=original_schema,
                    text=text_to_process,
                    validate_with_schema=validate_with_schema,
                    augment_metadata_kwargs=augment_metadata_kwargs,
                )
            )

        request_kwargs = dict(request_parameters or {})
        if request.input_artifacts:
            request_kwargs["input_artifacts"] = request.input_artifacts
        resp = llm.call_llm_chat_with_guided_decoding(
            messages=request.messages,
            json_schema=schema if use_guided_decoding else None,
            **request_kwargs,
        )

        # postprocessing: call each callback in order, but proceed if one fails
        for callback in postprocessing_callbacks:
            try:
                callback(out, resp)
            except Exception as e:
                error_msg_short, error_msg_long = exception2error_msg(e)
                show_msg = f"Failed to process document {text_id}: {error_msg_short}"
                # if we have response content, include a snippet for better debugging
                if out.response_content is not None:
                    show_msg += f", response_content = '{out.response_content[:1500]}...'"
                out["errors"].append(error_msg_short)
                out["errors_long"].append(error_msg_long)

    else:
        warn_once("No LLM provided for extraction, skipping LLM call.")

    check_utf8_encodable(out)

    return out


def extract_from_text_lenient(
    text: str,
    text_id: str,
    character_start: int = 0,
    character_end: int | None = None,
    **kwargs,
) -> SingleExtractionResult:
    """Wrapper around extract_from_text that catches all exceptions.

    This is useful when processing multiple documents and we want to
    continue processing even if one document fails.

    Args:
        text: The text to process.
        text_id: Text identifier for logging.
        character_start: Optional character offsets to specify a substring of `text` to process.
            Defaults to 0 (process from the beginning of the text).
        character_end: Optional character offsets to specify a substring of `text` to process.
            If None (default), processes until the end of the text.

    Keyword Args:
        **kwargs (Any): Keyword arguments for [`extract_from_text`][..extract_from_text].

    Returns:
        A SingleExtractionResult object with the extraction result or error message.
    """

    try:
        return extract_from_text(
            text=text,
            text_id=text_id,
            character_start=character_start,
            character_end=character_end,
            **kwargs,
        )
    except Exception as e:
        error_msg_short, error_msg_long = exception2error_msg(e)
        logger.error(f"Error processing document {text_id}: {error_msg_short}")
        return SingleExtractionResult(
            character_start=character_start,
            character_end=character_end or len(text),
            errors=[error_msg_short],
            errors_long=[error_msg_long],
        )
