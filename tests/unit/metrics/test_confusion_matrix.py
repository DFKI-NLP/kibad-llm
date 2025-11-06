import logging

import pytest

from kibad_llm.metrics.confusion_matrix import ConfusionMatrix


def test_calculate_counts_single_label_tp():
    cm = ConfusionMatrix()
    counts = cm.calculate_counts(prediction={"A"}, reference={"A"})
    assert counts == {("A", "A"): 1}


def test_calculate_counts_multilabel_tp_fn_fp():
    cm = ConfusionMatrix()
    pred = {"A", "C"}
    ref = {"A", "B"}
    counts = cm.calculate_counts(prediction=pred, reference=ref)
    assert counts[("A", "A")] == 1
    # FN: label in gold but not predicted -> (gold_label, UNDETECTED)
    assert counts[("B", cm.undetected_label)] == 1
    # FP: label predicted but not in gold -> (UNASSIGNABLE, pred_label)
    assert counts[(cm.unassignable_label, "C")] == 1
    # No other spurious counts
    assert len(counts) == 3


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


def test_reset_clears_counts():
    cm = ConfusionMatrix()
    cm.update(prediction=["A"], reference=["B"])
    assert cm.compute()  # non-empty
    cm.reset()
    assert cm.compute() == {}


def test_errors_on_reserved_labels_in_inputs():
    cm = ConfusionMatrix()
    # undetected label must not appear in prediction
    with pytest.raises(ValueError):
        cm.calculate_counts(prediction={cm.undetected_label}, reference={"X"})
    # unassignable label must not appear in reference
    with pytest.raises(ValueError):
        cm.calculate_counts(prediction={"X"}, reference={cm.unassignable_label})


def test_show_as_markdown_logs(caplog):
    caplog.set_level(logging.INFO, logger="kibad_llm.metrics.confusion_matrix")
    cm = ConfusionMatrix(show_as_markdown=True)
    cm.update(prediction=["A"], reference=["B"])  # produces FN(B) and FP(A)
    cm.update(prediction=["C"], reference=[])  # produces FP(C)
    _ = cm.compute()
    # Ensure a markdown confusion matrix was logged
    lines = caplog.text.splitlines()
    # discard first line since it contains line number info which may vary
    assert lines[1:] == [
        "|              |   A |   C |   UNDETECTED |",
        "|:-------------|----:|----:|-------------:|",
        "| B            |   0 |   0 |            1 |",
        "| UNASSIGNABLE |   1 |   1 |            0 |",
    ]
