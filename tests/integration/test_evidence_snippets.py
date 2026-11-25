"""Integration tests for the evidence-snippet experiments (predict and judge) with scripted LLMs.

The experiments are defined in configs/experiment/predict/*_evidence_snippets.yaml and
configs/experiment/evaluate/*_snippet_judge.yaml. Real model outputs need a live backend, so the LLMs are
replaced by scripted ones; the configs, prompts, schemas and reference files are the real ones.
"""

import json
from typing import Any

from datasets import Dataset
from hydra.core.global_hydra import GlobalHydra
from hydra.utils import instantiate
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from omegaconf import open_dict
import pandas as pd
import pytest

from kibad_llm.config import PROJ_ROOT
from kibad_llm.extractors.snippets import CompactText
from kibad_llm.llms.base import LLM
from tests.conftest import cfg_global

# In the fixture, this sentence is set in bold across a line break: "**THG-Emissionen aus Moorböden können nur
# durch**\n**Wiedervernässung reduziert werden.**"
ANCHOR = "THG-Emissionen aus Moorböden können nur durch Wiedervernässung reduziert werden."

EXPERIMENTS = {
    # predict experiment: (evaluate experiment, label field, reference file, reference id column)
    "ecosystemservice_evidence_snippets": (
        "ecosystem_service_snippet_judge",
        "ecosystem_service_trends",
        "data/interim/ecosystem_services/wald_devset_processed.csv",
    ),
    "organism_trends_evidence_snippets": (
        "organism_trends_snippet_judge",
        "organism_trends",
        "data/external/organism_trends/Referenz_Wald_korrigiert_angepasst.csv",
    ),
}


def _notes() -> dict[str, str]:
    """Return complete notes as the model would."""
    return {
        "document_language": "Deutsch",
        "study_topic": "Photovoltaik auf Moorböden",
        "study_design": "",
        "study_area": "Deutschland",
        "time_period": "",
        "organisms": "",
        "variables": "THG-Emissionen",
        "current_section": "Hintergrund",
        "open_points": "",
    }


class ScriptedExtractionLLM(LLM):
    """Answer snippet calls with a finding if the chunk contains ANCHOR, and label calls with no labels."""

    def __init__(self, label_field: str) -> None:
        """Store the label field of the task schema."""
        self.label_field = label_field
        self.calls: list[tuple[str, str]] = []

    def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
        """Return a schema-conform response for the snippet or label pass."""
        system, user = messages[0].content, messages[-1].content
        if "Belegstellen" in system:
            self.calls.append(("snippets", user))
            findings = []
            if CompactText.compact(ANCHOR) in CompactText.compact(user):
                findings.append(
                    {
                        "section": "Hintergrund",
                        "section_type": "introduction",
                        "finding": "Nur Wiedervernässung reduziert THG-Emissionen aus Moorböden.",
                        "context": "",
                        "figure_or_table": "",
                        "anchors": [ANCHOR],
                    }
                )
            content = {"notes": _notes(), "findings": findings}
        else:
            self.calls.append(("labels", user))
            content = {self.label_field: []}
        return ChatResponse(message=ChatMessage(content=json.dumps(content)))


class AlwaysMatchJudge(LLM):
    """Rate every candidate in the prompt as a match and record the prompts."""

    def __init__(self) -> None:
        """Initialize the prompt record."""
        self.prompts: list[str] = []

    def call_llm_chat_with_guided_decoding(self, messages, **kwargs) -> ChatResponse:
        """Return a match for each candidate id found in the prompt."""
        prompt = messages[-1].content
        self.prompts.append(prompt)
        ids = [line.split()[-1] for line in prompt.splitlines() if line.startswith("## Textstelle ")]
        judgements = [
            {"candidate_id": i, "rationale": "same", "verdict": "match", "result_agreement": "agrees"}
            for i in ids
        ]
        return ChatResponse(message=ChatMessage(content=json.dumps({"judgements": judgements})))


@pytest.mark.parametrize("predict_experiment", list(EXPERIMENTS))
def test_evidence_snippet_experiment(tmp_path, predict_experiment: str) -> None:
    """Run a predict experiment on a fixture document, then judge its snippets with the evaluate experiment."""
    evaluate_experiment, label_field, reference_file = EXPERIMENTS[predict_experiment]
    text = json.loads((PROJ_ROOT / "tests/fixtures/markdown/25ABQZIH.pdf.json").read_text())["text"]

    # --- prediction ---
    cfg = cfg_global(
        out_dir=tmp_path,
        overrides=[f"experiment/predict={predict_experiment}", "extractor/llm=dry-run"],
    )
    extractor = instantiate(cfg.extractor, _convert_="all")
    GlobalHydra.instance().clear()
    llm = ScriptedExtractionLLM(label_field)
    result = extractor(text=text, text_id="25ABQZIH.pdf", llm=llm, return_reasoning=False)

    kinds = [kind for kind, _ in llm.calls]
    assert kinds == ["snippets", "snippets", "labels"]
    assert "Noch keine Notizen" in llm.calls[0][1]
    assert "- Thema: Photovoltaik auf Moorböden" in llm.calls[1][1]
    assert result["errors_list"] == [[]] * 3, result["errors_list"]

    structured = result["structured"]
    assert set(structured) == {label_field, "study_notes", "evidence_findings"}
    assert structured[label_field] == []
    (card,) = structured["evidence_findings"]
    assert card["located"] and card["anchors"][0]["match"] == "normalized"
    assert "**Wiedervernässung reduziert werden.**" in card["snippets"][0]["text"]
    assert len(card["snippets"][0]["text"]) <= cfg.extractor.max_snippet_chars
    assert card["snippets"][0]["text"] in llm.calls[2][1]

    # the result can be written as a prediction line
    prediction_file = tmp_path / "predictions.jsonl"
    Dataset.from_list([{"file_name": "25ABQZIH.pdf", **result}]).to_json(prediction_file)

    # --- judging: reuse the prediction for a document that has gold entries ---
    gold_key = str(pd.read_csv(PROJ_ROOT / reference_file, usecols=["Key"])["Key"].iloc[0])
    line = json.loads(prediction_file.read_text().splitlines()[0])
    with open(prediction_file, "a") as f:
        f.write(json.dumps({**line, "file_name": f"{gold_key}.pdf"}) + "\n")

    cfg = cfg_global(
        out_dir=tmp_path,
        config_name="evaluate.yaml",
        overrides=[f"experiment/evaluate={evaluate_experiment}", "extractor/llm@metric.llm=dry-run"],
    )
    with open_dict(cfg):
        cfg.dataset.predictions.file = str(prediction_file)
        cfg.dataset.allow_missing_predictions = True
        cfg.metric.details_file = str(tmp_path / "judgements.json")
    dataset = instantiate(cfg.dataset, _convert_="all")
    judge = AlwaysMatchJudge()
    metric = instantiate(cfg.metric, _convert_="all", llm=judge)
    text_fields = list(cfg.metric.text_fields)
    GlobalHydra.instance().clear()

    for record_id, example in dataset.items():
        metric.update(
            prediction=example["prediction"], reference=example["reference"], record_id=record_id
        )
    scores: dict[str, Any] = metric.compute()

    n_gold = scores["counts"]["gold_entries"]
    assert n_gold >= 1
    assert scores["counts"]["records_without_gold"] == 1
    assert scores["strict"]["recall"] == 1.0 and scores["strict"]["precision"] == 1.0
    assert scores["result_agreement"]["agrees"] == n_gold
    assert len(judge.prompts) == n_gold
    prompt = judge.prompts[0]
    assert "# Gold-Eintrag" in prompt and "## Textstelle F1" in prompt
    assert any(f"- {field}: " in prompt for field in text_fields)
    assert (tmp_path / "judgements.json").exists()
