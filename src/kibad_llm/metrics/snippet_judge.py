"""LLM-judge metric that compares evidence snippets with gold entries.

Classes:
    SnippetJudgeMetric: Ask an LLM whether the evidence snippets of a document support each gold entry.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Mapping, Sequence
import json
import logging
import os
from typing import Any

from kibad_llm.extractors.base import extract_from_text_lenient
from kibad_llm.extractors.evidence_snippets import FINDINGS_KEY, NOTES_KEY
from kibad_llm.extractors.snippets import (
    NOTES_FIELDS_HIDDEN_AFTER_READING,
    format_value,
    render_finding_card,
    render_notes,
)
from kibad_llm.llms.base import LLM
from kibad_llm.llms.request import prefill_template_fields
from kibad_llm.metric import Metric
from kibad_llm.schema.evidence_snippets import RENDER_TEXTS

logger = logging.getLogger(__name__)

VERDICTS = ("match", "partial", "no_match")
RESULT_AGREEMENTS = ("agrees", "conflicts", "unclear")
NOT_JUDGED = "not_judged"


def _safe_div(numerator: float, denominator: float) -> float:
    """Divide, returning 0.0 for a zero denominator.

    Args:
        numerator: Numerator.
        denominator: Denominator.

    Returns:
        The quotient, or 0.0 if `denominator` is 0.
    """
    return numerator / denominator if denominator else 0.0


def _f1(precision: float, recall: float) -> float:
    """Return the harmonic mean of precision and recall.

    Args:
        precision: Precision.
        recall: Recall.

    Returns:
        The F1 score, or 0.0 if both are 0.
    """
    return _safe_div(2 * precision * recall, precision + recall)


class SnippetJudgeMetric(Metric):
    """Ask an LLM whether the evidence snippets of a document support each gold entry.

    Predictions are the `structured` outputs of the
    [`EvidenceSnippetExtractor`][kibad_llm.extractors.evidence_snippets.EvidenceSnippetExtractor]. For each
    gold entry, the judge sees the gold labels, the gold text fields (annotator notes etc.), the study notes
    and all candidate finding cards of the document (in batches), and returns a verdict per candidate:
    `match`, `partial` or `no_match`, plus whether the reported result agrees with the gold entry.

    Reported scores (strict counts only `match`, lenient also `partial`):

    - recall: share of gold entries supported by at least one candidate,
    - precision: share of candidates (in documents with gold entries) that support at least one gold entry,
    - f1 of both,
    - result agreement: for gold entries with a `match`, whether the best matching candidate's result
      `agrees`, `conflicts` or is `unclear`.

    Candidates in documents without gold entries cannot be judged against the gold data; they are only
    counted. Note that precision is affected by duplicates: the same finding reported in the abstract and
    in the results counts as two candidates.

    Attributes:
        reference_field: Field of the reference that holds the list of gold entries.
        prompt_template: Prompt template of the judge. Besides `{document}` and `{schema_description}`, it
            can use `{task_description}`.
        schema: JSON schema of the judge output (see
            [`SnippetJudgeOutput`][kibad_llm.schema.evidence_snippets.SnippetJudgeOutput]).
        llm: LLM backend of the judge. If None, no calls are made and all candidates are `not_judged`.
        task_description: Task-specific explanation for the judge.
        label_fields: Gold fields shown as labels. If None, all fields not in `text_fields`.
        text_fields: Gold fields shown as annotator text.
        findings_field: Prediction field with the finding cards.
        notes_field: Prediction field with the study notes.
        include_unlocated: Whether candidates without a located snippet are judged as well.
        max_candidates_per_call: Maximum number of candidates per judge call.
        details_file: If set, per-entry judgements are written to this JSON file in `compute`.
        call_kwargs: Further keyword arguments for
            [`extract_from_text_lenient`][kibad_llm.extractors.base.extract_from_text_lenient].
    """

    def __init__(
        self,
        reference_field: str,
        prompt_template: dict[str, Any],
        schema: dict[str, Any],
        llm: LLM | None = None,
        task_description: str = "",
        label_fields: list[str] | None = None,
        text_fields: list[str] | None = None,
        findings_field: str = FINDINGS_KEY,
        notes_field: str = NOTES_KEY,
        include_unlocated: bool = False,
        max_candidates_per_call: int = 10,
        details_file: str | None = None,
        **call_kwargs: Any,
    ) -> None:
        """Store the configuration and reset the state.

        Args:
            reference_field: Field of the reference that holds the list of gold entries.
            prompt_template: Prompt template of the judge.
            schema: JSON schema of the judge output.
            llm: LLM backend of the judge.
            task_description: Task-specific explanation for the judge.
            label_fields: Gold fields shown as labels.
            text_fields: Gold fields shown as annotator text.
            findings_field: Prediction field with the finding cards.
            notes_field: Prediction field with the study notes.
            include_unlocated: Whether candidates without a located snippet are judged as well.
            max_candidates_per_call: Maximum number of candidates per judge call.
            details_file: If set, per-entry judgements are written to this JSON file in `compute`.

        Keyword Args:
            **call_kwargs (Any): Further keyword arguments for the judge calls, e.g. `request_parameters`,
                `use_guided_decoding` or `return_reasoning`.

        Raises:
            ValueError: If `max_candidates_per_call` is not positive.
        """
        if max_candidates_per_call < 1:
            raise ValueError("max_candidates_per_call must be at least 1")
        self.reference_field = reference_field
        self.prompt_template = prefill_template_fields(
            prompt_template, {"task_description": task_description}
        )
        self.schema = schema
        self.llm = llm
        self.label_fields = label_fields
        self.text_fields = text_fields or []
        self.findings_field = findings_field
        self.notes_field = notes_field
        self.include_unlocated = include_unlocated
        self.max_candidates_per_call = max_candidates_per_call
        self.details_file = details_file
        self.call_kwargs = call_kwargs
        self.reset()

    def reset(self) -> None:
        """Reset the collected judgements."""
        self.gold_entries: list[dict[str, Any]] = []
        self.candidates: list[dict[str, Any]] = []
        self.counts: Counter[str] = Counter()

    def _render_gold_entry(self, entry: Mapping[str, Any]) -> str:
        """Render one gold entry with its labels and annotator text.

        Args:
            entry: Gold entry.

        Returns:
            Markdown with one list item per non-empty field.
        """
        label_fields = (
            self.label_fields
            if self.label_fields is not None
            else [k for k in entry if k not in self.text_fields]
        )

        def _items(fields: Sequence[str]) -> list[str]:
            return [
                f"- {field}: {format_value(entry[field])}"
                for field in fields
                if entry.get(field) not in (None, "", [])
            ]

        lines = [
            f"# {RENDER_TEXTS['gold_heading']}",
            f"{RENDER_TEXTS['gold_labels']}:",
            *(_items(label_fields) or [f"- {RENDER_TEXTS['gold_no_labels']}"]),
        ]
        text_items = _items(self.text_fields)
        if text_items:
            lines.extend(["", f"{RENDER_TEXTS['gold_text']}:", *text_items])
        return "\n".join(lines)

    def _judge(
        self,
        gold_entry: Mapping[str, Any],
        notes: Mapping[str, Any] | None,
        candidates: Sequence[Mapping[str, Any]],
        call_id: str,
    ) -> dict[str, dict[str, Any]]:
        """Judge one batch of candidates against one gold entry.

        Args:
            gold_entry: Gold entry.
            notes: Study notes of the document.
            candidates: Finding cards to judge.
            call_id: Identifier for logging.

        Returns:
            Judgements keyed by candidate id. Candidates the judge did not return are missing.
        """
        document = "\n\n".join(
            [
                self._render_gold_entry(gold_entry),
                f"# {RENDER_TEXTS['notes_heading_judge']}",
                render_notes(notes, hidden_fields=NOTES_FIELDS_HIDDEN_AFTER_READING),
                f"# {RENDER_TEXTS['candidates_heading']}",
                *(render_finding_card(c) for c in candidates),
            ]
        )
        result = extract_from_text_lenient(
            text=document,
            text_id=call_id,
            prompt_template=self.prompt_template,
            schema=self.schema,
            llm=self.llm,
            **self.call_kwargs,
        )
        if self.llm is not None:
            self.counts["judge_calls"] += 1
        if result.errors:
            self.counts["judge_errors"] += 1

        ids = {c["id"] for c in candidates}
        judgements: dict[str, dict[str, Any]] = {}
        structured = result.structured if isinstance(result.structured, Mapping) else {}
        for judgement in structured.get("judgements") or []:
            if not isinstance(judgement, Mapping):
                continue
            candidate_id = judgement.get("candidate_id")
            if (
                isinstance(candidate_id, str)
                and candidate_id in ids
                and candidate_id not in judgements
            ):
                judgements[candidate_id] = dict(judgement)
        return judgements

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Judge all candidates of one document against all its gold entries.

        Args:
            prediction: `structured` output of the evidence-snippet extractor, or None.
            reference: Reference dict with the gold entries at `reference_field`, or None/empty.
            record_id: Document id.
        """
        prediction = prediction if isinstance(prediction, Mapping) else {}
        cards = [c for c in prediction.get(self.findings_field) or [] if isinstance(c, Mapping)]
        self.counts["findings"] += len(cards)
        self.counts["findings_unlocated"] += sum(1 for c in cards if not c.get("located"))
        candidates = [c for c in cards if self.include_unlocated or c.get("located")]
        notes = prediction.get(self.notes_field)

        gold: Any = (reference or {}).get(self.reference_field) or []
        if not isinstance(gold, list):
            gold = [gold]
        # scalar gold entries (e.g. single labels) are shown under the name of the reference field
        gold = [e if isinstance(e, Mapping) else {self.reference_field: e} for e in gold]
        if not gold:
            self.counts["records_without_gold"] += 1
            self.counts["candidates_in_records_without_gold"] += len(candidates)
            return

        candidate_verdicts: dict[str, list[str]] = {c["id"]: [] for c in candidates}
        for j, entry in enumerate(gold):
            judgements: dict[str, dict[str, Any]] = {}
            for batch_start in range(0, len(candidates), self.max_candidates_per_call):
                batch = candidates[batch_start : batch_start + self.max_candidates_per_call]
                judgements.update(
                    self._judge(entry, notes, batch, call_id=f"{record_id}_gold_{j}_{batch_start}")
                )
            per_candidate = []
            for candidate in candidates:
                judgement = judgements.get(candidate["id"])
                verdict = judgement.get("verdict") if judgement else NOT_JUDGED
                if verdict not in VERDICTS:
                    verdict = NOT_JUDGED
                candidate_verdicts[candidate["id"]].append(verdict)
                per_candidate.append(
                    {
                        "candidate_id": candidate["id"],
                        "verdict": verdict,
                        "result_agreement": (judgement or {}).get("result_agreement"),
                        "rationale": (judgement or {}).get("rationale"),
                    }
                )
            self.gold_entries.append(
                {"record_id": record_id, "gold": dict(entry), "judgements": per_candidate}
            )
        for candidate in candidates:
            self.candidates.append(
                {
                    "record_id": record_id,
                    "candidate_id": candidate["id"],
                    "verdicts": candidate_verdicts[candidate["id"]],
                }
            )

    @staticmethod
    def _best(judgements: Sequence[Mapping[str, Any]]) -> tuple[str, str | None]:
        """Return the best verdict for a gold entry and the result agreement of its best candidates.

        Args:
            judgements: Per-candidate judgements for one gold entry.

        Returns:
            The best verdict (`match` > `partial` > `no_match` > `not_judged`) and, among the candidates
            with that verdict, the best result agreement (`agrees` > `conflicts` > `unclear`).
        """
        order = [*VERDICTS, NOT_JUDGED]
        if not judgements:
            return "no_match", None
        best = min((j["verdict"] for j in judgements), key=order.index)
        agreements = [j.get("result_agreement") for j in judgements if j["verdict"] == best]
        agreement = next((a for a in RESULT_AGREEMENTS if a in agreements), None)
        return best, agreement

    def _compute(self) -> dict[str, Any]:
        """Aggregate the judgements.

        Returns:
            Counts and scores, see the class docstring. Per-entry judgements are written to `details_file`
            if it is set.
        """
        gold_best = [self._best(entry["judgements"]) for entry in self.gold_entries]
        n_gold = len(gold_best)
        gold_match = sum(1 for verdict, _ in gold_best if verdict == "match")
        gold_lenient = sum(1 for verdict, _ in gold_best if verdict in ("match", "partial"))
        agreement = Counter(a or "unclear" for verdict, a in gold_best if verdict == "match")

        n_candidates = len(self.candidates)
        candidates_match = sum(1 for c in self.candidates if "match" in c["verdicts"])
        candidates_lenient = sum(
            1 for c in self.candidates if {"match", "partial"} & set(c["verdicts"])
        )
        candidates_not_judged = sum(
            1 for c in self.candidates if c["verdicts"] and set(c["verdicts"]) == {NOT_JUDGED}
        )

        recall = _safe_div(gold_match, n_gold)
        precision = _safe_div(candidates_match, n_candidates)
        recall_lenient = _safe_div(gold_lenient, n_gold)
        precision_lenient = _safe_div(candidates_lenient, n_candidates)

        result: dict[str, Any] = {
            "strict": {"precision": precision, "recall": recall, "f1": _f1(precision, recall)},
            "lenient": {
                "precision": precision_lenient,
                "recall": recall_lenient,
                "f1": _f1(precision_lenient, recall_lenient),
            },
            "result_agreement": {key: agreement.get(key, 0) for key in RESULT_AGREEMENTS},
            "counts": {
                "gold_entries": n_gold,
                "gold_entries_match": gold_match,
                "gold_entries_match_or_partial": gold_lenient,
                "candidates": n_candidates,
                "candidates_match": candidates_match,
                "candidates_match_or_partial": candidates_lenient,
                "candidates_not_judged": candidates_not_judged,
                "findings": self.counts["findings"],
                "findings_unlocated": self.counts["findings_unlocated"],
                "records_without_gold": self.counts["records_without_gold"],
                "candidates_in_records_without_gold": self.counts[
                    "candidates_in_records_without_gold"
                ],
                "judge_calls": self.counts["judge_calls"],
                "judge_errors": self.counts["judge_errors"],
            },
        }

        if self.details_file:
            os.makedirs(os.path.dirname(os.path.abspath(self.details_file)), exist_ok=True)
            with open(self.details_file, "w") as f:
                json.dump(
                    {"gold_entries": self.gold_entries, "candidates": self.candidates},
                    f,
                    indent=2,
                    ensure_ascii=False,
                    default=str,
                )
            logger.info(f"Wrote per-entry judgements to {self.details_file}")
        return result
