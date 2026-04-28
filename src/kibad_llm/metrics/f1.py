from collections import defaultdict
from collections.abc import Hashable
from copy import deepcopy
from typing import Any

from pandas import DataFrame

from kibad_llm.metrics.base import MetricWithPrepareEntryAsSet
from kibad_llm.metrics.collection import MetricCollection


class F1MicroSingleFieldMetric(MetricWithPrepareEntryAsSet):
    """Computes micro averaged precision, recall, and F1 score for single- and multi-label
    classification tasks.

    The metric operates on sets and allows for simple preprocessing, see _prepare_entry for details.

    WARNING:
    !Since the metric operates on sets, this can obfuscate if the LLM produces duplicate labels
    !in multi-label settings. E.g., prediction = ["A", "A", "B"] and reference = ["A", "B"] will
    !be treated as perfect prediction with tp=2, fp=0, fn=0 even though the prediction contains a
    !duplicate label "A".

    Args:
        **kwargs: Keyword arguments for entry-to-set preparation. See
            `MetricWithPrepareEntryAsSet` for supported options.
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.reset()

    def reset(self) -> None:
        """Resets all values of the internal state to zero"""
        self.state: dict[str, int] = {"tp": 0, "fp": 0, "fn": 0}

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        """Updates the internal state with the given prediction(s) and reference(s).
        See `_prepare_entry_as_set` for accepted input formats.
        """
        prediction_set = self._prepare_entry_as_set(prediction)
        reference_set = self._prepare_entry_as_set(reference)

        self.state["tp"] += len(prediction_set & reference_set)
        self.state["fp"] += len(prediction_set - reference_set)
        self.state["fn"] += len(reference_set - prediction_set)

    @staticmethod
    def calculate_scores(state: dict[str, int]) -> dict[str, float]:
        """Calculates precision, recall and f1 from true positives, false positives and false negatives.

        Args:
            state: dictionary with keys "tp", "fp", "fn"

        returns: dictionary with precision, recall and f1
        """
        tp, fp, fn = state["tp"], state["fp"], state["fn"]
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "support": tp + fn,
        }

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes the micro average of precision, recall and f1 score."""
        return self.calculate_scores(state=self.state)


def _convert_to_key_value(
    entry: dict, field: str, key_entries: list
) -> tuple[dict[str, Any], set[str]]:
    """Converts a dict entry with a dict or list of dicts as value for a given field into multiple
    entries with key values as part of the field name.

    Args:
        entry: entry with the field to be converted
        field: field to be converted
        key_entries: list of keys to be used as key entries for the conversion. These should
            be keys of the dict entries in the field value. The values of these keys will be
            concatenated and added to the field name for the new entries.

    Returns:
        A tuple of the converted entry and the set of new field names created by the conversion.
    """

    entry = deepcopy(entry)
    field_value = entry.pop(field, None)

    # a single dict
    if isinstance(field_value, dict):
        key_values = []
        for key in key_entries:
            key_values.append(field_value.pop(key, None))
        new_field = f"{field}." + "&".join(key_values)
        entry[new_field] = field_value
        return entry, {new_field}

    # multiple entries of dicts
    elif isinstance(field_value, (list, set)):
        if not all(isinstance(e, dict) for e in field_value):
            raise TypeError(
                f"Field {field} contains non-dict entries, but subfield_keys are provided."
            )

        new_fields = set()
        for f_value in field_value:
            key_values = []
            for key in key_entries:
                key_values.append(f_value.pop(key, None))
            new_field = f"{field}." + "&".join(key_values)
            if new_field not in entry:
                entry[new_field] = []
            entry[new_field].append(f_value)
            new_fields.add(new_field)
        for new_field in new_fields:
            entry[new_field] = type(field_value)(entry[new_field])
        return entry, new_fields

    else:
        raise TypeError(
            f"Field {field} is neither a dict nor a list of dicts, but subfield_keys are provided."
        )


class F1MicroMultipleFieldsMetric(MetricCollection[F1MicroSingleFieldMetric]):

    def __init__(
        self,
        fields: list[str] | None = None,
        format_as_markdown: bool = True,
        subfield_keys: dict[str, list[str]] | None = None,
        sort_fields: bool = False,
        **kwargs,
    ) -> None:
        """Computes F1MicroSingleFieldMetric for multiple fields at once as well as micro (ALL)
        and macro (AVG) over all fields.

        Args:
            fields: List of fields to compute F1MicroSingleFieldMetric for. If not provided,
                the metric will be computed for all fields found in the data.
            format_as_markdown: Whether to format the result as a markdown table. Defaults to True.
            subfield_keys: Optional dict mapping field names to lists of keys that will indicate
                which subfields of the dict entries for these fields should be considered as key entries
                for these elements. Instead of calculating metrics for the whole dict,
                the metric will be calculated separately for each of the respective values. For example,
                with subfield_keys={"field1": ["key1", "key2"]}, the metric will be calculated separately
                for field1.key1=valueA&key2=valueB, field1.key1=valueC&key2=valueD, etc. This allows
                to calculate metrics for specific subfields of dict entries.
            sort_fields: Whether to sort the fields in the output. Defaults to False.
            **kwargs: Additional keyword arguments for F1MicroSingleFieldMetric, e.g., ignore_subfields.
        """
        # for now, just raise error if fields contain MICRO or MACRO
        if fields is not None and ("ALL" in fields or "AVG" in fields):
            raise ValueError("Fields cannot contain 'ALL' or 'AVG' as field names.")

        self.fields = fields
        self.subfield_keys = subfield_keys
        self.metric_kwargs = kwargs
        super().__init__(sort_fields=sort_fields)

        self.format_as_markdown = format_as_markdown

    def _update(self, prediction: Any, reference: Any, record_id: Hashable | None = None) -> None:
        if not isinstance(prediction, dict) or not isinstance(reference, dict):
            raise TypeError(
                f"Prediction and reference should be dicts, but got {type(prediction)} and {type(reference)}."
            )
        if self.fields is None:
            fields = list(prediction.keys() | reference.keys())
        else:
            fields = self.fields

        if self.subfield_keys is not None:
            new_fields = []
            for field in fields:
                if field in self.subfield_keys:
                    prediction, new_prediction_fields = _convert_to_key_value(
                        entry=prediction, field=field, key_entries=self.subfield_keys[field]
                    )
                    reference, new_reference_fields = _convert_to_key_value(
                        entry=reference, field=field, key_entries=self.subfield_keys[field]
                    )
                    new_fields.extend(new_prediction_fields | new_reference_fields)
                else:
                    new_fields.append(field)
            fields = new_fields

        # check if all required metrics exist and create missing ones via self.add_metric
        for field in fields:
            if field not in self.metrics:
                self.add_metric(field, F1MicroSingleFieldMetric(field=field, **self.metric_kwargs))

        super()._update(prediction=prediction, reference=reference, record_id=record_id)

    def _compute(self, *args, **kwargs) -> dict[str, Any]:
        """Computes the results for all sub-metrics and micro average over all instances.

        Returns:
            A dictionary mapping field names to their computed results.
        """
        result = super()._compute(*args, **kwargs)
        # compute mean for precision, recall, f1 over all fields
        scores_list = defaultdict(list)
        for field_result in result.values():
            for key, value in field_result.items():
                scores_list[key].append(value)
        result["AVG"] = {key: sum(values) / len(values) for key, values in scores_list.items()}

        # compute micro average over all instances based on states of all sub-metrics
        state_total = {
            "tp": sum(metric.state["tp"] for metric in self.metrics.values()),
            "fp": sum(metric.state["fp"] for metric in self.metrics.values()),
            "fn": sum(metric.state["fn"] for metric in self.metrics.values()),
        }
        result["ALL"] = F1MicroSingleFieldMetric.calculate_scores(state=state_total)
        return result

    def _format_result(self, result: dict[str, Any]) -> str:
        """Formats the result as a markdown table if specified, otherwise as pretty-printed JSON.

        Args:
            result: The result dictionary to format.
        Returns: A string representation of the result.
        """
        if self.format_as_markdown:
            # create pandas DataFrame and convert to markdown table
            df = DataFrame.from_dict(result, orient="index")
            df.index.name = "field"
            # round to 3 decimal places
            df = df.round(3)
            return df.to_markdown()
        else:
            return super()._format_result(result)
