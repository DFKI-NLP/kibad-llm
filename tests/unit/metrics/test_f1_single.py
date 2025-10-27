import pytest

from kibad_llm.metrics.f1 import F1SingleLabelMetric


def test_perfect_matches() -> None:
    m = F1SingleLabelMetric(field="label")
    m.update({"label": "foo"}, {"label": "foo"})
    m.update({"label": "bar"}, {"label": "bar"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(1.0)
    assert out["recall"] == pytest.approx(1.0)
    assert out["f1"] == pytest.approx(1.0)


def test_all_mismatches() -> None:
    m = F1SingleLabelMetric(field="label")
    m.update({"label": "foo"}, {"label": "woo"})
    m.update({"label": "bar"}, {"label": "rar"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_mixed_counts() -> None:
    m = F1SingleLabelMetric(field="label")
    # tp
    m.update({"label": "foo"}, {"label": "foo"})
    # fp and fn and bool
    m.update({"label": True}, {"label": False})
    # fn only
    m.update({"label": None}, {"label": "dar"})
    # fp only
    m.update({"label": "eoo"}, {"label": None})
    # fp only again
    m.update({"label": "fuu"}, {"label": None})
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
    m.update({"label": "foo"}, {"label": "foo"})
    assert m.compute(m)["f1"] == pytest.approx(1.0)
    m.reset()
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)
