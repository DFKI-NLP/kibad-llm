import logging

import pytest

from kibad_llm.metrics.confusion_matrix import ConfusionMatrix


def test_update_and_compute_accumulates_and_structures_result():
    cm = ConfusionMatrix(field="labels")

    # First sample: TP(A), FN(B), FP(C)
    cm.update(prediction={"labels": ["A", "C"]}, reference={"labels": ["A", "B"]})
    # Second sample: FN(B) only
    cm.update(prediction={"labels": None}, reference={"labels": ["B"]})
    # Third sample: TP(D)
    cm.update(prediction={"labels": "D"}, reference={"labels": {"D"}})

    res = cm.compute()
    # res is a mapping: gold_label -> {pred_label -> count}
    assert res["A"]["A"] == 1
    # FN(B) counted under prediction side as UNDETECTED
    assert res["B"][cm.undetected_label] == 2
    # FP(C) counted under gold side as UNASSIGNABLE
    assert res[cm.unassignable_label]["C"] == 1
    assert res["D"]["D"] == 1


def test_errors_on_reserved_labels_in_inputs_are_raised_on_compute():
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


def test_compute_uses_custom_reserved_labels_and_stringifies_labels():
    cm = ConfusionMatrix(unassignable_label="OTHER", undetected_label="MISSING")

    cm.update(prediction=[1, 3], reference=[1, 2], record_id="record-1")

    assert cm.compute(reset=False) == {
        "1": {"1": 1},
        "2": {"MISSING": 1},
        "OTHER": {"3": 1},
    }


def test_show_as_markdown_logs_with_field_header_and_reserved_labels_last(caplog):
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
        "| B     |   0 |   0 |         1 |",
        "| OTHER |   1 |   1 |         0 |",
    ]
