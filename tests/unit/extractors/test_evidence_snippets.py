"""Unit tests for the EvidenceSnippetExtractor with a scripted LLM."""

import json
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
import pytest

from kibad_llm.extractors.evidence_snippets import EvidenceSnippetExtractor, _update_notes
from kibad_llm.llms.base import LLM
from kibad_llm.schema.evidence_snippets import ChunkEvidence

FIRST = "Methods. We compared mixed and pure beech stands in the Hainich forest. "
SECOND = "Results. Mixed stands produced more biomass than pure stands (p < 0.01)."
TEXT = FIRST + SECOND

SNIPPET_TEMPLATE = {
    "system_message": "Task: {task_description}\n{schema_description}",
    "user_message": "Notes:\n{running_notes}\nChunk {chunk_index}/{num_chunks}:\n{document}",
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
    assert [notes["current_section"] for notes in result["study_notes_list"]] == ["Methods", "Results"]

    (card,) = structured["evidence_findings"]
    assert card["id"] == "F1" and card["chunk_index"] == 1 and card["located"]
    assert card["anchors"][0]["in_chunk"] is True
    assert SECOND in card["snippets"][0]["text"]

    label_document = llm.calls[2][-1].content
    assert "## Textstelle F1" in label_document and SECOND in label_document
    assert "Fagus sylvatica" in label_document

    assert result["errors_list"] == [[], [], []]
    assert result["character_start_list"][:2] == [0, len(FIRST)]


def test_label_pass_is_skipped_without_located_findings() -> None:
    """Without located findings, no label call is made and the label keys are None."""
    responses = [
        json.dumps({"notes": _notes(), "findings": [_finding("Not in the text at all, really not.")]}),
        json.dumps({"notes": _notes(), "findings": []}),
    ]
    llm = ScriptedLLM(responses)
    result = _extractor()(TEXT, "doc", llm=llm)

    assert len(llm.calls) == 2
    assert result["structured"]["trends"] is None
    (card,) = result["structured"]["evidence_findings"]
    assert card["located"] is False and card["snippets"] == []


def test_label_pass_can_be_disabled() -> None:
    """With label_pass=False, only the chunks are processed."""
    responses = [
        json.dumps({"notes": _notes(), "findings": [_finding("We compared mixed and pure beech stands")]}),
        json.dumps({"notes": _notes(), "findings": []}),
    ]
    llm = ScriptedLLM(responses)
    result = _extractor(label_pass=False)(TEXT, "doc", llm=llm)
    assert len(llm.calls) == 2
    assert result["structured"]["evidence_findings"][0]["located"] is True
    assert result["structured"]["trends"] is None


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
    assert _update_notes(notes, {"a": "new", "b": "", "c": None}) == {"a": "new", "b": "keep", "c": ""}
    assert _update_notes(notes, None) == notes


def test_invalid_snippet_sizes() -> None:
    """min_snippet_chars must not exceed max_snippet_chars."""
    with pytest.raises(ValueError):
        _extractor(min_snippet_chars=100, max_snippet_chars=10)
