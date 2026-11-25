"""Unit tests for the EvidenceSnippetExtractor with a scripted LLM."""

import json
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
import pytest

from kibad_llm.extractors.evidence_snippets import (
    EvidenceSnippetExtractor,
    _update_notes,
)
from kibad_llm.llms.base import LLM
from kibad_llm.schema.evidence_snippets import ChunkEvidence, FindingAggregation

FIRST = "Methods. We compared mixed and pure beech stands in the Hainich forest. "
SECOND = "Results. Mixed stands produced more biomass than pure stands (p < 0.01)."
TEXT = FIRST + SECOND

SNIPPET_TEMPLATE = {
    "system_message": "Task: {task_description}\n{schema_description}",
    "user_message": "Notes:\n{running_notes}\nChunk {chunk_index}/{num_chunks}:\n{document}",
}
AGGREGATION_TEMPLATE = {
    "system_message": "Group. {task_description}",
    "user_message": "{document}",
}
LABEL_TEMPLATE = {"system_message": "Labels.", "user_message": "{document}"}
LABEL_SCHEMA = {
    "type": "object",
    "properties": {"trends": {"type": "array", "items": {"type": "string"}}},
    "required": ["trends"],
}

NOTES_FIELDS = list(ChunkEvidence.model_json_schema()["$defs"]["StudyNotes"]["properties"])


def _notes(**values: str) -> dict[str, str]:
    """Return complete notes with the given values and empty strings otherwise."""
    return {field: values.get(field, "") for field in NOTES_FIELDS}


def _finding(anchor: str, finding: str = "Mixed > pure") -> dict[str, Any]:
    """Return a finding with all required fields."""
    return {
        "section": "Results",
        "section_type": "results",
        "finding": finding,
        "context": "",
        "figure_or_table": "",
        "anchors": [anchor],
    }


class ScriptedLLM(LLM):
    """Return the scripted responses in order and record the received messages."""

    def __init__(self, responses: list[str]) -> None:
        """Store the responses."""
        self.responses = list(responses)
        self.calls: list[list[Any]] = []

    def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
        """Return the next scripted response."""
        self.calls.append(messages)
        return ChatResponse(message=ChatMessage(content=self.responses[len(self.calls) - 1]))


def _extractor(**kwargs: Any) -> EvidenceSnippetExtractor:
    """Create an extractor that splits TEXT into two chunks."""
    config: dict[str, Any] = {
        "snippet_prompt_template": SNIPPET_TEMPLATE,
        "snippet_schema": ChunkEvidence.model_json_schema(),
        "snippet_task_description": "Find biomass effects.",
        "aggregation_prompt_template": AGGREGATION_TEMPLATE,
        "aggregation_schema": FindingAggregation.model_json_schema(),
        "max_char_buffer": len(FIRST),
        "min_snippet_chars": 10,
        "max_snippet_chars": 500,
        "return_as_list": ["errors", "character_start"],
        "prompt_template": LABEL_TEMPLATE,
        "schema": LABEL_SCHEMA,
        "use_guided_decoding": True,
        "validate_with_schema": True,
    }
    return EvidenceSnippetExtractor(**{**config, **kwargs})


def test_extractor_carries_notes_builds_snippets_and_labels() -> None:
    """Notes reach the next chunk prompt, anchors become snippets, and the label pass sees the snippets."""
    responses = [
        json.dumps(
            {
                "notes": _notes(study_topic="Mixed vs. pure {beech}", current_section="Methods"),
                "findings": [],
            }
        ),
        json.dumps(
            {
                "notes": _notes(current_section="Results", organisms="Fagus sylvatica"),
                "findings": [_finding("Mixed stands produced more biomass than pure stands")],
            }
        ),
        json.dumps({"trends": ["positive"]}),
    ]
    llm = ScriptedLLM(responses)
    result = _extractor()(text=TEXT, text_id="doc", llm=llm)

    assert len(llm.calls) == 3
    first_user, second_user = llm.calls[0][-1].content, llm.calls[1][-1].content
    assert "Noch keine Notizen" in first_user and "Chunk 1/2" in first_user
    # braces in the notes stay literal; empty updates do not erase earlier notes
    assert "- Thema: Mixed vs. pure {beech}" in second_user and "Chunk 2/2" in second_user
    assert "Task: Find biomass effects." in llm.calls[0][0].content

    structured = result["structured"]
    assert structured["trends"] == ["positive"]
    assert structured["study_notes"]["study_topic"] == "Mixed vs. pure {beech}"
    assert structured["study_notes"]["current_section"] == "Results"
    assert [notes["current_section"] for notes in result["study_notes_list"]] == [
        "Methods",
        "Results",
    ]

    (raw_card,) = structured["evidence_findings_raw"]
    assert raw_card["id"] == "F1" and raw_card["chunk_index"] == 1 and raw_card["located"]
    assert raw_card["anchors"][0]["in_chunk"] is True
    assert SECOND in raw_card["snippets"][0]["text"]
    # a single located finding needs no aggregation call
    (card,) = structured["evidence_findings"]
    assert card["id"] == "A1" and card["member_ids"] == ["F1"]
    assert card["snippets"] == raw_card["snippets"]

    label_document = llm.calls[2][-1].content
    assert "## Textstelle A1" in label_document and SECOND in label_document
    assert "Fagus sylvatica" in label_document

    assert result["errors_list"] == [[], [], []]
    assert result["character_start_list"][:2] == [0, len(FIRST)]


def test_label_pass_is_skipped_without_located_findings() -> None:
    """Without located findings, no label call is made and the label keys are None."""
    responses = [
        json.dumps(
            {"notes": _notes(), "findings": [_finding("Not in the text at all, really not.")]}
        ),
        json.dumps({"notes": _notes(), "findings": []}),
    ]
    llm = ScriptedLLM(responses)
    result = _extractor()(TEXT, "doc", llm=llm)

    assert len(llm.calls) == 2
    assert result["structured"]["trends"] is None
    assert result["structured"]["evidence_findings"] == []
    (card,) = result["structured"]["evidence_findings_raw"]
    assert card["located"] is False and card["snippets"] == []


def test_label_pass_can_be_disabled() -> None:
    """With label_pass=False, only the chunks are processed."""
    responses = [
        json.dumps(
            {"notes": _notes(), "findings": [_finding("We compared mixed and pure beech stands")]}
        ),
        json.dumps({"notes": _notes(), "findings": []}),
    ]
    llm = ScriptedLLM(responses)
    result = _extractor(label_pass=False)(TEXT, "doc", llm=llm)
    assert len(llm.calls) == 2
    assert result["structured"]["evidence_findings"][0]["located"] is True
    assert result["structured"]["trends"] is None


def _two_findings_responses() -> list[str]:
    """Return chunk responses with one located finding per chunk."""
    return [
        json.dumps(
            {
                "notes": _notes(),
                "findings": [_finding("We compared mixed and pure beech stands", "design")],
            }
        ),
        json.dumps(
            {
                "notes": _notes(),
                "findings": [_finding("Mixed stands produced more biomass than pure stands")],
            }
        ),
    ]


def test_aggregation_merges_findings_and_keeps_all_snippets() -> None:
    """Grouped findings become one card with all member snippets; the label pass sees the merged card."""
    aggregation = {
        "groups": [
            {
                "finding_ids": ["F2", "F1", "F9"],
                "finding": "Mixed > pure (biomass)",
                "context": "",
            },
            {"finding_ids": ["F1"], "finding": "repeated id is ignored", "context": ""},
        ]
    }
    responses = [*_two_findings_responses(), json.dumps(aggregation), json.dumps({"trends": []})]
    llm = ScriptedLLM(responses)
    result = _extractor(min_snippet_chars=1, max_snippet_chars=60, snippet_merge_gap=0)(
        TEXT, "doc", llm=llm
    )

    assert len(llm.calls) == 4
    aggregation_prompt = llm.calls[2]
    assert aggregation_prompt[0].content == "Group. Find biomass effects."
    assert "## F1" in aggregation_prompt[-1].content and "## F2" in aggregation_prompt[-1].content

    (card,) = result["structured"]["evidence_findings"]
    assert card["member_ids"] == ["F1", "F2"] and card["chunk_indices"] == [0, 1]
    assert card["finding"] == "Mixed > pure (biomass)"
    assert [a["finding_id"] for a in card["anchors"]] == ["F1", "F2"]
    assert len(card["snippets"]) == 2
    assert [s["text"] for s in card["snippets"]] == [
        s["text"] for raw in result["structured"]["evidence_findings_raw"] for s in raw["snippets"]
    ]
    assert "## Textstelle A1" in llm.calls[3][-1].content
    assert result["errors_list"] == [[], [], [], []]


def test_failed_aggregation_keeps_findings_separate() -> None:
    """If the aggregation call fails, each located finding stays on its own and the error is recorded."""
    responses = [*_two_findings_responses(), "not json", json.dumps({"trends": []})]
    llm = ScriptedLLM(responses)
    result = _extractor()(TEXT, "doc", llm=llm)

    assert len(llm.calls) == 4
    assert result["errors_list"][2][0].startswith("JSONDecodeError")
    cards = result["structured"]["evidence_findings"]
    assert [c["member_ids"] for c in cards] == [["F1"], ["F2"]]
    assert [c["id"] for c in cards] == ["A1", "A2"]


def test_aggregation_can_be_disabled() -> None:
    """With aggregate_findings=False, no aggregation call is made."""
    responses = [*_two_findings_responses(), json.dumps({"trends": []})]
    llm = ScriptedLLM(responses)
    result = _extractor(aggregate_findings=False)(TEXT, "doc", llm=llm)
    assert len(llm.calls) == 3
    assert len(result["structured"]["evidence_findings"]) == 2


def test_failed_chunk_keeps_notes_and_records_error() -> None:
    """An invalid response is recorded as an error and the notes are kept."""
    responses = [
        json.dumps({"notes": _notes(study_topic="Biomass"), "findings": []}),
        "not json",
    ]
    llm = ScriptedLLM(responses)
    result = _extractor()(TEXT, "doc", llm=llm)
    assert result["errors_list"][0] == []
    assert result["errors_list"][1][0].startswith("JSONDecodeError")
    assert result["study_notes_list"][1]["study_topic"] == "Biomass"


def test_update_notes() -> None:
    """Non-empty values replace old ones, empty values do not erase, non-mappings are ignored."""
    notes = {"a": "old", "b": "keep"}
    assert _update_notes(notes, {"a": "new", "b": "", "c": None}) == {
        "a": "new",
        "b": "keep",
        "c": "",
    }
    assert _update_notes(notes, None) == notes


def test_invalid_configuration() -> None:
    """Inconsistent snippet sizes and aggregation without template are rejected."""
    with pytest.raises(ValueError):
        _extractor(min_snippet_chars=100, max_snippet_chars=10)
    with pytest.raises(ValueError):
        _extractor(aggregation_prompt_template=None)
