from collections.abc import Hashable


def merge_references_into_predictions(
    predictions: dict,
    references: dict,
) -> dict[Hashable, dict[str, dict]]:
    """Create a new Dataset with entries "prediction" and "reference" by merging references
    into predictions based on matching IDs. If no matching reference is found for a prediction,
    the "reference" field will be an empty dict.

    Args:
        predictions: Dataset containing prediction entries.
        references: Dataset containing reference entries.
    Returns:
        A new Dataset where each entry contains a "prediction" and its corresponding "reference".
    """

    merged_dataset = {
        k: {"prediction": predictions[k], "reference": references[k]} for k in predictions
    }
    return merged_dataset
