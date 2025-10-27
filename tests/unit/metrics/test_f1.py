import pytest

from kibad_llm.metrics.f1 import MicroF1Metric


def test_perfect_matches() -> None:
    m = MicroF1Metric(field="label")
    m.update({"label": "foo"}, {"label": "foo"})
    m.update({"label": "bar"}, {"label": "bar"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(1.0)
    assert out["recall"] == pytest.approx(1.0)
    assert out["f1"] == pytest.approx(1.0)


def test_all_mismatches() -> None:
    m = MicroF1Metric(field="label")
    m.update({"label": "foo"}, {"label": "woo"})
    m.update({"label": "bar"}, {"label": "rar"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_mixed_counts() -> None:
    m = MicroF1Metric(field="label")
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
    m = MicroF1Metric(field="label")
    m.update({"label": None}, {"label": None})
    m.update({"label": None}, {"label": None})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_reset() -> None:
    m = MicroF1Metric(field="label")
    m.update({"label": "foo"}, {"label": "foo"})
    assert m.compute(m)["f1"] == pytest.approx(1.0)
    m.reset()
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_multi_perfect_matches() -> None:
    m = MicroF1Metric(field="label")
    m.update({"label": ["foo", "woo"]}, {"label": ["foo", "woo"]})
    m.update({"label": {"bar", "dar"}}, {"label": {"bar", "dar"}})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(1.0)
    assert out["recall"] == pytest.approx(1.0)
    assert out["f1"] == pytest.approx(1.0)


def test_multi_all_mismatches() -> None:
    m = MicroF1Metric(field="label")
    m.update({"label": ["foo", "boo"]}, {"label": ["woo", "doo"]})
    m.update({"label": {"bar", "dar"}}, {"label": {"rar", "sar"}})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_multi_mixed_count() -> None:
    m = MicroF1Metric()
    m.update(["foo", True], {"bar", "dar", True})
    out = m.compute(m)
    # tp=1, fp=1, fn=2 -> precision=1/2, recall=1/3, f1=2*(((1/2)*(1/3))/((1/2)+(1/3)))
    assert out["precision"] == pytest.approx(1 / 2)
    assert out["recall"] == pytest.approx(1 / 3)
    assert out["f1"] == pytest.approx(2 * (((1 / 2) * (1 / 3)) / ((1 / 2) + (1 / 3))))


def test_multi_mixed_counts() -> None:
    m = MicroF1Metric(field="label")
    # tp
    m.update({"label": {"foo"}}, {"label": ["foo"]})
    # fp and fn and bool
    m.update({"label": [True]}, {"label": False})
    # fn only
    m.update({"label": None}, {"label": "dar"})
    # fp only
    m.update({"label": {"eoo"}}, {"label": None})
    # fp twice
    m.update({"label": ["fuu", True]}, {"label": None})
    # tp and fp and fn
    m.update({"label": ["fuu", True]}, {"label": {"bar", True}})
    out = m.compute(m)
    # tp=2, fp=5, fn=3 -> precision=2/7, recall=2/5, f1=2*(((2/7)*(2/5))/((2/7)+(2/5)))
    assert out["precision"] == pytest.approx(2 / 7)
    assert out["recall"] == pytest.approx(2 / 5)
    assert out["f1"] == pytest.approx(2 * (((2 / 7) * (2 / 5)) / ((2 / 7) + (2 / 5))))


def test_multi_mixed_counts_no_field() -> None:
    m = MicroF1Metric()
    # tp
    m.update({"foo"}, ["foo"])
    # fp and fn and bool
    m.update([True], False)
    # fn only
    m.update(None, "dar")
    # fp only
    m.update({"eoo"}, None)
    # fp twice
    m.update(["fuu", True], None)
    # tp and fp and fn
    m.update(["fuu", True], {"bar", True})
    out = m.compute(m)
    # tp=2, fp=5, fn=3 -> precision=2/7, recall=2/5, f1=2*(((2/7)*(2/5))/((2/7)+(2/5)))
    assert out["precision"] == pytest.approx(2 / 7)
    assert out["recall"] == pytest.approx(2 / 5)
    assert out["f1"] == pytest.approx(2 * (((2 / 7) * (2 / 5)) / ((2 / 7) + (2 / 5))))
