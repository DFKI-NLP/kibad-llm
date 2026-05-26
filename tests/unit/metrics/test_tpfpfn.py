"""Unit tests for single-field and multi-field tp/fp/fn entry collectors."""

import json

import pytest

from kibad_llm.metrics.tpfpfn import TpFpFnCollector, TpFpFnCollectorCollection


def test_compute_returns_tpfpfn_entries_with_record_ids() -> None:
    """The collector should expose global tp/fp/fn entries together with record ids."""
    m = TpFpFnCollector()

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A"], record_id="record-2")

    assert m.compute(reset=False) == {
        "tp": [["record-1", "A"], ["record-2", "A"]],
        "fp": [["record-1", "B"]],
        "fn": [["record-1", "C"]],
    }


def test_compute_groups_entries_per_record() -> None:
    """The collector should optionally group tp/fp/fn entries by record id."""
    m = TpFpFnCollector(per_record=True)

    m.update(prediction=["A", "B"], reference=["A", "C"], record_id="record-1")
    m.update(prediction=["A"], reference=["A", "D"], record_id="record-2")

    assert m.compute(reset=False) == {
        "record-1": {"tp": ["A"], "fp": ["B"], "fn": ["C"]},
        "record-2": {"tp": ["A"], "fp": [], "fn": ["D"]},
    }


@pytest.mark.parametrize("per_record", [False, True])
def test_compute_output_is_json_roundtrip_stable(per_record) -> None:
    """Collector outputs should already be JSON-safe for both output modes."""
    m = TpFpFnCollector(per_record=per_record, field="items")

    m.update(
        prediction={"items": [{"label": "A"}, {"label": "B"}]},
        reference={"items": [{"label": "A"}, {"label": "C"}]},
        record_id="record-1",
    )

    result = m._compute()

    assert result == json.loads(json.dumps(result))


def test_collection_computes_one_tpfpfn_result_per_explicit_field() -> None:
    """The collection should return one independent tp/fp/fn result per configured field."""
    m = TpFpFnCollectorCollection(fields=["status", "labels"], sort_fields=True)

    m.update(
        prediction={"labels": ["A", "C"], "status": "predicted"},
        reference={"labels": ["A", "B"], "status": "gold"},
        record_id="row-1",
    )

    result = m.compute(reset=False)

    assert list(result) == ["labels", "status"]
    assert result == {
        "labels": {
            "tp": [["row-1", "A"]],
            "fp": [["row-1", "C"]],
            "fn": [["row-1", "B"]],
        },
        "status": {
            "tp": [],
            "fp": [["row-1", "predicted"]],
            "fn": [["row-1", "gold"]],
        },
    }


def test_collection_auto_discovers_fields() -> None:
    """The collection should lazily create per-field collectors for discovered fields."""
    m = TpFpFnCollectorCollection()

    m.update(
        prediction={"matching": "A"},
        reference={"matching": "A", "missing": "B"},
        record_id="row-1",
    )

    assert m.compute(reset=False) == {
        "matching": {
            "tp": [["row-1", "A"]],
            "fp": [],
            "fn": [],
        },
        "missing": {
            "tp": [],
            "fp": [],
            "fn": [["row-1", "B"]],
        },
    }


def test_collection_supports_grouped_subfields() -> None:
    """Grouped-field expansion should create one tp/fp/fn collector per generated subfield."""
    m = TpFpFnCollectorCollection(
        fields=["label"],
        subfield_keys={"label": ["type"]},
        subfield_values={"label": ["value"]},
        sort_fields=True,
    )

    m.update(
        prediction={"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "bar"}]},
        reference={"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "baz"}]},
        record_id="row-1",
    )

    assert m.compute(reset=False) == {
        "label.A": {
            "tp": [["row-1", [["value", "foo"]]]],
            "fp": [],
            "fn": [],
        },
        "label.B": {
            "tp": [],
            "fp": [["row-1", [["value", "bar"]]]],
            "fn": [["row-1", [["value", "baz"]]]],
        },
    }


def test_collection_forwards_per_record_to_child_collectors() -> None:
    """Collection kwargs should allow per-field collectors to emit per-record grouped entries."""
    m = TpFpFnCollectorCollection(fields=["labels"], per_record=True)

    m.update(
        prediction={"labels": ["A", "B"]}, reference={"labels": ["A", "C"]}, record_id="record-1"
    )
    m.update(prediction={"labels": ["A"]}, reference={"labels": ["A", "D"]}, record_id="record-2")

    assert m.compute(reset=False) == {
        "labels": {
            "record-1": {"tp": ["A"], "fp": ["B"], "fn": ["C"]},
            "record-2": {"tp": ["A"], "fp": [], "fn": ["D"]},
        }
    }
