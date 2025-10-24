import pytest

from kibad_llm.metrics.f1 import F1SingleLabelMetric


def test_perfect_matches() -> None:
    m = F1SingleLabelMetric(field="label")
    m.update({"label": "a"}, {"label": "a"})
    m.update({"label": "b"}, {"label": "b"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(1.0)
    assert out["recall"] == pytest.approx(1.0)
    assert out["f1"] == pytest.approx(1.0)


def test_all_mismatches() -> None:
    m = F1SingleLabelMetric(field="label")
    m.update({"label": "a"}, {"label": "b"})
    m.update({"label": "x"}, {"label": "y"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_mixed_counts() -> None:
    m = F1SingleLabelMetric(field="label")
    # tp
    m.update({"label": "a"}, {"label": "a"})
    # fp and fn
    m.update({"label": "b"}, {"label": "c"})
    # fn only
    m.update({"label": None}, {"label": "d"})
    # fp only
    m.update({"label": "e"}, {"label": None})
    # fp only again
    m.update({"label": "f"}, {"label": None})
    out = m.compute(m)
    # tp=1, fp=3, fn=2 -> precision=1/4, recall=1/3, f1=2/7
    assert out["precision"] == pytest.approx(1 / 4)
    assert out["recall"] == pytest.approx(1 / 3)
    assert out["f1"] == pytest.approx(2 / 7)


def test_all_none_zero_division() -> None:
    m = F1SingleLabelMetric(field="label")
    m.update({"label": None}, {"label": None})
    m.update({"label": None}, {"label": None})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_reset() -> None:
    m = F1SingleLabelMetric(field="label")
    m.update({"label": "z"}, {"label": "z"})
    assert m.compute(m)["f1"] == pytest.approx(1.0)
    m.reset()
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)
