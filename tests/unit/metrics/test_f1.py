import pytest

from kibad_llm.metrics.f1 import F1MicroMultipleFieldsMetric, F1MicroSingleFieldMetric


def test_perfect_matches() -> None:
    m = F1MicroSingleFieldMetric(field="label")
    m.update({"label": "foo"}, {"label": "foo"})
    m.update({"label": "bar"}, {"label": "bar"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(1.0)
    assert out["recall"] == pytest.approx(1.0)
    assert out["f1"] == pytest.approx(1.0)


def test_all_mismatches() -> None:
    m = F1MicroSingleFieldMetric(field="label")
    m.update({"label": "foo"}, {"label": "woo"})
    m.update({"label": "bar"}, {"label": "rar"})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_mixed_counts() -> None:
    m = F1MicroSingleFieldMetric(field="label")
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
    m = F1MicroSingleFieldMetric(field="label")
    m.update({"label": None}, {"label": None})
    m.update({"label": None}, {"label": None})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_reset() -> None:
    m = F1MicroSingleFieldMetric(field="label")
    m.update({"label": "foo"}, {"label": "foo"})
    assert m.compute(m)["f1"] == pytest.approx(1.0)
    m.reset()
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_multi_perfect_matches() -> None:
    m = F1MicroSingleFieldMetric(field="label")
    m.update({"label": ["foo", "woo"]}, {"label": ["foo", "woo"]})
    m.update({"label": {"bar", "dar"}}, {"label": {"bar", "dar"}})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(1.0)
    assert out["recall"] == pytest.approx(1.0)
    assert out["f1"] == pytest.approx(1.0)


def test_multi_value_all_mismatches() -> None:
    m = F1MicroSingleFieldMetric(field="label")
    m.update({"label": ["foo", "boo"]}, {"label": ["woo", "doo"]})
    m.update({"label": {"bar", "dar"}}, {"label": {"rar", "sar"}})
    out = m.compute(m)
    assert out["precision"] == pytest.approx(0.0)
    assert out["recall"] == pytest.approx(0.0)
    assert out["f1"] == pytest.approx(0.0)


def test_multi_value_mixed_count() -> None:
    m = F1MicroSingleFieldMetric()
    m.update(["foo", True], {"bar", "dar", True})
    out = m.compute(m)
    # tp=1, fp=1, fn=2 -> precision=1/2, recall=1/3, f1=2*(((1/2)*(1/3))/((1/2)+(1/3)))
    assert out["precision"] == pytest.approx(1 / 2)
    assert out["recall"] == pytest.approx(1 / 3)
    assert out["f1"] == pytest.approx(2 * (((1 / 2) * (1 / 3)) / ((1 / 2) + (1 / 3))))


def test_multi_value_mixed_counts() -> None:
    m = F1MicroSingleFieldMetric(field="label")
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


def test_multi_value_mixed_counts_no_field() -> None:
    m = F1MicroSingleFieldMetric()
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


def test_multiple_fields_single_field() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"])
    m.update({"label": "foo"}, {"label": "foo"})
    m.update({"label": "bar"}, {"label": "rar"})
    out = m.compute()
    assert out == {
        "ALL": {"f1": 0.5, "precision": 0.5, "recall": 0.5},
        "label": {"f1": 0.5, "precision": 0.5, "recall": 0.5},
    }


def test_multiple_fields() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label1", "label2"])
    m.update({"label1": "foo", "label2": "A"}, {"label1": "foo", "label2": "B"})
    m.update({"label1": "bar", "label2": "C"}, {"label1": "rar", "label2": "C"})
    out = m.compute()
    assert out == {
        "ALL": {"f1": 0.5, "precision": 0.5, "recall": 0.5},
        "label1": {"f1": 0.5, "precision": 0.5, "recall": 0.5},
        "label2": {"f1": 0.5, "precision": 0.5, "recall": 0.5},
    }


def test_multiple_fields_reset() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"])
    m.update({"label": "foo"}, {"label": "foo"})
    assert m.compute()["label"]["f1"] == pytest.approx(1.0)
    m.reset()
    out = m.compute()
    assert out["label"]["f1"] == pytest.approx(0.0)


def test_multiple_fields_format_result_markdown() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label1", "label2"], format_as_markdown=True)
    m.update({"label1": "foo", "label2": "A"}, {"label1": "foo", "label2": "A"})
    result = m.compute()
    formatted = m._format_result(result)
    assert formatted == (
        "| field   |   precision |   recall |   f1 |\n"
        "|:--------|------------:|---------:|-----:|\n"
        "| label1  |           1 |        1 |    1 |\n"
        "| label2  |           1 |        1 |    1 |\n"
        "| ALL     |           1 |        1 |    1 |"
    )


def test_multiple_fields_format_result_json() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"], format_as_markdown=False)
    m.update({"label": "foo"}, {"label": "foo"})
    result = m.compute()
    formatted = m._format_result(result)
    assert formatted == (
        "{\n"
        '  "label": {\n'
        '    "precision": 1.0,\n'
        '    "recall": 1.0,\n'
        '    "f1": 1.0\n'
        "  },\n"
        '  "ALL": {\n'
        '    "precision": 1.0,\n'
        '    "recall": 1.0,\n'
        '    "f1": 1.0\n'
        "  }\n"
        "}"
    )


@pytest.mark.parametrize(
    "format_as_markdown,sort_fields", [(True, True), (True, False), (False, True), (False, False)]
)
def test_multiple_fields_show(format_as_markdown: bool, sort_fields: bool, caplog) -> None:
    m = F1MicroMultipleFieldsMetric(
        fields=["b_field", "a_field"],
        format_as_markdown=format_as_markdown,
        sort_fields=sort_fields,
    )
    m.update({"b_field": "foo", "a_field": "A"}, {"b_field": "foo", "a_field": "A"})
    with caplog.at_level("INFO"):
        m.show_result()

    # split off the header line
    header, logged_output = caplog.text.split("\n", 1)

    assert "Evaluation results:" in header
    if format_as_markdown:
        if sort_fields:
            assert logged_output == (
                "| field   |   precision |   recall |   f1 |\n"
                "|:--------|------------:|---------:|-----:|\n"
                "| a_field |           1 |        1 |    1 |\n"
                "| b_field |           1 |        1 |    1 |\n"
                "| ALL     |           1 |        1 |    1 |\n"
            )
        else:
            assert logged_output == (
                "| field   |   precision |   recall |   f1 |\n"
                "|:--------|------------:|---------:|-----:|\n"
                "| b_field |           1 |        1 |    1 |\n"
                "| a_field |           1 |        1 |    1 |\n"
                "| ALL     |           1 |        1 |    1 |\n"
            )
    else:
        if sort_fields:
            assert logged_output == (
                "{\n"
                '  "a_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0\n'
                "  },\n"
                '  "b_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0\n'
                "  },\n"
                '  "ALL": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0\n'
                "  }\n"
                "}\n"
            )
        else:
            assert logged_output == (
                "{\n"
                '  "b_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0\n'
                "  },\n"
                '  "a_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0\n'
                "  },\n"
                '  "ALL": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0\n'
                "  }\n"
                "}\n"
            )
