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
        "ALL": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2},
        "AVG": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2.0},
        "label": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2},
    }


def test_multiple_fields() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label1", "label2"])
    m.update({"label1": "foo", "label2": "A"}, {"label1": "foo", "label2": "B"})
    m.update({"label1": "bar", "label2": "C"}, {"label1": "rar", "label2": "C"})
    out = m.compute()
    assert out == {
        "ALL": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 4},
        "AVG": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2.0},
        "label1": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2},
        "label2": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2},
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
        "| field   |   precision |   recall |   f1 |   support |\n"
        "|:--------|------------:|---------:|-----:|----------:|\n"
        "| label1  |           1 |        1 |    1 |         1 |\n"
        "| label2  |           1 |        1 |    1 |         1 |\n"
        "| AVG     |           1 |        1 |    1 |         1 |\n"
        "| ALL     |           1 |        1 |    1 |         2 |"
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
        '    "f1": 1.0,\n'
        '    "support": 1\n'
        "  },\n"
        '  "AVG": {\n'
        '    "precision": 1.0,\n'
        '    "recall": 1.0,\n'
        '    "f1": 1.0,\n'
        '    "support": 1.0\n'
        "  },\n"
        '  "ALL": {\n'
        '    "precision": 1.0,\n'
        '    "recall": 1.0,\n'
        '    "f1": 1.0,\n'
        '    "support": 1\n'
        "  }\n"
        "}"
    )


def test_multiple_fields_subfield_keys_expand_entries() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"], subfield_keys={"label": ["type"]})
    m.update(
        {"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "bar"}]},
        {"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "baz"}]},
    )

    out = m.compute()

    assert out == {
        "ALL": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 2},
        "AVG": {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 1.0},
        "label.A": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
        "label.B": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1},
    }


def test_multiple_fields_subfield_keys_require_dict_entries() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"], subfield_keys={"label": ["type"]})

    with pytest.raises(TypeError, match="contains non-dict entries"):
        m.update({"label": ["foo"]}, {"label": ["foo"]})


def test_multiple_fields_subfield_keys_missing_field_on_one_side() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"], subfield_keys={"label": ["type"]})
    m.update({}, {"label": [{"type": "A", "value": "foo"}]})

    out = m.compute()

    assert out == {
        "ALL": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1},
        "AVG": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1.0},
        "label.A": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1},
    }


def test_multiple_fields_subfield_keys_missing_subkey_uses_none_suffix() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"], subfield_keys={"label": ["type"]})
    m.update(
        {"label": [{"value": "foo"}]},
        {"label": [{"type": "A", "value": "foo"}]},
    )

    out = m.compute()

    assert out == {
        "ALL": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1},
        "AVG": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 0.5},
        "label.A": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1},
        "label.None": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 0},
    }


def test_multiple_fields_subfield_keys_expand_single_dict_entry() -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"], subfield_keys={"label": ["type"]})
    m.update(
        {"label": {"type": "A", "value": "foo"}},
        {"label": {"type": "A", "value": "foo"}},
    )

    out = m.compute()

    assert out == {
        "ALL": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
        "AVG": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1.0},
        "label.A": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
    }


def test_multiple_fields_subfield_values_keep_only_selected_payload_fields() -> None:
    m = F1MicroMultipleFieldsMetric(
        fields=["label"],
        subfield_keys={"label": ["type"]},
        subfield_values={"label": ["value"]},
    )
    m.update(
        {"label": [{"type": "A", "value": "foo", "ignored": "left"}]},
        {"label": [{"type": "A", "value": "foo", "ignored": "right"}]},
    )

    out = m.compute()

    assert out == {
        "ALL": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
        "AVG": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1.0},
        "label.A": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
    }


def test_multiple_fields_subfield_values_keep_only_selected_payload_fields_single_dict() -> None:
    m = F1MicroMultipleFieldsMetric(
        fields=["label"],
        subfield_keys={"label": ["type"]},
        subfield_values={"label": ["value"]},
    )
    m.update(
        {"label": {"type": "A", "value": "foo", "ignored": "left"}},
        {"label": {"type": "A", "value": "foo", "ignored": "right"}},
    )

    out = m.compute()

    assert out == {
        "ALL": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
        "AVG": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1.0},
        "label.A": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
    }


def test_multiple_fields_subfield_values_can_score_only_selected_nested_values() -> None:
    m = F1MicroMultipleFieldsMetric(
        fields=["organism_trends"],
        subfield_keys={"organism_trends": ["Hauptgruppe_RoteListen", "Lebensraum"]},
        subfield_values={"organism_trends": ["Antwortvariable"]},
    )
    m.update(
        {
            "organism_trends": [
                {
                    "Hauptgruppe_RoteListen": "Amphibien",
                    "Lebensraum": "Wald",
                    "Antwortvariable": "Abundanz",
                    "Trend": "negative",
                    "Untergruppe_RoteListen": "foo",
                }
            ]
        },
        {
            "organism_trends": [
                {
                    "Hauptgruppe_RoteListen": "Amphibien",
                    "Lebensraum": "Wald",
                    "Antwortvariable": "Abundanz",
                    "Trend": "positive",
                    "Untergruppe_RoteListen": "bar",
                }
            ]
        },
    )

    out = m.compute()

    assert out == {
        "ALL": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1},
        "AVG": {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1.0},
        "organism_trends.Amphibien&Wald": {
            "f1": 1.0,
            "precision": 1.0,
            "recall": 1.0,
            "support": 1,
        },
    }


def test_multiple_fields_auto_discovers_fields_when_not_configured() -> None:
    m = F1MicroMultipleFieldsMetric(fields=None)
    m.update({"a": "foo"}, {"a": "foo", "b": "bar"})

    out = m.compute()

    assert out["a"] == {"f1": 1.0, "precision": 1.0, "recall": 1.0, "support": 1}
    assert out["b"] == {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": 1}
    assert out["AVG"] == {"f1": 0.5, "precision": 0.5, "recall": 0.5, "support": 1.0}
    assert out["ALL"]["precision"] == pytest.approx(1.0)
    assert out["ALL"]["recall"] == pytest.approx(0.5)
    assert out["ALL"]["f1"] == pytest.approx(2 / 3)
    assert out["ALL"]["support"] == 2


@pytest.mark.parametrize(
    ("prediction", "reference", "expected_support"),
    [(None, {"label": "foo"}, 1), ({"label": "foo"}, None, 0)],
)
def test_multiple_fields_accepts_none_as_empty_dict(
    prediction: dict[str, str] | None, reference: dict[str, str] | None, expected_support: int
) -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"])
    m.update(prediction, reference)

    out = m.compute()

    assert out == {
        "ALL": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": expected_support},
        "AVG": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": float(expected_support)},
        "label": {"f1": 0.0, "precision": 0.0, "recall": 0.0, "support": expected_support},
    }


@pytest.mark.parametrize("prediction", [[], ""])
def test_multiple_fields_rejects_falsy_non_dict_predictions(prediction: object) -> None:
    m = F1MicroMultipleFieldsMetric(fields=["label"])

    with pytest.raises(TypeError, match="Prediction and reference should be dicts"):
        m.update(prediction, {"label": "foo"})


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
                "| field   |   precision |   recall |   f1 |   support |\n"
                "|:--------|------------:|---------:|-----:|----------:|\n"
                "| a_field |           1 |        1 |    1 |         1 |\n"
                "| b_field |           1 |        1 |    1 |         1 |\n"
                "| AVG     |           1 |        1 |    1 |         1 |\n"
                "| ALL     |           1 |        1 |    1 |         2 |\n"
            )
        else:
            assert logged_output == (
                "| field   |   precision |   recall |   f1 |   support |\n"
                "|:--------|------------:|---------:|-----:|----------:|\n"
                "| b_field |           1 |        1 |    1 |         1 |\n"
                "| a_field |           1 |        1 |    1 |         1 |\n"
                "| AVG     |           1 |        1 |    1 |         1 |\n"
                "| ALL     |           1 |        1 |    1 |         2 |\n"
            )
    else:
        if sort_fields:
            assert logged_output == (
                "{\n"
                '  "a_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 1\n'
                "  },\n"
                '  "b_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 1\n'
                "  },\n"
                '  "AVG": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 1.0\n'
                "  },\n"
                '  "ALL": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 2\n'
                "  }\n"
                "}\n"
            )
        else:
            assert logged_output == (
                "{\n"
                '  "b_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 1\n'
                "  },\n"
                '  "a_field": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 1\n'
                "  },\n"
                '  "AVG": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 1.0\n'
                "  },\n"
                '  "ALL": {\n'
                '    "precision": 1.0,\n'
                '    "recall": 1.0,\n'
                '    "f1": 1.0,\n'
                '    "support": 2\n'
                "  }\n"
                "}\n"
            )
