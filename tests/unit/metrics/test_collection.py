"""Unit tests for metric collection helpers and field-discovery behavior."""

import pytest

from kibad_llm.metric import Metric
from kibad_llm.metrics.base import SingleFieldMetric
from kibad_llm.metrics.collection import (
    MetricCollection,
    MetricCollectionWithFieldDiscoveryAndGrouping,
    _expand_field_by_key_values,
)


class StaticMetric(Metric):
    """Simple test double that records resets and returns a fixed result."""

    def __init__(self, result: dict[str, object]) -> None:
        """Initialize the static metric test double.

        Args:
            result: Result returned by :meth:`_compute`.
        """
        self.result = result
        self.reset_calls = 0
        self.updates: list[tuple[object, object, object]] = []

    def reset(self) -> None:
        """Record that the metric was reset."""
        self.reset_calls += 1

    def _update(self, prediction: object, reference: object, record_id: object = None) -> None:
        """Record one update call.

        Args:
            prediction: Prediction passed to the metric.
            reference: Reference passed to the metric.
            record_id: Optional record identifier passed to the metric.
        """
        self.updates.append((prediction, reference, record_id))

    def _compute(self, *args, **kwargs) -> dict[str, object]:
        """Return the preconfigured result."""
        return self.result


class RecordingSingleFieldMetric(SingleFieldMetric):
    """Test double that records the values observed for one field."""

    def __init__(self, field: str | None = None, **kwargs) -> None:
        """Initialize the recording metric.

        Args:
            field: Optional field name to observe.
            **kwargs: Extra keyword arguments stored for assertion in tests.
        """
        self.init_kwargs = kwargs
        self.reset_calls = 0
        self.observations: list[tuple[object, object, object]] = []
        super().__init__(field=field)

    def reset(self) -> None:
        """Reset the recorded observations."""
        self.reset_calls += 1
        self.observations = []

    def _update(self, prediction: object, reference: object, record_id: object = None) -> None:
        """Record the observed field values for one update.

        Args:
            prediction: Prediction payload.
            reference: Reference payload.
            record_id: Optional record identifier forwarded by the caller.
        """
        if self.field is None:
            prediction_value = prediction
            reference_value = reference
        else:
            prediction_value = (
                prediction.get(self.field) if isinstance(prediction, dict) else prediction
            )
            reference_value = (
                reference.get(self.field) if isinstance(reference, dict) else reference
            )
        self.observations.append((prediction_value, reference_value, record_id))

    def _compute(self, *args, **kwargs) -> dict[str, object]:
        """Return the recorded observations and initialization kwargs."""
        return {
            "field": self.field,
            "observations": list(self.observations),
            "kwargs": dict(self.init_kwargs),
        }


# MetricCollection


def test_metric_collection_add_metric_rejects_duplicate_names() -> None:
    """MetricCollection should reject duplicate metric names."""
    m = MetricCollection[StaticMetric]()
    m.add_metric("label", StaticMetric({"value": 1}))

    with pytest.raises(ValueError, match="Metric label already exists"):
        m.add_metric("label", StaticMetric({"value": 2}))


def test_metric_collection_reset_forwards_to_children() -> None:
    """MetricCollection.reset should reset each child metric."""
    metric_a = StaticMetric({"value": "a"})
    metric_b = StaticMetric({"value": "b"})
    m = MetricCollection(metrics={"a": metric_a, "b": metric_b})

    m.reset()

    assert metric_a.reset_calls == 1
    assert metric_b.reset_calls == 1


def test_metric_collection_compute_respects_sort_fields() -> None:
    """MetricCollection.compute should optionally sort result fields."""
    m = MetricCollection(
        metrics={"b": StaticMetric({"value": "b"}), "a": StaticMetric({"value": "a"})},
        sort_fields=True,
    )

    out = m.compute(reset=False)

    assert list(out) == ["a", "b"]


# _expand_field_by_key_values


def test_expand_field_by_key_values_does_not_mutate_input() -> None:
    """Field expansion should operate on a deep copy of the input entry."""
    entry = {
        "label": {"type": "A", "value": "foo", "ignored": "left"},
        "other": "keep",
    }

    expanded, new_fields = _expand_field_by_key_values(
        entry=entry,
        field="label",
        key_entries=["type"],
        value_entries=["value"],
    )

    assert entry == {
        "label": {"type": "A", "value": "foo", "ignored": "left"},
        "other": "keep",
    }
    assert expanded == {"label.A": {"value": "foo"}, "other": "keep"}
    assert new_fields == {"label.A"}


# MetricCollectionWithFieldDiscoveryAndGrouping


def test_metric_collection_with_field_discovery_and_grouping_forwards_metric_kwargs_to_created_metrics() -> (
    None
):
    """Created field metrics should receive forwarded keyword arguments."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        marker="seen",
    )

    m.update({"label": "foo"}, {"label": "foo"})

    assert m.metrics["label"].init_kwargs == {"marker": "seen"}


@pytest.mark.parametrize(
    ("prediction", "reference", "expected_observation"),
    [
        (None, {"label": "foo"}, (None, "foo", None)),
        ({"label": "foo"}, None, ("foo", None, None)),
    ],
)
def test_metric_collection_with_field_discovery_and_grouping_accepts_none_as_empty_dict(
    prediction: dict[str, str] | None,
    reference: dict[str, str] | None,
    expected_observation: tuple[object, object, object],
) -> None:
    """`None` predictions or references should behave like empty dictionaries."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
    )

    m.update(prediction, reference)

    assert m.metrics["label"].observations == [expected_observation]


@pytest.mark.parametrize("prediction", [[], ""])
def test_metric_collection_with_field_discovery_and_grouping_rejects_falsy_non_dict_predictions(
    prediction: object,
) -> None:
    """Falsy non-dictionary predictions should still be rejected."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
    )

    with pytest.raises(TypeError, match="Prediction and reference should be dicts"):
        m.update(prediction, {"label": "foo"})


def test_metric_collection_with_field_discovery_and_grouping_auto_discovers_fields_when_not_configured() -> (
    None
):
    """The collection should lazily discover fields from incoming records."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(metric_class=RecordingSingleFieldMetric)

    m.update({"a": "foo"}, {"a": "foo", "b": "bar"}, record_id="row-1")

    assert set(m.metrics) == {"a", "b"}
    assert m.metrics["a"].observations == [("foo", "foo", "row-1")]
    assert m.metrics["b"].observations == [(None, "bar", "row-1")]


def test_metric_collection_with_field_discovery_and_grouping_subfield_keys_expand_entries() -> (
    None
):
    """Configured subfield keys should expand nested entries into generated fields."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
    )

    m.update(
        {"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "bar"}]},
        {"label": [{"type": "A", "value": "foo"}, {"type": "B", "value": "baz"}]},
    )

    assert set(m.metrics) == {"label.A", "label.B"}
    assert m.metrics["label.A"].observations == [([{"value": "foo"}], [{"value": "foo"}], None)]
    assert m.metrics["label.B"].observations == [([{"value": "bar"}], [{"value": "baz"}], None)]


def test_metric_collection_with_field_discovery_and_grouping_subfield_keys_require_dict_entries() -> (
    None
):
    """Subfield expansion should reject list entries that are not dictionaries."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
    )

    with pytest.raises(TypeError, match="contains non-dict entries"):
        m.update({"label": ["foo"]}, {"label": ["foo"]})


def test_metric_collection_with_field_discovery_and_grouping_subfield_keys_missing_field_on_one_side() -> (
    None
):
    """Expansion should still create metrics when a grouped field exists on only one side."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
    )

    m.update({}, {"label": [{"type": "A", "value": "foo"}]})

    assert set(m.metrics) == {"label.A"}
    assert m.metrics["label.A"].observations == [(None, [{"value": "foo"}], None)]


def test_metric_collection_with_field_discovery_and_grouping_subfield_keys_missing_subkey_uses_none_suffix() -> (
    None
):
    """Missing grouping keys should produce generated fields with a `None` suffix."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
    )

    m.update(
        {"label": [{"value": "foo"}]},
        {"label": [{"type": "A", "value": "foo"}]},
    )

    assert set(m.metrics) == {"label.A", "label.None"}
    assert m.metrics["label.A"].observations == [(None, [{"value": "foo"}], None)]
    assert m.metrics["label.None"].observations == [([{"value": "foo"}], None, None)]


def test_metric_collection_with_field_discovery_and_grouping_subfield_keys_expand_single_dict_entry() -> (
    None
):
    """A single nested dictionary should expand into one generated field."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
    )

    m.update(
        {"label": {"type": "A", "value": "foo"}},
        {"label": {"type": "A", "value": "foo"}},
    )

    assert set(m.metrics) == {"label.A"}
    assert m.metrics["label.A"].observations == [({"value": "foo"}, {"value": "foo"}, None)]


def test_metric_collection_with_field_discovery_and_grouping_subfield_values_keep_only_selected_payload_fields() -> (
    None
):
    """Subfield value filters should keep only the configured payload keys for lists."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
        subfield_values={"label": ["value"]},
    )

    m.update(
        {"label": [{"type": "A", "value": "foo", "ignored": "left"}]},
        {"label": [{"type": "A", "value": "foo", "ignored": "right"}]},
    )

    assert m.metrics["label.A"].observations == [([{"value": "foo"}], [{"value": "foo"}], None)]


def test_metric_collection_with_field_discovery_and_grouping_subfield_values_keep_only_selected_payload_fields_single_dict() -> (
    None
):
    """Subfield value filters should keep only the configured payload keys for dicts."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
        fields=["label"],
        subfield_keys={"label": ["type"]},
        subfield_values={"label": ["value"]},
    )

    m.update(
        {"label": {"type": "A", "value": "foo", "ignored": "left"}},
        {"label": {"type": "A", "value": "foo", "ignored": "right"}},
    )

    assert m.metrics["label.A"].observations == [({"value": "foo"}, {"value": "foo"}, None)]


def test_metric_collection_with_field_discovery_and_grouping_subfield_values_can_score_only_selected_nested_values() -> (
    None
):
    """Subfield value filters should support scoring only selected nested values."""
    m = MetricCollectionWithFieldDiscoveryAndGrouping(
        metric_class=RecordingSingleFieldMetric,
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

    assert set(m.metrics) == {"organism_trends.Amphibien&Wald"}
    assert m.metrics["organism_trends.Amphibien&Wald"].observations == [
        ([{"Antwortvariable": "Abundanz"}], [{"Antwortvariable": "Abundanz"}], None)
    ]
