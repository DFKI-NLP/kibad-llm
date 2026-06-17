"""Unit tests for single-field and multi-field confusion-matrix metrics."""

import logging

import pytest

from kibad_llm.metrics import ConfusionMatrix, ConfusionMatrixCollection


def test_update_and_compute_accumulates_and_structures_result() -> None:
    """ConfusionMatrix should aggregate tp, fp, and fn counts into the expected cells."""
    cm = ConfusionMatrix(field="labels")

    # First sample: TP(A), FN(B), FP(C)
    cm.update(prediction={"labels": ["A", "C"]}, reference={"labels": ["A", "B"]})
    # Second sample: FN(B) only
    cm.update(prediction={"labels": None}, reference={"labels": ["B"]})
    # Third sample: TP(D)
    cm.update(prediction={"labels": "D"}, reference={"labels": {"D"}})

    res = cm.compute()
    # res is a mapping: gold_label -> {pred_label -> count}
    assert res == {
        "A": {"A": 1.0},
        "B": {"C": 1.0, "UNDETECTED": 1.5},
        "D": {"D": 1.0},
        "UNASSIGNABLE": {"C": 0.5},
    }


def test_errors_on_reserved_labels_in_inputs_are_raised_on_compute() -> None:
    """Reserved placeholder labels should be rejected when present in the tracked data."""
    cm = ConfusionMatrix(field="labels")

    cm.update(
        prediction={"labels": [cm.undetected_label]},
        reference={"labels": ["X"]},
        record_id="record-1",
    )
    with pytest.raises(ValueError, match="The prediction has the label"):
        cm.compute(reset=False)

    cm.reset()
    cm.update(
        prediction={"labels": ["X"]},
        reference={"labels": [cm.unassignable_label]},
        record_id="record-2",
    )
    with pytest.raises(ValueError, match="The gold reference has the label"):
        cm.compute(reset=False)


def test_compute_uses_custom_reserved_labels_and_stringifies_labels() -> None:
    """Custom placeholders and non-string labels should be preserved in the computed output."""
    cm = ConfusionMatrix(unassignable_label="OTHER", undetected_label="MISSING")

    cm.update(prediction=[1, 3], reference=[1, 2], record_id="record-1")

    assert cm.compute(reset=False) == {
        "1": {"1": 1.0},
        "2": {"3": 1.0, "MISSING": 0.5},
        "OTHER": {"3": 0.5},
    }


def test_show_as_markdown_logs_with_field_header_and_reserved_labels_last(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Markdown logging should label the field and place reserved placeholder labels last."""
    caplog.set_level(logging.INFO, logger="kibad_llm.metrics.confusion_matrix")
    cm = ConfusionMatrix(
        field="labels",
        show_as_markdown=True,
        unassignable_label="OTHER",
        undetected_label="MISSING",
    )
    cm.update(prediction={"labels": ["A"]}, reference={"labels": ["B"]}, record_id=1)
    cm.update(prediction={"labels": ["C"]}, reference={"labels": []}, record_id=2)

    _ = cm.compute()

    lines = caplog.text.splitlines()
    assert lines[0].endswith("Confusion Matrix for field 'labels':")
    assert lines[1:] == [
        "|       |   A |   C |   MISSING |",
        "|:------|----:|----:|----------:|",
        "| B     | 1   |   0 |       0.5 |",
        "| OTHER | 0.5 |   1 |       0   |",
    ]


def test_confusion_matrix_collection_computes_one_matrix_per_explicit_field() -> None:
    """The collection should return one independent confusion matrix per configured field."""
    cm = ConfusionMatrixCollection(fields=["labels", "status"], sort_fields=True)

    cm.update(
        prediction={"labels": ["A", "C"], "status": "predicted"},
        reference={"labels": ["A", "B"], "status": "gold"},
        record_id="row-1",
    )

    assert cm.compute(reset=False) == {
        "labels": {
            "A": {"A": 1.0},
            "B": {"C": 1.0, "UNDETECTED": 0.5},
            "UNASSIGNABLE": {"C": 0.5},
        },
        "status": {
            "UNASSIGNABLE": {"predicted": 0.5},
            "gold": {"UNDETECTED": 0.5, "predicted": 1.0},
        },
    }


def test_confusion_matrix_collection_auto_discovers_fields() -> None:
    """The collection should lazily create confusion matrices for discovered fields."""
    cm = ConfusionMatrixCollection()

    cm.update(
        prediction={"matching": "A"},
        reference={"matching": "A", "missing": "B"},
        record_id="row-1",
    )

    assert cm.compute(reset=False) == {
        "matching": {"A": {"A": 1}},
        "missing": {"B": {"UNDETECTED": 1}},
    }


def test_confusion_matrix_collection_supports_grouped_subfields() -> None:
    """Grouped-field expansion should create one confusion matrix per generated subfield."""
    cm = ConfusionMatrixCollection(
        fields=["label"],
        subfield_keys={"label": ["type"]},
        subfield_values={"label": ["value"]},
        sort_fields=True,
    )

    cm.update(
        prediction={"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "bar"}]},
        reference={"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "baz"}]},
        record_id="row-1",
    )

    assert cm.compute(reset=False) == {
        "label.A": {"(('value', 'foo'),)": {"(('value', 'foo'),)": 1.0}},
        "label.B": {
            "(('value', 'baz'),)": {"(('value', 'bar'),)": 1.0, "UNDETECTED": 0.5},
            "UNASSIGNABLE": {"(('value', 'bar'),)": 0.5},
        },
    }
