"""Unit tests for the SnippetJudgeMetric with a scripted judge."""

import json
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
import pytest

from kibad_llm.llms.base import LLM
from kibad_llm.metrics.snippet_judge import SnippetJudgeMetric
from kibad_llm.schema.evidence_snippets import SnippetJudgeOutput

TEMPLATE = {"system_message": "Judge. {task_description}", "user_message": "{document}"}


def _card(card_id: str, located: bool = True) -> dict[str, Any]:
    """Return a minimal finding card."""
    return {
        "id": card_id,
        "section": "Results",
        "section_type": "results",
        "finding": f"finding {card_id}",
        "context": "",
        "figure_or_table": "",
        "anchors": [{"text": "quote"}],
        "snippets": [{"start": 0, "end": 4, "text": f"snippet {card_id}"}] if located else [],
        "located": located,
    }


class VerdictLLM(LLM):
    """Return verdicts per (gold ÖSL, candidate id) and record the prompts."""

    def __init__(self, verdicts: dict[tuple[str, str], tuple[str, str]]) -> None:
        """Store the verdicts as {(gold ÖSL, candidate id): (verdict, result_agreement)}."""
        self.verdicts = verdicts
        self.prompts: list[str] = []

    def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
        """Answer for all candidates mentioned in the prompt."""
        prompt = messages[-1].content
        self.prompts.append(prompt)
        gold = next(line[len("- ÖSL: ") :] for line in prompt.splitlines() if line.startswith("- ÖSL: "))
        judgements = [
            {"candidate_id": cid, "rationale": "r", "verdict": v, "result_agreement": a}
            for (g, cid), (v, a) in self.verdicts.items()
            if g == gold and f"## Textstelle {cid}\n" in prompt
        ]
        # unknown ids are ignored by the metric
        judgements.append(
            {"candidate_id": "X9", "rationale": "", "verdict": "match", "result_agreement": "agrees"}
        )
        return ChatResponse(message=ChatMessage(content=json.dumps({"judgements": judgements})))


def _metric(llm: LLM | None, **kwargs: Any) -> SnippetJudgeMetric:
    """Create a metric for ecosystem-service-like gold entries."""
    return SnippetJudgeMetric(
        reference_field="trends",
        prompt_template=TEMPLATE,
        schema=SnippetJudgeOutput.model_json_schema(),
        llm=llm,
        task_description="ÖSL relations.",
        text_fields=["Notiz"],
        **kwargs,
    )


def test_snippet_judge_scores_and_details(tmp_path) -> None:
    """Strict and lenient scores, result agreement, batching and the details file."""
    llm = VerdictLLM(
        {
            ("Zersetzung", "F1"): ("match", "agrees"),
            ("Zersetzung", "F2"): ("partial", "unclear"),
            ("Biomasseproduktion", "F2"): ("match", "conflicts"),
            ("Biomasseproduktion", "F3"): ("match", "agrees"),
        }
    )
    details_file = tmp_path / "judgements.json"
    metric = _metric(llm, max_candidates_per_call=2, details_file=str(details_file))
    prediction = {
        "study_notes": {"study_topic": "Forest study", "current_section": "Results"},
        "evidence_findings": [_card("F1"), _card("F2"), _card("F3"), _card("F4", located=False)],
    }
    reference = {
        "trends": [
            {"ÖSL": "Zersetzung", "Einfluss": "ja", "Notiz": "Buche vs. Eiche"},
            {"ÖSL": "Biomasseproduktion", "Einfluss": "pos"},
            {"ÖSL": "Kohlenstoffspeicherung", "Einfluss": "neu"},
        ]
    }
    metric.update(prediction=prediction, reference=reference, record_id="doc1")
    metric.update(prediction={"evidence_findings": [_card("F1")]}, reference={}, record_id="doc2")
    result = metric.compute()

    # 3 gold entries x 2 batches (3 located candidates, 2 per call)
    assert len(llm.prompts) == 6
    first_prompt = llm.prompts[0]
    assert "Labels:\n- ÖSL: Zersetzung\n- Einfluss: ja" in first_prompt
    assert "Notizen der Annotierenden:\n- Notiz: Buche vs. Eiche" in first_prompt
    assert "- Thema: Forest study" in first_prompt and "Aktueller Abschnitt" not in first_prompt
    assert "Textstelle F4" not in "".join(llm.prompts)

    assert result["counts"] == {
        "gold_entries": 3,
        "gold_entries_match": 2,
        "gold_entries_match_or_partial": 2,
        "candidates": 3,
        "candidates_match": 3,
        "candidates_match_or_partial": 3,
        "candidates_not_judged": 0,
        "findings": 5,
        "findings_unlocated": 1,
        "records_without_gold": 1,
        "candidates_in_records_without_gold": 1,
        "judge_calls": 6,
        "judge_errors": 0,
    }
    assert result["strict"]["recall"] == pytest.approx(2 / 3)
    assert result["strict"]["precision"] == pytest.approx(1.0)
    assert result["strict"]["f1"] == pytest.approx(0.8)
    # Biomasseproduktion: one matching candidate agrees, so the entry counts as agreeing
    assert result["result_agreement"] == {"agrees": 2, "conflicts": 0, "unclear": 0}

    details = json.loads(details_file.read_text())
    assert len(details["gold_entries"]) == 3
    verdicts = {j["candidate_id"]: j["verdict"] for j in details["gold_entries"][0]["judgements"]}
    assert verdicts == {"F1": "match", "F2": "partial", "F3": "not_judged"}
    # state is reset after compute
    assert metric.gold_entries == [] and metric.candidates == []


def test_snippet_judge_without_llm_or_candidates() -> None:
    """Without an LLM, candidates are not judged; without candidates, gold entries are missed."""
    metric = _metric(None)
    metric.update(
        prediction={"evidence_findings": [_card("F1")]},
        reference={"trends": [{"ÖSL": "Zersetzung"}]},
        record_id="doc1",
    )
    metric.update(prediction=None, reference={"trends": ["scalar label"]}, record_id="doc2")
    result = metric.compute()
    assert result["counts"]["gold_entries"] == 2
    assert result["counts"]["gold_entries_match"] == 0
    assert result["counts"]["candidates_not_judged"] == 1
    assert result["counts"]["judge_calls"] == 0
    assert result["strict"] == {"precision": 0.0, "recall": 0.0, "f1": 0.0}


def test_snippet_judge_invalid_batch_size() -> None:
    """At least one candidate per call is required."""
    with pytest.raises(ValueError):
        _metric(None, max_candidates_per_call=0)
