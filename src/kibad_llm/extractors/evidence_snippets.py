"""[`EvidenceSnippetExtractor`][.EvidenceSnippetExtractor] for snippet-first extraction with running notes.

Classes:
    EvidenceSnippetExtractor: Reads a document chunk by chunk while keeping running notes, collects
        evidence snippets for the findings, merges findings that describe the same result, and derives
        schema labels from the snippets in a final pass.
"""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from tqdm import tqdm

from kibad_llm.llms.request import prefill_template_fields
from kibad_llm.schema.evidence_snippets import RENDER_TEXTS

from .base import SingleExtractionResult, extract_from_text_lenient
from .chunking import _document_chunk_iterator
from .chunking_utils import tokenizers as tokenizer_lib
from .snippets import (
    CompactText,
    aggregate_finding_cards,
    build_finding_card,
    render_aggregation_document,
    render_evidence_document,
    render_notes,
)

logger = logging.getLogger(__name__)

# Keyword arguments of extract_from_text that the snippet pass shares with the label pass. All other
# arguments (schema, prompt template, evidence/confidence wrapping, ...) only configure the label pass,
# since the snippet pass has its own schema with verbatim anchors.
SNIPPET_PASS_SHARED_KWARGS = (
    "llm",
    "request_parameters",
    "use_guided_decoding",
    "validate_with_schema",
    "return_reasoning",
    "return_messages",
    "return_messages_formatted",
    "truncate_user_message_formatted",
)

NOTES_KEY = "study_notes"
FINDINGS_KEY = "evidence_findings"
RAW_FINDINGS_KEY = "evidence_findings_raw"


def _resolve_ref(schema: Mapping[str, Any], node: Mapping[str, Any]) -> Mapping[str, Any]:
    """Resolve a local `$ref` (e.g. `#/$defs/StudyNotes`) in a JSON schema.

    Args:
        schema: Root schema containing the definitions.
        node: Schema node that may be a reference.

    Returns:
        The referenced node, or `node` itself if it is not a local reference.
    """
    ref = node.get("$ref")
    if not isinstance(ref, str) or not ref.startswith("#/"):
        return node
    resolved: Any = schema
    for part in ref[2:].split("/"):
        resolved = resolved.get(part, {}) if isinstance(resolved, Mapping) else {}
    return resolved if isinstance(resolved, Mapping) else node


def _notes_fields(schema: Mapping[str, Any] | None) -> list[str]:
    """Return the field names of the `notes` object in the snippet schema.

    Args:
        schema: JSON schema of the snippet pass output.

    Returns:
        The property names of `notes`, or an empty list if the schema does not define them.
    """
    if not schema:
        return []
    notes = schema.get("properties", {}).get("notes")
    if not isinstance(notes, Mapping):
        return []
    return list(_resolve_ref(schema, notes).get("properties", {}))


def _update_notes(notes: dict[str, Any], update: Any) -> dict[str, Any]:
    """Merge the notes returned for a chunk into the running notes.

    Non-empty returned values replace the previous ones. Empty values do not erase information the
    model may have dropped by mistake.

    Args:
        notes: Running notes so far.
        update: `notes` object returned for the current chunk (ignored if not a mapping).

    Returns:
        The updated notes (a new dict).
    """
    result = dict(notes)
    if isinstance(update, Mapping):
        for key, value in update.items():
            if value not in (None, "", []):
                result[key] = value
            else:
                result.setdefault(key, "")
    return result


class EvidenceSnippetExtractor:
    """Snippet-first extractor: running notes across chunks, evidence snippets, then schema labels.

    For each document:

    1. The text is chunked as in [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor],
       but chunks are processed in order. Each chunk prompt contains the running notes from the previous
       chunks (study topic, design, area, organisms, variables, current section, open points). The model
       returns the updated notes and the findings in the chunk, each marked by one to three verbatim
       anchors in the language of the document.
    2. The anchors are located in the full text and widened to paragraphs or sentences in code (see
       [`build_finding_card`][kibad_llm.extractors.snippets.build_finding_card]), so the snippets are
       verbatim and large enough for a judge.
    3. Findings that describe the same result (e.g. in the abstract, the results and the conclusion) are
       merged: one LLM call per document groups the located findings by their IDs, summaries and quotes, and
       code joins the verbatim snippets of each group (see
       [`aggregate_finding_cards`][kibad_llm.extractors.snippets.aggregate_finding_cards]). All snippets of a
       group are kept. Without grouping (disabled, fewer than two located findings, or a failed call), each
       located finding stays on its own.
    4. Optionally, a final label pass runs the configured `prompt_template` and `schema` (exactly like the
       `simple` extractor) on a document rendered from the notes and the snippets. This gives the usual
       structured labels, e.g. `ecosystem_service_trends`, in the output language of the task prompt.

    Attributes:
        snippet_prompt_template: Prompt template of the snippet pass. Besides `{document}` and
            `{schema_description}`, it can use `{running_notes}`, `{chunk_index}`, `{num_chunks}` and
            `{task_description}`.
        snippet_schema: JSON schema of the snippet pass output, with `notes` and `findings` (see
            [`ChunkEvidence`][kibad_llm.schema.evidence_snippets.ChunkEvidence]).
        snippet_task_description: Task-specific description of the findings to look for. Also inserted at
            `{task_description}` in the aggregation prompt.
        aggregate_findings: Whether to merge findings that describe the same result with an LLM call.
        aggregation_prompt_template: Prompt template of the aggregation call. Besides `{document}` and
            `{schema_description}`, it can use `{task_description}`.
        aggregation_schema: JSON schema of the aggregation output (see
            [`FindingAggregation`][kibad_llm.schema.evidence_snippets.FindingAggregation]).
        label_pass: Whether to run the final label pass.
        return_as_list: Fields of the per-call results to return as lists, one entry per LLM call
            (all chunk calls in order, then the aggregation call and the label call if they ran).
        tokenizer: Tokenizer used for chunking.
        max_char_buffer: Maximum chunk size in characters.
        min_snippet_chars: Target minimum snippet length in characters.
        max_snippet_chars: Maximum snippet length in characters (before merging nearby snippets).
        snippet_merge_gap: Snippets of one finding at most this many characters apart are merged.
        verbose: Log progress per chunk.
        default_kwargs: Further keyword arguments for
            [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient]. They configure
            the label pass; the entries in `SNIPPET_PASS_SHARED_KWARGS` (e.g. `llm`) also apply to the
            snippet pass.
    """

    def __init__(
        self,
        snippet_prompt_template: dict[str, Any],
        snippet_schema: dict[str, Any],
        snippet_task_description: str = "",
        aggregate_findings: bool = True,
        aggregation_prompt_template: dict[str, Any] | None = None,
        aggregation_schema: dict[str, Any] | None = None,
        label_pass: bool = True,
        return_as_list: list[str] | None = None,
        tokenizer: tokenizer_lib.Tokenizer | None = None,
        max_char_buffer: int = 20000,
        min_snippet_chars: int = 800,
        max_snippet_chars: int = 2500,
        snippet_merge_gap: int = 200,
        verbose: bool = False,
        **kwargs,
    ):
        """Store the configuration.

        Args:
            snippet_prompt_template: Prompt template of the snippet pass.
            snippet_schema: JSON schema of the snippet pass output.
            snippet_task_description: Task-specific description of the findings to look for.
            aggregate_findings: Whether to merge findings that describe the same result with an LLM call.
            aggregation_prompt_template: Prompt template of the aggregation call.
            aggregation_schema: JSON schema of the aggregation output.
            label_pass: Whether to run the final label pass.
            return_as_list: Fields of the per-call results to return as lists.
            tokenizer: Tokenizer used for chunking.
            max_char_buffer: Maximum chunk size in characters.
            min_snippet_chars: Target minimum snippet length in characters.
            max_snippet_chars: Maximum snippet length in characters.
            snippet_merge_gap: Snippets of one finding at most this many characters apart are merged.
            verbose: Log progress per chunk.

        Keyword Args:
            **kwargs (Any): Keyword arguments for
                [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient].

        Raises:
            ValueError: If the snippet sizes are inconsistent, or aggregation is enabled without its prompt
                template or schema.
        """
        if not 0 < min_snippet_chars <= max_snippet_chars:
            raise ValueError(
                f"Expected 0 < min_snippet_chars <= max_snippet_chars, got {min_snippet_chars} "
                f"and {max_snippet_chars}."
            )
        if aggregate_findings and (
            aggregation_prompt_template is None or aggregation_schema is None
        ):
            raise ValueError(
                "aggregate_findings requires aggregation_prompt_template and aggregation_schema."
            )
        self.snippet_prompt_template = snippet_prompt_template
        self.snippet_schema = snippet_schema
        self.snippet_task_description = snippet_task_description
        self.aggregate_findings = aggregate_findings
        self.aggregation_prompt_template = aggregation_prompt_template
        self.aggregation_schema = aggregation_schema
        self.label_pass = label_pass
        self.return_as_list = return_as_list or []
        self.tokenizer = tokenizer
        self.max_char_buffer = max_char_buffer
        self.min_snippet_chars = min_snippet_chars
        self.max_snippet_chars = max_snippet_chars
        self.snippet_merge_gap = snippet_merge_gap
        self.verbose = verbose
        self.default_kwargs = kwargs

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        """Process one document.

        Args:
            *args (Any): Positional form of `text` and `text_id`, in that order.

        Keyword Args:
            text (str): Input document to process.
            text_id (str): Id of input document.
            * (Any): Refer to [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient]

        Returns:
            Dict with the key `structured`, holding the label pass output (one entry per top-level schema
            property; None if the label pass did not run or failed), the final notes at `study_notes`, the
            aggregated finding cards (located findings only) at `evidence_findings` and the per-chunk finding
            cards (including unlocated ones) at `evidence_findings_raw`. The running notes after each chunk are
            returned at `study_notes_list`. For each field in `return_as_list`, `"{field}_list"` holds one entry
            per LLM call.
        """
        text = kwargs.pop("text", None)
        if text is None:
            text = args[0]
        text_id = kwargs.pop("text_id", None)
        if text_id is None:
            text_id = args[-1]

        combined_kwargs = {**self.default_kwargs, **kwargs}
        snippet_kwargs = {
            k: v for k, v in combined_kwargs.items() if k in SNIPPET_PASS_SHARED_KWARGS
        }

        chunks = _document_chunk_iterator(
            document=text, max_char_buffer=self.max_char_buffer, tokenizer=self.tokenizer
        )
        compact_text = CompactText(text)

        notes: dict[str, Any] = {key: "" for key in _notes_fields(self.snippet_schema)}
        notes_list: list[dict[str, Any]] = []
        cards: list[dict[str, Any]] = []
        calls: list[SingleExtractionResult] = []

        chunk_iterator: Any = enumerate(chunks)
        if self.verbose:
            logger.info(f"{len(chunks)} chunks in document {text_id}")
            chunk_iterator = tqdm(chunk_iterator, total=len(chunks), desc=text_id)
        for i, chunk in chunk_iterator:
            chunk_start = chunk.char_interval.start_pos or 0
            chunk_end = chunk.char_interval.end_pos
            prompt_template = prefill_template_fields(
                self.snippet_prompt_template,
                {
                    "running_notes": render_notes(
                        notes, empty_text=RENDER_TEXTS["no_notes_first_chunk"]
                    ),
                    "chunk_index": str(i + 1),
                    "num_chunks": str(len(chunks)),
                    "task_description": self.snippet_task_description,
                },
            )
            result = extract_from_text_lenient(
                text=text,
                text_id=f"{text_id}_chunk_{i}",
                prompt_template=prompt_template,
                schema=self.snippet_schema,
                **snippet_kwargs,
                character_start=chunk_start,
                character_end=chunk_end,
            )
            calls.append(result)

            structured = result.structured if isinstance(result.structured, Mapping) else {}
            notes = _update_notes(notes, structured.get("notes"))
            notes_list.append(dict(notes))
            for finding in structured.get("findings") or []:
                if not isinstance(finding, Mapping):
                    continue
                cards.append(
                    build_finding_card(
                        finding,
                        finding_id=f"F{len(cards) + 1}",
                        chunk_index=i,
                        text=text,
                        compact_text=compact_text,
                        chunk_start=chunk_start,
                        chunk_end=chunk_end if chunk_end is not None else len(text),
                        min_snippet_chars=self.min_snippet_chars,
                        max_snippet_chars=self.max_snippet_chars,
                        merge_gap=self.snippet_merge_gap,
                    )
                )

        aggregated = self._aggregate(notes, cards, text, text_id, snippet_kwargs, calls)
        labels = self._label_pass(notes, aggregated, text_id, combined_kwargs, calls)

        result_dict: dict[str, Any] = {
            "structured": {
                **labels,
                NOTES_KEY: notes,
                FINDINGS_KEY: aggregated,
                RAW_FINDINGS_KEY: cards,
            },
            f"{NOTES_KEY}_list": notes_list,
        }
        for field in self.return_as_list:
            result_dict[f"{field}_list"] = [call.get(field, None) for call in calls]
        return result_dict

    def _aggregate(
        self,
        notes: dict[str, Any],
        cards: list[dict[str, Any]],
        text: str,
        text_id: str,
        snippet_kwargs: dict[str, Any],
        calls: list[SingleExtractionResult],
    ) -> list[dict[str, Any]]:
        """Merge located findings that describe the same result.

        The aggregation call is made if it is enabled and at least two findings were located. Its call result
        is appended to `calls`.

        Args:
            notes: Final running notes.
            cards: Per-chunk finding cards.
            text: Full document text.
            text_id: Document id for logging.
            snippet_kwargs: Keyword arguments shared with the snippet pass (e.g. `llm`).
            calls: Results of all LLM calls so far; extended in place.

        Returns:
            Aggregated cards of the located findings. Without grouping, each located finding is its own card.
        """
        located_cards = [card for card in cards if card["located"]]
        groups = None
        if (
            self.aggregate_findings
            and self.aggregation_prompt_template is not None
            and len(located_cards) >= 2
        ):
            result = extract_from_text_lenient(
                text=render_aggregation_document(notes, located_cards),
                text_id=f"{text_id}_aggregation",
                prompt_template=prefill_template_fields(
                    self.aggregation_prompt_template,
                    {"task_description": self.snippet_task_description},
                ),
                schema=self.aggregation_schema,
                **snippet_kwargs,
            )
            calls.append(result)
            if isinstance(result.structured, Mapping):
                groups = result.structured.get("groups")
        return aggregate_finding_cards(
            located_cards, groups, text=text, merge_gap=self.snippet_merge_gap
        )

    def _label_pass(
        self,
        notes: dict[str, Any],
        cards: list[dict[str, Any]],
        text_id: str,
        combined_kwargs: dict[str, Any],
        calls: list[SingleExtractionResult],
    ) -> dict[str, Any]:
        """Derive schema labels from the notes and the aggregated findings.

        The pass is skipped if it is disabled or no finding could be located. Its call result is
        appended to `calls`.

        Args:
            notes: Final running notes.
            cards: Aggregated finding cards.
            text_id: Document id for logging.
            combined_kwargs: Keyword arguments for the label call.
            calls: Results of all LLM calls so far; extended in place.

        Returns:
            The label pass output. To keep the output format identical for all documents, every top-level
            property of the label schema is present, set to None if the pass did not run or failed.
        """
        schema = combined_kwargs.get("schema")
        properties: Mapping[str, Any] = (
            schema.get("properties", {}) if isinstance(schema, Mapping) else {}
        )
        labels: dict[str, Any] = {key: None for key in properties}

        located_cards = [card for card in cards if card["located"]]
        if not self.label_pass or not located_cards:
            return labels

        evidence_document = render_evidence_document(notes, located_cards)
        result = extract_from_text_lenient(
            text=evidence_document, text_id=f"{text_id}_labels", **combined_kwargs
        )
        calls.append(result)
        if isinstance(result.structured, Mapping):
            labels.update(result.structured)
        return labels
