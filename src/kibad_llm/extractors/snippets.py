"""Build evidence snippets from model-quoted anchors without further LLM calls.

The model only marks a finding by quoting one to three short anchors. The functions here locate
those anchors in the source text and widen each match to whole paragraphs or sentences, so that a
judge (human or model) sees enough context. Locating tolerates the differences that typically make
verbatim quotes fail: whitespace and line breaks, Markdown emphasis, quote characters, hyphenation at
line ends, Unicode variants and ellipses.

Classes:
    CompactText: Alphanumeric-only view of a text with a mapping back to the original offsets.

Functions:
    locate_anchor: Find the span of an anchor in a text, preferably inside a search window.
    expand_span: Widen a span to paragraphs or sentences within a size budget.
    merge_spans: Merge overlapping or nearby spans.
    build_finding_card: Locate the anchors of one model finding and attach the widened snippets.
    aggregate_finding_cards: Merge finding cards that describe the same result into aggregated cards.
    format_value: Format a JSON-like value for rendering in prompts.
    render_notes: Render running notes as a short Markdown list.
    render_finding_card: Render a finding card with its snippets as Markdown.
    render_evidence_document: Render notes and finding cards as one Markdown document.
    render_aggregation_document: Render notes and compact finding cards as input for the aggregation step.
"""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Mapping, Sequence
import re
from typing import Any
import unicodedata

from kibad_llm.schema.evidence_snippets import NOTES_LABELS, RENDER_TEXTS

from .base import _find_anchor_match_spans

# Anchors shorter than this (in alphanumeric characters) are only matched exactly, since
# tolerant matching of very short strings produces false positives.
MIN_COMPACT_ANCHOR_CHARS = 20
# For the partial fallback, the shortest run of consecutive anchor words that may be matched.
MIN_PARTIAL_WORDS = 6

_ELLIPSIS_RE = re.compile(r"\[\s*(?:\.\.\.|…)\s*\]|\(\s*(?:\.\.\.|…)\s*\)|\.\.\.|…")
_PARAGRAPH_BREAK_RE = re.compile(r"\n[ \t]*\n")
_SENTENCE_END_RE = re.compile(r"(?<=[.!?])[\"')\]]*\s+")

# Notes that only steer the chunk-by-chunk reading and are not useful afterwards.
NOTES_FIELDS_HIDDEN_AFTER_READING = ("current_section", "open_points")


class CompactText:
    """Alphanumeric-only, lowercased view of a text with a mapping back to the original offsets.

    Unicode is normalized with NFKC and everything that is not a letter or digit is dropped. This
    makes matching robust against whitespace, punctuation, Markdown, quotes and hyphenation.

    Attributes:
        text: The compact text.
        offsets: For each character of `text`, the offset of its source character in the original text.
    """

    def __init__(self, text: str) -> None:
        """Build the compact view.

        Args:
            text: Original text.
        """
        chars: list[str] = []
        offsets: list[int] = []
        for offset, char in enumerate(text):
            for normalized in unicodedata.normalize("NFKC", char):
                if normalized.isalnum():
                    chars.append(normalized.lower())
                    offsets.append(offset)
        self.text = "".join(chars)
        self.offsets = offsets

    @staticmethod
    def compact(text: str) -> str:
        """Return the compact form of a text, as used for the full text.

        Args:
            text: Any text, e.g. an anchor.

        Returns:
            The lowercased, NFKC-normalized letters and digits of `text`.
        """
        return "".join(c.lower() for c in unicodedata.normalize("NFKC", text) if c.isalnum())

    def find(self, needle: str, start: int = 0, end: int | None = None) -> tuple[int, int] | None:
        """Find a compact needle and map the match back to original offsets.

        Args:
            needle: Compact string to search for.
            start: Original offset where the search window starts.
            end: Original offset where the search window ends (exclusive), or None for the text end.

        Returns:
            The `(start, end)` span in the original text, or None if not found.
        """
        if not needle:
            return None
        compact_start = bisect_left(self.offsets, start)
        compact_end = len(self.offsets) if end is None else bisect_left(self.offsets, end)
        position = self.text.find(needle, compact_start, compact_end)
        if position < 0:
            return None
        return self.offsets[position], self.offsets[position + len(needle) - 1] + 1


def _locate_in_window(
    text: str,
    anchor: str,
    compact_text: CompactText,
    start: int,
    end: int | None,
) -> tuple[int, int, str] | None:
    """Try all matching strategies for one anchor inside one search window.

    Args:
        text: Full original text.
        anchor: Anchor as quoted by the model.
        compact_text: Compact view of `text`.
        start: Window start offset.
        end: Window end offset (exclusive), or None for the text end.

    Returns:
        `(start, end, match_type)` or None. `match_type` is one of `exact`, `normalized`,
        `ellipsis` or `partial`.
    """
    window_end = len(text) if end is None else end
    # 1) exact up to whitespace (and wrapping quotes), as used by evidence detection
    exact = _find_anchor_match_spans(text=text[start:window_end], anchor=anchor)
    if exact:
        return exact[0][0] + start, exact[0][1] + start, "exact"

    compact_anchor = CompactText.compact(anchor)
    if len(compact_anchor) < MIN_COMPACT_ANCHOR_CHARS:
        return None

    # 2) alphanumeric-only match
    span = compact_text.find(compact_anchor, start, window_end)
    if span is not None:
        return span[0], span[1], "normalized"

    # 3) anchor with omissions: all parts must appear in order
    parts = [CompactText.compact(p) for p in _ELLIPSIS_RE.split(anchor)]
    parts = [p for p in parts if p]
    if len(parts) > 1 and all(len(p) >= MIN_COMPACT_ANCHOR_CHARS // 2 for p in parts):
        cursor = start
        part_spans = []
        for part in parts:
            part_span = compact_text.find(part, cursor, window_end)
            if part_span is None:
                break
            part_spans.append(part_span)
            cursor = part_span[1]
        else:
            return part_spans[0][0], part_spans[-1][1], "ellipsis"

    # 4) longest run of consecutive anchor words (handles small paraphrases at the edges)
    words = anchor.split()
    for size in range(len(words) - 1, MIN_PARTIAL_WORDS - 1, -1):
        for offset in range(len(words) - size + 1):
            compact_part = CompactText.compact(" ".join(words[offset : offset + size]))
            if len(compact_part) < MIN_COMPACT_ANCHOR_CHARS:
                continue
            span = compact_text.find(compact_part, start, window_end)
            if span is not None:
                return span[0], span[1], "partial"
    return None


def locate_anchor(
    text: str,
    anchor: str,
    compact_text: CompactText | None = None,
    window_start: int = 0,
    window_end: int | None = None,
) -> tuple[int, int, str, bool] | None:
    """Find the span of an anchor in a text, preferably inside a search window.

    The window (usually the chunk the model saw) is searched first, then the whole text.

    Args:
        text: Full original text.
        anchor: Anchor as quoted by the model.
        compact_text: Precomputed compact view of `text`; built on the fly if None.
        window_start: Start offset of the preferred search window.
        window_end: End offset (exclusive) of the preferred search window, or None for the text end.

    Returns:
        `(start, end, match_type, in_window)` or None if the anchor cannot be located. See
        [`_locate_in_window`][.._locate_in_window] for the match types.
    """
    if not isinstance(anchor, str) or not anchor.strip():
        return None
    compact_text = compact_text or CompactText(text)
    found = _locate_in_window(text, anchor, compact_text, window_start, window_end)
    if found is not None:
        return found[0], found[1], found[2], True
    if window_start > 0 or (window_end is not None and window_end < len(text)):
        found = _locate_in_window(text, anchor, compact_text, 0, None)
        if found is not None:
            return found[0], found[1], found[2], False
    return None


def _paragraph_bounds(text: str) -> list[tuple[int, int]]:
    """Split a text into paragraphs at blank lines.

    Args:
        text: Original text.

    Returns:
        `(start, end)` spans of all paragraphs, in order, including empty ones.
    """
    bounds = []
    position = 0
    for match in _PARAGRAPH_BREAK_RE.finditer(text):
        bounds.append((position, match.start()))
        position = match.end()
    bounds.append((position, len(text)))
    return bounds


def _sentence_bounds(text: str, start: int, end: int) -> list[tuple[int, int]]:
    """Split a region of a text into sentences.

    Args:
        text: Original text.
        start: Region start offset.
        end: Region end offset (exclusive).

    Returns:
        `(start, end)` spans of the sentences in the region, in order.
    """
    bounds = []
    position = start
    for match in _SENTENCE_END_RE.finditer(text, start, end):
        bounds.append((position, match.start()))
        position = match.end()
    bounds.append((position, end))
    return bounds


def _grow(
    units: Sequence[tuple[int, int]], first: int, last: int, min_chars: int, max_chars: int
) -> tuple[int, int]:
    """Add neighbouring units (paragraphs or sentences) until a span is long enough.

    Units are added alternately after and before the current span. A unit is skipped if adding it
    would exceed `max_chars`.

    Args:
        units: Ordered `(start, end)` spans.
        first: Index of the first unit of the current span.
        last: Index of the last unit of the current span.
        min_chars: Target minimum span length.
        max_chars: Maximum span length.

    Returns:
        The indices `(first, last)` of the grown span.
    """
    while units[last][1] - units[first][0] < min_chars:
        grown = False
        if last + 1 < len(units) and units[last + 1][1] - units[first][0] <= max_chars:
            last += 1
            grown = True
        if (
            units[last][1] - units[first][0] < min_chars
            and first > 0
            and units[last][1] - units[first - 1][0] <= max_chars
        ):
            first -= 1
            grown = True
        if not grown:
            break
    return first, last


def expand_span(
    text: str, start: int, end: int, min_chars: int = 800, max_chars: int = 2500
) -> tuple[int, int]:
    """Widen a span to whole paragraphs or sentences within a size budget.

    The span grows to its paragraph(s) and then to neighbouring paragraphs until it has at least
    `min_chars` characters. If the paragraph is longer than `max_chars`, whole sentences around the
    span are used instead. A span that is itself longer than `max_chars` is returned unchanged.

    Args:
        text: Original text.
        start: Span start offset.
        end: Span end offset (exclusive).
        min_chars: Target minimum snippet length.
        max_chars: Maximum snippet length.

    Returns:
        The widened `(start, end)` span, stripped of surrounding whitespace.
    """
    if end - start >= max_chars:
        return start, end

    paragraphs = _paragraph_bounds(text)
    starts = [p[0] for p in paragraphs]
    first = max(bisect_left(starts, start + 1) - 1, 0)
    last = max(bisect_left(starts, max(end, start + 1)) - 1, first)

    if paragraphs[last][1] - paragraphs[first][0] <= max_chars:
        first, last = _grow(paragraphs, first, last, min_chars, max_chars)
        new_start, new_end = paragraphs[first][0], paragraphs[last][1]
    else:
        # paragraph too long: use sentences of the paragraph(s) around the span
        sentences = _sentence_bounds(text, paragraphs[first][0], paragraphs[last][1])
        sentence_starts = [s[0] for s in sentences]
        s_first = max(bisect_left(sentence_starts, start + 1) - 1, 0)
        s_last = max(bisect_left(sentence_starts, max(end, start + 1)) - 1, s_first)
        if sentences[s_last][1] - sentences[s_first][0] > max_chars:
            return start, end
        s_first, s_last = _grow(sentences, s_first, s_last, min_chars, max_chars)
        new_start, new_end = sentences[s_first][0], sentences[s_last][1]

    new_start, new_end = min(new_start, start), max(new_end, end)
    while new_start < new_end and text[new_start].isspace():
        new_start += 1
    while new_end > new_start and text[new_end - 1].isspace():
        new_end -= 1
    return new_start, new_end


def merge_spans(spans: Sequence[tuple[int, int]], max_gap: int = 200) -> list[tuple[int, int]]:
    """Merge overlapping spans and spans that are at most `max_gap` characters apart.

    Args:
        spans: `(start, end)` spans in any order.
        max_gap: Maximum number of characters between two spans that are still merged.

    Returns:
        Sorted, merged spans.
    """
    merged: list[tuple[int, int]] = []
    for start, end in sorted(spans):
        if merged and start - merged[-1][1] <= max_gap:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def build_finding_card(
    finding: Mapping[str, Any],
    *,
    finding_id: str,
    chunk_index: int,
    text: str,
    compact_text: CompactText,
    chunk_start: int,
    chunk_end: int,
    min_snippet_chars: int = 800,
    max_snippet_chars: int = 2500,
    merge_gap: int = 200,
) -> dict[str, Any]:
    """Locate the anchors of one model finding and attach the widened snippets.

    Args:
        finding: One entry of the `findings` list returned by the model (see
            [`EvidenceFinding`][kibad_llm.schema.evidence_snippets.EvidenceFinding]).
        finding_id: ID of the finding within the document, e.g. `F3`.
        chunk_index: Index of the chunk the finding was extracted from.
        text: Full document text.
        compact_text: Compact view of `text`.
        chunk_start: Start offset of the chunk in `text`.
        chunk_end: End offset of the chunk in `text` (exclusive).
        min_snippet_chars: Target minimum length of each snippet.
        max_snippet_chars: Maximum length of each snippet (before merging nearby snippets).
        merge_gap: Snippets at most this many characters apart are merged.

    Returns:
        A JSON-serializable finding card with the model fields, the located `anchors`
        (each with `text`, `start`, `end`, `match` and `in_chunk`; offsets are None if not located),
        the merged `snippets` (each with `start`, `end` and `text`) and `located`, which is True if at
        least one anchor was found.
    """
    anchors: Any = finding.get("anchors") or []
    if isinstance(anchors, str):
        anchors = [anchors]

    anchor_records = []
    spans = []
    for anchor in anchors:
        found = locate_anchor(
            text,
            anchor,
            compact_text=compact_text,
            window_start=chunk_start,
            window_end=chunk_end,
        )
        if found is None:
            anchor_records.append(
                {"text": anchor, "start": None, "end": None, "match": None, "in_chunk": None}
            )
            continue
        start, end, match_type, in_window = found
        anchor_records.append(
            {
                "text": anchor,
                "start": start,
                "end": end,
                "match": match_type,
                "in_chunk": in_window,
            }
        )
        spans.append(expand_span(text, start, end, min_snippet_chars, max_snippet_chars))

    snippets = [
        {"start": start, "end": end, "text": text[start:end]}
        for start, end in merge_spans(spans, max_gap=merge_gap)
    ]

    def _as_str(key: str) -> str:
        value = finding.get(key)
        return value if isinstance(value, str) else ""

    return {
        "id": finding_id,
        "chunk_index": chunk_index,
        "section": _as_str("section"),
        "section_type": _as_str("section_type"),
        "finding": _as_str("finding"),
        "context": _as_str("context"),
        "figure_or_table": _as_str("figure_or_table"),
        "anchors": anchor_records,
        "snippets": snippets,
        "located": len(snippets) > 0,
    }


def format_value(value: Any) -> str:
    """Format a scalar for rendering, e.g. `1998.0` as `1998`.

    Args:
        value: Any JSON-like value.

    Returns:
        A string representation.
    """
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, list):
        return ", ".join(format_value(v) for v in value)
    return str(value)


def render_notes(
    notes: Mapping[str, Any] | None,
    empty_text: str = RENDER_TEXTS["no_notes"],
    hidden_fields: Sequence[str] = (),
) -> str:
    """Render running notes as a short Markdown list.

    Args:
        notes: Notes keyed by field name (see
            [`StudyNotes`][kibad_llm.schema.evidence_snippets.StudyNotes]).
        empty_text: Text to return if no field has content.
        hidden_fields: Fields to leave out.

    Returns:
        One list item per non-empty field.
    """
    lines = [
        f"- {NOTES_LABELS.get(key, key)}: {format_value(value)}"
        for key, value in (notes or {}).items()
        if key not in hidden_fields and value not in (None, "", [])
    ]
    return "\n".join(lines) if lines else empty_text


def render_finding_card(card: Mapping[str, Any], heading_level: int = 2) -> str:
    """Render a finding card with its snippets as Markdown.

    Args:
        card: Finding card as returned by [`build_finding_card`][..build_finding_card].
        heading_level: Markdown heading level for the card title.

    Returns:
        The rendered card: ID, section, figure/table reference, summary, context and the snippets.
        If no anchor was located, the unlocated anchors are shown instead of snippets.
    """
    lines = [f"{'#' * heading_level} {RENDER_TEXTS['card_title']} {card.get('id', '')}"]
    section = card.get("section") or ""
    section_type = card.get("section_type") or ""
    if section or section_type:
        lines.append(
            f"{RENDER_TEXTS['section']}: {section}"
            + (f" ({section_type})" if section_type else "")
        )
    if card.get("figure_or_table"):
        lines.append(f"{RENDER_TEXTS['figure_or_table']}: {card['figure_or_table']}")
    if card.get("finding"):
        lines.append(f"{RENDER_TEXTS['finding_by_model']}: {card['finding']}")
    if card.get("context"):
        lines.append(f"{RENDER_TEXTS['context_from_document']}: {card['context']}")
    snippets: Any = card.get("snippets") or []
    if snippets:
        lines.append(f"{RENDER_TEXTS['snippets']}:")
        lines.append("\n\n[...]\n\n".join(s["text"] for s in snippets))
    else:
        anchors = [a.get("text", "") for a in card.get("anchors") or []]
        lines.append(f"{RENDER_TEXTS['quotes_unlocated']}: " + " | ".join(anchors))
    return "\n".join(lines)


def render_evidence_document(
    notes: Mapping[str, Any] | None, cards: Sequence[Mapping[str, Any]]
) -> str:
    """Render notes and finding cards as one Markdown document, e.g. as input for the label pass.

    Args:
        notes: Final running notes of the document.
        cards: Finding cards as returned by [`build_finding_card`][..build_finding_card].

    Returns:
        A Markdown document with an explanatory header, the notes and all cards.
    """
    parts = [
        RENDER_TEXTS["evidence_document_header"],
        f"# {RENDER_TEXTS['notes_heading']}",
        render_notes(notes, hidden_fields=NOTES_FIELDS_HIDDEN_AFTER_READING),
        f"# {RENDER_TEXTS['cards_heading']}",
    ]
    parts.extend(render_finding_card(card) for card in cards)
    return "\n\n".join(parts)


def _card_position(card: Mapping[str, Any]) -> int:
    """Return the text position of a card: its first snippet start, else its first located anchor.

    Args:
        card: Finding card.

    Returns:
        The offset, or a large number if the card has no location.
    """
    starts = [s["start"] for s in card.get("snippets") or []]
    starts += [a["start"] for a in card.get("anchors") or [] if a.get("start") is not None]
    return min(starts) if starts else 2**62


def _unique(values: Sequence[Any]) -> list[str]:
    """Return the non-empty string values in order, without repetitions.

    Args:
        values: Values to filter.

    Returns:
        The unique non-empty strings.
    """
    return list(dict.fromkeys(v for v in values if isinstance(v, str) and v))


def aggregate_finding_cards(
    cards: Sequence[Mapping[str, Any]],
    groups: Any,
    *,
    text: str,
    merge_gap: int = 200,
    id_prefix: str = "A",
) -> list[dict[str, Any]]:
    """Merge finding cards that describe the same result into aggregated cards.

    The groups come from the model (see
    [`FindingAggregation`][kibad_llm.schema.evidence_snippets.FindingAggregation]). Only the summary and context are
    taken from the model; all evidence (anchors and snippets) comes from the member cards, so no new text is added.
    Unknown IDs are ignored, an ID listed in several groups stays in the first one, and cards in no group become
    single-member groups. Passing no groups therefore keeps every card as its own aggregated card.

    Args:
        cards: Finding cards as returned by [`build_finding_card`][..build_finding_card].
        groups: `groups` list returned by the model, or None.
        text: Full document text, used to re-slice merged snippets.
        merge_gap: Snippets at most this many characters apart are merged.
        id_prefix: Prefix of the aggregated card IDs.

    Returns:
        Aggregated cards in text order with the IDs `A1`, `A2`, ... Each has `member_ids` and `chunk_indices` of its
        members, their sections, section types and figure/table references joined, all their anchors (each with
        its `finding_id`), all their snippets (merged and in text order), the `finding` and `context` of the group
        (falling back to the members') and `located`.
    """
    by_id = {card["id"]: card for card in cards}
    assigned: set[str] = set()
    grouped: list[tuple[list[str], Mapping[str, Any]]] = []
    for group in groups if isinstance(groups, list) else []:
        if not isinstance(group, Mapping):
            continue
        ids: Any = group.get("finding_ids") or []
        if isinstance(ids, str):
            ids = [ids]
        members = [
            i
            for i in dict.fromkeys(ids)
            if isinstance(i, str) and i in by_id and i not in assigned
        ]
        if members:
            assigned.update(members)
            grouped.append((members, group))
    grouped.extend(([card["id"]], {}) for card in cards if card["id"] not in assigned)

    aggregated = []
    for members, group in grouped:
        member_cards = sorted((by_id[i] for i in members), key=_card_position)
        spans = [(s["start"], s["end"]) for c in member_cards for s in c.get("snippets") or []]
        snippets = [
            {"start": start, "end": end, "text": text[start:end]}
            for start, end in merge_spans(spans, max_gap=merge_gap)
        ]
        group_finding = group.get("finding")
        group_context = group.get("context")
        aggregated.append(
            {
                "member_ids": [c["id"] for c in member_cards],
                "chunk_indices": sorted({c["chunk_index"] for c in member_cards}),
                "section": " | ".join(_unique([c.get("section") for c in member_cards])),
                "section_type": ", ".join(_unique([c.get("section_type") for c in member_cards])),
                "finding": (
                    group_finding
                    if isinstance(group_finding, str) and group_finding
                    else member_cards[0].get("finding", "")
                ),
                "context": (
                    group_context
                    if isinstance(group_context, str) and group_context
                    else next(iter(_unique([c.get("context") for c in member_cards])), "")
                ),
                "figure_or_table": ", ".join(
                    _unique([c.get("figure_or_table") for c in member_cards])
                ),
                "anchors": [
                    {**anchor, "finding_id": c["id"]}
                    for c in member_cards
                    for anchor in c.get("anchors") or []
                ],
                "snippets": snippets,
                "located": len(snippets) > 0,
            }
        )

    aggregated.sort(key=_card_position)
    return [{"id": f"{id_prefix}{i + 1}", **card} for i, card in enumerate(aggregated)]


def render_aggregation_document(
    notes: Mapping[str, Any] | None, cards: Sequence[Mapping[str, Any]]
) -> str:
    """Render notes and compact finding cards as input for the aggregation step.

    Only the quotes are shown, not the widened snippets, to keep the input small.

    Args:
        notes: Final running notes of the document.
        cards: Finding cards as returned by [`build_finding_card`][..build_finding_card].

    Returns:
        A Markdown document with an explanatory header, the notes and one compact entry per card, in text order.
    """
    parts = [
        RENDER_TEXTS["aggregation_document_header"],
        f"# {RENDER_TEXTS['notes_heading']}",
        render_notes(notes, hidden_fields=NOTES_FIELDS_HIDDEN_AFTER_READING),
        f"# {RENDER_TEXTS['cards_heading']}",
    ]
    for card in sorted(cards, key=_card_position):
        lines = [f"## {card.get('id', '')}"]
        section = card.get("section") or ""
        section_type = card.get("section_type") or ""
        if section or section_type:
            lines.append(
                f"{RENDER_TEXTS['section']}: {section}"
                + (f" ({section_type})" if section_type else "")
            )
        if card.get("figure_or_table"):
            lines.append(f"{RENDER_TEXTS['figure_or_table']}: {card['figure_or_table']}")
        lines.append(f"{RENDER_TEXTS['finding']}: {card.get('finding', '')}")
        if card.get("context"):
            lines.append(f"{RENDER_TEXTS['context']}: {card['context']}")
        lines.append(f"{RENDER_TEXTS['quotes']}:")
        lines.extend(f"- {anchor.get('text', '')}" for anchor in card.get("anchors") or [])
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
