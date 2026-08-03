"""GBIF name normalization helpers.

Functions:
    normalize_spezies: Resolve a scientific name to GBIF's canonical name.
    normalize_spezies_batch: Resolve multiple scientific names in one GBIF request.
"""

import argparse
from collections.abc import Callable
from copy import copy
from functools import partial
import logging
from typing import Any, TypeAlias, TypeGuard

import requests

GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v2/species/match"
GBIF_SPECIES_BATCH_MATCH_URL = "https://api.gbif.org/v2/species/match"
DEFAULT_QUERY_PARAM = "scientificName"

logger = logging.getLogger(__name__)


def normalize_spezies(
    name: str,
    min_confidence: int | None = None,
    query_param: str = DEFAULT_QUERY_PARAM,
    response_fields: list[str] | None = None,
) -> dict[str, Any] | None:
    """Resolve a species name to GBIF's canonical name.

    Args:
        name: Species name to resolve.
        min_confidence: Optional minimum GBIF match confidence percentage required to return a name.
        query_param: Query parameter name used to send `name` to GBIF.
        response_fields: List of GBIF response fields to return. If not provided, all fields will be returned.

    Returns:
        A dictionary containing the requested GBIF response fields, or `None` if no match is found or the
        match does not meet `min_confidence`.

    Raises:
        ValueError: If `min_confidence` is not between 0 and 100, inclusive.
        ValueError: If GBIF returns an invalid match response.
        requests.RequestException: If the GBIF Species Match API request fails.
        requests.HTTPError: If the GBIF Species Match API returns a non-200 status code.
    """
    _validate_min_confidence(min_confidence)

    response = requests.get(
        GBIF_SPECIES_MATCH_URL,
        params={query_param: name},
        timeout=10,
    )
    response.raise_for_status()
    result = response.json()

    return _normalize_match_result(result, min_confidence, response_fields)


def normalize_spezies_batch(
    names: list[str],
    min_confidence: int | None = None,
    query_param: str = DEFAULT_QUERY_PARAM,
    response_fields: list[str] | None = None,
) -> list[dict[str, Any] | None]:
    """Resolve scientific names to GBIF's canonical names in one request.

    Args:
        names: Scientific names to resolve. GBIF accepts up to 1,000 names per request.
        min_confidence: Optional minimum GBIF match confidence percentage required to return a name.
        query_param: Request-object field name used to send each scientific name to GBIF.
        response_fields: List of GBIF response fields to return. If empty, all fields will be returned.

    Returns:
        A list of dictionaries containing the requested GBIF response fields, or `None` for names that
        have no match or do not meet `min_confidence`. The order of the returned list matches the order of
        the input `names`.

    Raises:
        ValueError: If `min_confidence` is not between 0 and 100, inclusive.
        ValueError: If GBIF returns an invalid batch match response.
        requests.RequestException: If the GBIF Species Match API request fails.
        requests.HTTPError: If the GBIF Species Match API returns a non-200 status code.
    """
    if len(names) > 1000:
        raise ValueError(
            f"Too many Scientific names to resolve ({len(names)}). GBIF accepts up to 1,000 names per request."
        )

    _validate_min_confidence(min_confidence)

    response = requests.post(
        GBIF_SPECIES_BATCH_MATCH_URL,
        json=[{query_param: name} for name in names],
        timeout=10,
    )
    response.raise_for_status()
    results = response.json()

    if not isinstance(results, list) or len(results) != len(names):
        raise ValueError("GBIF returned an invalid batch match response")

    return [_normalize_match_result(result, min_confidence, response_fields) for result in results]


def _validate_min_confidence(min_confidence: int | None) -> None:
    """Validate an optional GBIF confidence percentage.

    Args:
        min_confidence: Minimum acceptable GBIF match confidence percentage, or `None` to
            disable confidence filtering.

    Raises:
        ValueError: If `min_confidence` is outside the inclusive range from 0 to 100.
    """
    if min_confidence is not None and not 0 <= min_confidence <= 100:
        raise ValueError("min_confidence must be between 0 and 100")


Terminal: TypeAlias = str | int | float | list[Any] | tuple[Any, ...] | None
NestedDict: TypeAlias = dict[str, "NestedDict | Terminal"]
NestedValue: TypeAlias = NestedDict | Terminal


def _is_nested_dict(value: NestedValue) -> TypeGuard[NestedDict]:
    """Return whether a nested value is another nested dictionary."""
    return isinstance(value, dict)


def _filter_nested_dict(
    nested_dict: NestedDict,
    keep_fields: list[str],
    sep: str = ".",
) -> NestedDict:
    """Keep selected fields from a nested dictionary.

    Fields can use the specified separator to access nested fields, such as ``"author.name"``.
    Missing paths and paths that traverse through terminal values are ignored.

    Args:
        nested_dict: Nested dictionary to filter.
        keep_fields: List of fields to keep. Each field can be a nested path using the specified separator.
        sep: Separator used to split nested field paths. Defaults to ".".

    Returns:
        A new nested dictionary containing only the requested fields.
    """
    filtered_dict: NestedDict = {}

    for field in keep_fields:
        if not field:
            continue

        keys = field.split(sep)
        current_source = nested_dict

        for key in keys[:-1]:
            source_value = current_source.get(key)

            # The requested path either does not exist or passes through
            # a terminal value.
            if not _is_nested_dict(source_value):
                break
            current_source = source_value
        else:
            last_key = keys[-1]
            if last_key not in current_source:
                continue

            current_target = filtered_dict
            for key in keys[:-1]:
                target_value = current_target.get(key)
                if _is_nested_dict(target_value):
                    current_target = target_value
                else:
                    next_target: NestedDict = {}
                    current_target[key] = next_target
                    current_target = next_target
            current_target[last_key] = current_source[last_key]

    return filtered_dict


def _normalize_match_result(
    response: object,
    min_confidence: float | None,
    response_fields: list[str] | None = None,
) -> NestedDict | None:
    """Extract a normalized name from one GBIF Species Match API result.

    Args:
        response: Response object returned for a single GBIF name-match request.
        min_confidence: Minimum acceptable GBIF match confidence percentage, or `None` to
            disable confidence filtering.
        response_fields: List of GBIF response fields to return. If not provided, all fields will be returned.
            Entries can contain "." to access nested fields, e.g. "classification.KINGDOM".

    Returns:
        A dictionary containing the requested GBIF response fields, or `None` if no match is found or the result
        does not meet `min_confidence`.

    Raises:
        ValueError: If `result` is not a valid GBIF match response, does not contain a string
            in `response_fields`, or lacks a numeric confidence required for filtering.
    """
    if not isinstance(response, dict):
        raise ValueError("GBIF returned an invalid match response")

    if response["diagnostics"].get("matchType") == "NONE":
        return None

    # entries in "classification" have this format:
    # {
    #   "key": "6",
    #   "name": "Plantae",
    #   "rank": "KINGDOM"
    # },
    classification_as_dict = {
        value["rank"]: value["name"] for value in response.get("classification", [])
    }

    result = copy(response)
    result["classification"] = classification_as_dict

    if min_confidence is not None:
        confidence = response["diagnostics"].get("confidence")
        # the GBIF match endpoint returns confidence as integer percentages
        if not isinstance(confidence, int):
            raise ValueError("GBIF returned a match without a numeric confidence value")
        if confidence < min_confidence:
            return None

    if response_fields is not None:
        result = _filter_nested_dict(result, response_fields)

    return result


def add_arguments(parser: argparse.ArgumentParser) -> None:
    """Add GBIF Species Match API options to a command-line parser."""
    parser.add_argument(
        "--min-confidence",
        type=int,
        default=None,
        help="Minimum GBIF match confidence percentage required to return a name.",
    )
    parser.add_argument(
        "--query-param",
        default=DEFAULT_QUERY_PARAM,
        help="Query parameter name used to send the species name to GBIF.",
    )
    parser.add_argument(
        "--response-fields",
        default=None,
        nargs="+",
        help="GBIF response fields returned from the GBIF Species Match API. If not provided, "
        "all fields will be returned. Entries can contain '.' to access nested fields, "
        "e.g. 'classification.KINGDOM'.",
    )


def create_normalizer(arguments: argparse.Namespace) -> Callable[[str], dict[str, Any] | None]:
    """Create a GBIF normalizer from parsed command-line arguments."""
    logger.info(
        f"Creating GBIF normalizer with query_param={arguments.query_param}, "
        f"response_fields={arguments.response_fields}, and min_confidence={arguments.min_confidence}"
    )
    return partial(
        normalize_spezies,
        min_confidence=arguments.min_confidence,
        query_param=arguments.query_param,
        response_fields=arguments.response_fields,
    )
