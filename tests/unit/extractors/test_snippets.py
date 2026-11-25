"""Unit tests for locating anchors and building evidence snippets."""

import pytest

from kibad_llm.extractors.snippets import (
    CompactText,
    aggregate_finding_cards,
    build_finding_card,
    expand_span,
    format_value,
    locate_anchor,
    merge_spans,
    render_aggregation_document,
    render_evidence_document,
    render_finding_card,
    render_notes,
)

TEXT = (
    "# Title\n\n"
    "Intro paragraph about forests.\n\n"
    "## Results\n\n"
    "Mixed stands produced **more biomass** than mono-\nspecific stands (p < 0.01). "
    "This held for all sites.\n\n"
    "Decomposition did not differ between the tree species “beech” and oak.\n"
)


def test_compact_text_maps_back_to_original_offsets() -> None:
    """Compact matches map to the first and last matched characters of the original text."""
    compact = CompactText("A **bold**-\nword")
    assert compact.text == "aboldword"
    found = compact.find("boldword")
    assert found is not None
    start, end = found
    assert "A **bold**-\nword"[start:end] == "bold**-\nword"


def test_locate_anchor_exact_ignores_whitespace() -> None:
    """Line breaks in the text do not prevent an exact match."""
    found = locate_anchor(TEXT, "This held for all sites.")
    assert found is not None
    start, end, match_type, in_window = found
    assert TEXT[start:end] == "This held for all sites."
    assert match_type == "exact"
    assert in_window is True


def test_locate_anchor_normalized_handles_markdown_hyphenation_and_quotes() -> None:
    """Markdown emphasis, line-end hyphenation and typographic quotes are tolerated."""
    found = locate_anchor(TEXT, "Mixed stands produced more biomass than monospecific stands")
    assert found is not None
    assert found[2] == "normalized"
    assert TEXT[found[0] : found[1]].startswith("Mixed stands produced **more biomass**")

    found = locate_anchor(
        TEXT, 'Decomposition did not differ between the tree species "beech" and oak.'
    )
    assert found is not None
    assert found[2] == "normalized"


def test_locate_anchor_with_ellipsis() -> None:
    """Parts separated by an ellipsis are located in order and the span covers all parts."""
    found = locate_anchor(TEXT, "Mixed stands produced more biomass ... for all sites")
    assert found is not None
    start, end, match_type, _ = found
    assert match_type == "ellipsis"
    assert TEXT[start:end].startswith("Mixed stands")
    assert TEXT[start:end].endswith("for all sites")


def test_locate_anchor_partial_match() -> None:
    """A paraphrased ending still locates the longest run of verbatim words."""
    found = locate_anchor(TEXT, "Decomposition did not differ between the tree species at all")
    assert found is not None
    assert found[2] == "partial"
    assert TEXT[found[0] : found[1]] == "Decomposition did not differ between the tree species"


def test_locate_anchor_unlocated_and_short_anchors() -> None:
    """Anchors that are not in the text, short anchors with differences, and empty anchors are not found."""
    assert locate_anchor(TEXT, "Grasslands stored more carbon than forests overall.") is None
    # differs only by Markdown, but too short for tolerant matching
    assert locate_anchor(TEXT, "more biomass than") is None
    assert locate_anchor(TEXT, "  ") is None


def test_locate_anchor_prefers_window_and_falls_back_to_full_text() -> None:
    """The search window is preferred; anchors outside it are found in the full text."""
    text = "Same sentence here.\n\nOther.\n\nSame sentence here."
    second = text.rindex("Same")
    found = locate_anchor(text, "Same sentence here.", window_start=second)
    assert found is not None and found[0] == second and found[3] is True

    found = locate_anchor(
        text, "Same sentence here.", window_start=second - 5, window_end=second - 1
    )
    assert found is not None and found[0] == 0 and found[3] is False


def test_expand_span_grows_to_paragraphs() -> None:
    """Short spans grow to their paragraph and then to neighbouring paragraphs."""
    start = TEXT.index("This held")
    end = start + len("This held for all sites.")
    new_start, new_end = expand_span(TEXT, start, end, min_chars=10, max_chars=500)
    assert TEXT[new_start:new_end].startswith("Mixed stands")
    assert TEXT[new_start:new_end].endswith("This held for all sites.")

    new_start, new_end = expand_span(TEXT, start, end, min_chars=200, max_chars=500)
    snippet = TEXT[new_start:new_end]
    assert "Decomposition" in snippet and "## Results" in snippet
    assert len(snippet) <= 500


def test_expand_span_uses_sentences_for_long_paragraphs() -> None:
    """In a paragraph longer than max_chars, whole sentences around the span are used."""
    sentences = [f"Sentence number {i} has some words." for i in range(30)]
    text = " ".join(sentences)
    start = text.index("Sentence number 15")
    end = start + len(sentences[15])
    new_start, new_end = expand_span(text, start, end, min_chars=100, max_chars=150)
    snippet = text[new_start:new_end]
    assert sentences[15] in snippet
    assert 100 <= len(snippet) <= 150
    assert snippet.startswith("Sentence number") and snippet.endswith(".")


def test_expand_span_keeps_spans_longer_than_max() -> None:
    """A span longer than max_chars is returned unchanged."""
    assert expand_span(TEXT, 0, 50, min_chars=10, max_chars=20) == (0, 50)


def test_merge_spans() -> None:
    """Overlapping and nearby spans are merged, distant ones are kept apart."""
    assert merge_spans([(50, 60), (0, 10), (5, 20), (25, 30)], max_gap=5) == [
        (0, 30),
        (50, 60),
    ]


def test_build_finding_card() -> None:
    """Located anchors produce merged snippets; unlocated anchors are kept with empty offsets."""
    finding = {
        "section": "Results",
        "section_type": "results",
        "finding": "Mixed stands produce more biomass.",
        "context": "",
        "figure_or_table": "",
        "anchors": ["This held for all sites.", "An anchor that is nowhere in the text at all."],
    }
    card = build_finding_card(
        finding,
        finding_id="F1",
        chunk_index=0,
        text=TEXT,
        compact_text=CompactText(TEXT),
        chunk_start=0,
        chunk_end=len(TEXT),
        min_snippet_chars=10,
        max_snippet_chars=500,
    )
    assert card["id"] == "F1"
    assert card["located"] is True
    assert [a["match"] for a in card["anchors"]] == ["exact", None]
    assert card["anchors"][1]["start"] is None
    assert len(card["snippets"]) == 1
    snippet = card["snippets"][0]
    assert TEXT[snippet["start"] : snippet["end"]] == snippet["text"]
    assert "Mixed stands" in snippet["text"]


@pytest.mark.parametrize(
    ("value", "expected"), [(1998.0, "1998"), (0.5, "0.5"), (["a", 2.0], "a, 2")]
)
def test_format_value(value, expected) -> None:
    """Whole floats are shown without decimals and lists are joined."""
    assert format_value(value) == expected


def test_rendering() -> None:
    """Notes skip empty and hidden fields; cards show snippets or the unlocated quotes."""
    notes = {"study_topic": "Forests", "time_period": "", "current_section": "Results"}
    assert render_notes({}, empty_text="none") == "none"
    assert render_notes(notes) == "- Thema: Forests\n- Aktueller Abschnitt: Results"

    card = {
        "id": "F2",
        "section": "Results",
        "section_type": "results",
        "finding": "Effect.",
        "context": "",
        "figure_or_table": "Fig. 2",
        "anchors": [{"text": "quote"}],
        "snippets": [],
    }
    rendered = render_finding_card(card)
    assert rendered.startswith(
        "## Textstelle F2\nAbschnitt: Results (results)\nAbbildung/Tabelle: Fig. 2"
    )
    assert "Zitate (nicht im Text gefunden): quote" in rendered

    document = render_evidence_document(notes, [{**card, "snippets": [{"text": "Snippet text."}]}])
    assert "- Thema: Forests" in document
    assert "Aktueller Abschnitt" not in document
    assert "Auszug aus der Studie:\nSnippet text." in document


def _card(card_id: str, start: int, end: int, chunk_index: int = 0, **fields: str) -> dict:
    """Return a located finding card with one snippet of TEXT."""
    return {
        "id": card_id,
        "chunk_index": chunk_index,
        "section": fields.get("section", "Results"),
        "section_type": fields.get("section_type", "results"),
        "finding": fields.get("finding", f"finding {card_id}"),
        "context": fields.get("context", ""),
        "figure_or_table": fields.get("figure_or_table", ""),
        "anchors": [{"text": f"quote {card_id}", "start": start, "end": end, "match": "exact"}],
        "snippets": [{"start": start, "end": end, "text": TEXT[start:end]}],
        "located": True,
    }


def test_aggregate_finding_cards() -> None:
    """Groups merge cards in text order; unknown and repeated IDs are ignored; ungrouped cards stay alone."""
    decomposition = TEXT.index("Decomposition")
    cards = [
        _card("F1", decomposition, decomposition + 13, chunk_index=1, section="Results"),
        _card(
            "F2",
            0,
            7,
            section="Abstract",
            section_type="title_or_abstract",
            figure_or_table="Fig. 1",
        ),
        _card("F3", 9, 14, context="intro context"),
    ]
    groups = [
        {"finding_ids": ["F1", "F2", "F7"], "finding": "merged", "context": ""},
        {"finding_ids": ["F2"], "finding": "ignored", "context": ""},
        "not a group",
    ]
    aggregated = aggregate_finding_cards(cards, groups, text=TEXT, merge_gap=0)

    assert [c["id"] for c in aggregated] == ["A1", "A2"]
    merged, single = aggregated
    assert merged["member_ids"] == ["F2", "F1"] and merged["chunk_indices"] == [0, 1]
    assert merged["finding"] == "merged" and merged["context"] == ""
    assert merged["section"] == "Abstract | Results"
    assert merged["section_type"] == "title_or_abstract, results"
    assert merged["figure_or_table"] == "Fig. 1"
    assert [a["finding_id"] for a in merged["anchors"]] == ["F2", "F1"]
    assert [s["text"] for s in merged["snippets"]] == ["# Title", "Decomposition"]
    assert single["member_ids"] == ["F3"]
    assert single["finding"] == "finding F3" and single["context"] == "intro context"


def test_aggregate_finding_cards_merges_overlapping_snippets_and_falls_back() -> None:
    """Overlapping member snippets are merged and re-sliced; without groups every card stays alone."""
    cards = [_card("F1", 0, 10), _card("F2", 5, 20)]
    (merged,) = aggregate_finding_cards(
        cards, [{"finding_ids": ["F1", "F2"], "finding": "", "context": ""}], text=TEXT
    )
    assert merged["snippets"] == [{"start": 0, "end": 20, "text": TEXT[:20]}]
    assert merged["finding"] == "finding F1"

    assert [c["member_ids"] for c in aggregate_finding_cards(cards, None, text=TEXT)] == [
        ["F1"],
        ["F2"],
    ]


def test_render_aggregation_document() -> None:
    """The aggregation input shows notes and compact cards with quotes, but no snippets."""
    card = _card("F1", 0, 7, figure_or_table="Tab. 2", context="ctx")
    document = render_aggregation_document({"study_topic": "Forests", "open_points": "x"}, [card])
    assert "- Thema: Forests" in document and "Offene Punkte" not in document
    assert "## F1\nAbschnitt: Results (results)\nAbbildung/Tabelle: Tab. 2" in document
    assert "Ergebnis: finding F1\nKontext: ctx\nZitate:\n- quote F1" in document
    assert "# Title" not in document
