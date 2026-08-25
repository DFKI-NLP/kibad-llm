from collections.abc import Hashable
import logging

from kibad_llm.dataset.prediction import DictWithMetadata

logger = logging.getLogger(__name__)


def merge_references_into_predictions(
    predictions: dict,
    references: dict,
    allow_missing_references: bool = False,
    allow_missing_predictions: bool = False,
    verbose: bool = False,
) -> dict[Hashable, dict[str, dict]]:
    """Create a new Dataset with entries "prediction" and "reference" by merging references
    into predictions based on matching IDs.

    Args:
        predictions: Dataset containing prediction entries.
        references: Dataset containing reference entries.
        allow_missing_references: If True, allows predictions without corresponding references.
            This will fill missing references with empty dictionaries. If False, raises an error
            if any prediction is missing a reference.
        allow_missing_predictions: If True, allows references without corresponding predictions.
            If False, raises an error if any reference is missing a prediction.
            IMPORTANT: In either case, evaluation is only performed if the prediction is
            present, so missing predictions will not be evaluated. However, support (=TP+FN)
            calculation will be affected.
        verbose: If True, logs warnings for any missing references.
    Returns:
        A new Dataset where each entry contains a "prediction" and its corresponding "reference".
    """

    missing_references = set(predictions) - set(references)
    if missing_references:
        if not allow_missing_references:
            raise ValueError(f"Missing references for the following keys: {missing_references}")
        elif verbose:
            logger.warning(
                f"Missing references for the following keys: {missing_references}. "
                "Filling missing references with empty dictionaries."
            )
    missing_predictions = set(references) - set(predictions)
    if missing_predictions:
        if not allow_missing_predictions:
            raise ValueError(f"Missing predictions for the following keys: {missing_predictions}")
        elif verbose:
            logger.warning(
                f"Missing predictions for the following keys: {missing_predictions}. "
                "IMPORTANT: Evaluation is only performed if the prediction is present, "
                "so missing predictions will not be evaluated. However, support (=TP+FN) "
                "calculation will be affected."
            )

    merged_dataset = {
        k: {"prediction": predictions[k], "reference": references.get(k, {})}
        for k in set(predictions)
    }

    if isinstance(predictions, DictWithMetadata):
        merged_dataset = DictWithMetadata(
            merged_dataset,
            metadata=predictions.metadata,
        )

    return merged_dataset
