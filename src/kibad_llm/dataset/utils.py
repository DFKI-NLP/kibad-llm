from collections.abc import Callable, Hashable

from datasets import Dataset


def merge_references_into_predictions(
    predictions: Dataset,
    references: Dataset,
    predictions_id_key: str,
    references_id_key: str,
    process_predictions_id: Callable[..., Hashable] | None = None,
    process_references_id: Callable[..., Hashable] | None = None,
) -> Dataset:
    """Create a new Dataset with entries "prediction" and "reference" by merging references
    into predictions based on matching IDs. If no matching reference is found for a prediction,
    the "reference" field will be an empty dict.

    Args:
        predictions: Dataset containing prediction entries.
        references: Dataset containing reference entries.
        predictions_id_key: The field name in predictions used to match with references.
        references_id_key: The field name in references used to match with predictions.
        process_predictions_id: Optional function to process prediction IDs before matching.
        process_references_id: Optional function to process reference IDs before matching.
    Returns:
        A new Dataset where each entry contains a "prediction" and its corresponding "reference".
    """

    # Create a mapping from reference IDs to reference entries
    process_references_id = process_references_id or (lambda x: x)
    reference_map = {
        entry[process_references_id(references_id_key)]: entry for entry in references
    }

    process_predictions_id = process_predictions_id or (lambda x: x)

    def _merge_entry(prediction_entry):
        instance_id = process_predictions_id(prediction_entry[predictions_id_key])
        reference_entry = reference_map.get(instance_id, {})
        return {"prediction": prediction_entry, "reference": reference_entry}

    merged_dataset = predictions.map(_merge_entry)
    return merged_dataset
