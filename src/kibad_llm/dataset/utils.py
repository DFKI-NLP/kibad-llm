from collections.abc import Hashable


def merge_references_into_predictions(
    predictions: dict,
    references: dict,
    allow_missing_references: bool = False,
) -> dict[Hashable, dict[str, dict]]:
    """Create a new Dataset with entries "prediction" and "reference" by merging references
    into predictions based on matching IDs.

    Args:
        predictions: Dataset containing prediction entries.
        references: Dataset containing reference entries.
        allow_missing_references: If True, allows predictions without corresponding references.
            This will fill missing references with empty dictionaries. If False, raises an error
            if any prediction is missing a reference.
    Returns:
        A new Dataset where each entry contains a "prediction" and its corresponding "reference".
    """
    if not allow_missing_references:
        missing_keys = set(predictions) - set(references)
        if missing_keys:
            raise ValueError(f"Missing references for the following keys: {missing_keys}")

    merged_dataset = {
        k: {"prediction": predictions[k], "reference": references.get(k, {})} for k in predictions
    }
    return merged_dataset
