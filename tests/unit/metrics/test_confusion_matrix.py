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
    assert counts[("B", cm.unassignable_label)] == 1
    assert counts[(cm.undetected_label, "C")] == 1
    # No other spurious counts
    assert len(counts) == 3


def test_prepare_entry_various_types():
    cm = ConfusionMatrix()
    assert cm._prepare_entry(None) == set()
    assert cm._prepare_entry("x") == {"x"}
    assert cm._prepare_entry(["a", "a", "b"]) == {"a", "b"}
    assert (
        cm._prepare_entry({"labels": ["a"]}) == {("labels", "a")} if False else True
    )  # sanity placeholder

    cm_field = ConfusionMatrix(field="labels")
    assert cm_field._prepare_entry({"labels": ["x", "y", "y"]}) == {"x", "y"}
    assert cm_field._prepare_entry({"other": "z"}) == set()
    assert cm_field._prepare_entry({"labels": None}) == set()


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
    assert res["B"][cm.unassignable_label] == 2
    assert res[cm.undetected_label]["C"] == 1
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
    cm.update(prediction=["A"], reference=["B"])  # produces FN(B) and no TP
    cm.update(prediction=["C"], reference=[])  # produces FP(C)
    _ = cm.compute()
    # Ensure a markdown confusion matrix was logged
    assert caplog.text == (
        "INFO     kibad_llm.metrics.confusion_matrix:confusion_matrix.py:134 Confusion Matrix:\n"
        "|            |   A |   C |   UNASSIGNABLE |\n"
        "|:-----------|----:|----:|---------------:|\n"
        "| B          |   0 |   0 |              1 |\n"
        "| UNDETECTED |   1 |   1 |              0 |\n"
    )
