"""GBIF name normalization helpers.

Functions:
    normalize_spezies: Resolve a scientific name to GBIF's canonical name.
    normalize_spezies_batch: Resolve multiple scientific names in one GBIF request.
    process_json_lines_file: Normalize names in a JSON Lines file.
"""

import argparse
import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger(__name__)


GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_SPECIES_BATCH_MATCH_URL = "https://api.gbif.org/v2/species/match"
DEFAULT_QUERY_PARAM = "scientificName"
DEFAULT_RESPONSE_FIELD = "canonicalName"


def normalize_spezies(
    name: str,
    min_confidence: float | None = None,
    query_param: str = DEFAULT_QUERY_PARAM,
    response_field: str = DEFAULT_RESPONSE_FIELD,
) -> str | None:
    """Resolve a species name to GBIF's canonical name.

    Args:
        name: Species name to resolve.
        min_confidence: Optional minimum GBIF match confidence percentage required to return a name.
        query_param: Query parameter name used to send `name` to GBIF.
        response_field: Response field containing the normalized species name.

    Returns:
        The canonical scientific name returned by GBIF, or `None` if no match is found or the
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

    return _normalize_match_result(result, min_confidence, response_field)


def normalize_spezies_batch(
    names: list[str],
    min_confidence: float | None = None,
    query_param: str = DEFAULT_QUERY_PARAM,
    response_field: str = DEFAULT_RESPONSE_FIELD,
) -> list[str | None]:
    """Resolve scientific names to GBIF's canonical names in one request.

    Args:
        names: Scientific names to resolve. GBIF accepts up to 1,000 names per request.
        min_confidence: Optional minimum GBIF match confidence percentage required to return a name.
        query_param: Request-object field name used to send each scientific name to GBIF.
        response_field: Response field containing each normalized scientific name.

    Returns:
        Canonical scientific names in the same order as `names`, with `None` for unmatched or
        insufficient-confidence entries.

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

    return [_normalize_match_result(result, min_confidence, response_field) for result in results]


def _validate_min_confidence(min_confidence: float | None) -> None:
    """Validate an optional GBIF confidence percentage.

    Args:
        min_confidence: Minimum acceptable GBIF match confidence percentage, or `None` to
            disable confidence filtering.

    Raises:
        ValueError: If `min_confidence` is outside the inclusive range from 0 to 100.
    """
    if min_confidence is not None and not 0 <= min_confidence <= 100:
        raise ValueError("min_confidence must be between 0 and 100")


def _normalize_match_result(
    result: object,
    min_confidence: float | None,
    response_field: str,
) -> str | None:
    """Extract a normalized name from one GBIF Species Match API result.

    Args:
        result: Response object returned for a single GBIF name-match request.
        min_confidence: Minimum acceptable GBIF match confidence percentage, or `None` to
            disable confidence filtering.
        response_field: Name of the response field containing the normalized scientific name.

    Returns:
        The normalized scientific name, or `None` when GBIF reports no match or the result
        does not meet `min_confidence`.

    Raises:
        ValueError: If `result` is not a valid GBIF match response, does not contain a string
            in `response_field`, or lacks a numeric confidence required for filtering.
    """
    if not isinstance(result, dict):
        raise ValueError("GBIF returned an invalid match response")

    if result.get("matchType") == "NONE":
        return None

    canonical_name = result.get(response_field)
    if not isinstance(canonical_name, str):
        raise ValueError("GBIF returned a match without a canonical name")

    if min_confidence is not None:
        confidence = result.get("confidence")
        if not isinstance(confidence, (int, float)):
            raise ValueError("GBIF returned a match without a numeric confidence")
        if confidence < min_confidence:
            return None

    return canonical_name


def _normalize_names(
    name: str | list[str], **kwargs
) -> tuple[str | None | list[str | None], int, int]:
    """Normalize a scientific name or a homogeneous list of scientific names.

    Args:
        name: A scientific name or a list of scientific names.
        kwargs: Additional keyword arguments to pass to normalize_spezies function.

    Returns:
        A tuple consisting of:
            - The normalized name, or a list of normalized names in the original order.
            - The number of names processed.
            - The number of names successfully normalized.
    """
    if isinstance(name, list):
        if not all(isinstance(item, str) for item in name):
            raise TypeError("Species name lists must contain only strings")
        normalized_names = [normalize_spezies(item, **kwargs) for item in name]
        return (
            normalized_names,
            len(name),
            len([item for item in normalized_names if item is not None]),
        )

    normalized_name = normalize_spezies(name, **kwargs)
    return normalized_name, 1, 1 if normalized_name is not None else 0


def _process_json_object(
    json_value: object, parent_keys: list[str], read_key: str, write_key: str, **kwargs
) -> tuple[int, int]:
    """Find JSON objects through nested dictionaries and lists, then write normalized names.

    Args:
        json_value: Current JSON value to process.
        parent_keys: Remaining dictionary keys to navigate before reading a name.
        read_key: Key containing the name or list of names to normalize.
        write_key: Key receiving the normalized name or list of normalized names.
        kwargs: Additional keyword arguments to pass to normalize_spezies function.

    Returns:
        A tuple consisting of:
         - The number of names processed.
         - The number of names successfully normalized.
    """
    num_processed, num_normalized = 0, 0
    if isinstance(json_value, list):
        for item in json_value:
            new_processed, new_normalized = _process_json_object(
                item, parent_keys, read_key, write_key, **kwargs
            )
            num_processed += new_processed
            num_normalized += new_normalized
        return num_processed, num_normalized

    if not isinstance(json_value, dict):
        return 0, 0

    if parent_keys:
        child = json_value.get(parent_keys[0])
        if child is not None:
            new_processed, new_normalized = _process_json_object(
                child, parent_keys[1:], read_key, write_key, **kwargs
            )
            return new_processed, new_normalized
        return 0, 0

    name = json_value.get(read_key)
    if name is None:
        return num_processed, num_normalized
    if not isinstance(name, (str, list)):
        raise TypeError("Species names must be a string or a list of strings")
    json_value[write_key], new_processed, new_normalized = _normalize_names(name, **kwargs)

    return new_processed, new_normalized


def process_json_lines_file(
    input_path: str,
    read_key: str,
    output_path: str | None = None,
    write_key: str | None = None,
    parent_keys: list[str] | None = None,
    **kwargs,
) -> None:
    """Normalize names in a JSON Lines file.

    Args:
        input_path: Path to the input JSON Lines file.
        read_key: Key to extract the species name or list of names from each JSON object.
        output_path: Path to the normalized JSON Lines file. If not provided,
            the output file will be named "{input_path.stem}_normalized_names.json".
        write_key: Key to write the normalized species name or list of normalized names to.
            If not provided, the result will be written to "{read_key}_normalized.json".
        parent_keys: Parent keys to navigate before reading a name. Each level may contain a
            nested dictionary or a list of nested dictionaries.
        kwargs: Additional keyword arguments to pass to normalize_spezies function.
    """
    logger.info(f"Normalizing species names in JSON Lines file: {input_path}")
    _output_file = output_path or f"{Path(input_path).stem}_normalized_names.json"
    write_key = write_key or f"{read_key}_normalized"
    num_processed, num_normalized, num_lines = 0, 0, 0
    with open(input_path) as input_file:
        with open(_output_file, "w") as output_file:
            for line in input_file:
                json_obj = json.loads(line)
                new_processed, new_normalized = _process_json_object(
                    json_obj, parent_keys or [], read_key, write_key, **kwargs
                )
                num_processed += new_processed
                num_normalized += new_normalized
                output_file.write(json.dumps(json_obj) + "\n")
                num_lines += 1
    logger.info(
        f"Processed {num_lines} lines, normalized {num_normalized} names out of {num_processed} processed."
    )
    logger.info(f"Result was written to: {_output_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        description="Normalize species names in a JSON Lines file using GBIF's Species Match API.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("input_path", help="Path to the input JSON Lines file.")
    parser.add_argument(
        "output_path",
        default=None,
        help="Path to the output JSON Lines file. If not provided, the "
        "output file will be named '{input_path.stem}_normalized_names.json'.",
    )
    parser.add_argument(
        "read_key", help="Key to read the species name or list of names from each JSON object."
    )
    parser.add_argument(
        "write_key",
        default=None,
        help="Key to write the normalized species name or list of normalized names to. "
        "If not provided, the result will be written to '{read_key}_normalized'.",
    )
    parser.add_argument(
        "--parent-keys",
        nargs="*",
        default=[],
        help="Parent keys to navigate before reading a name. Each level may contain a nested dictionary "
        "or a list of nested dictionaries.",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=None,
        help="Minimum GBIF match confidence percentage required to return a name.",
    )
    parser.add_argument(
        "--query-param",
        default=DEFAULT_QUERY_PARAM,
        help="Query parameter name used to send the species name to GBIF.",
    )
    parser.add_argument(
        "--response-field",
        default=DEFAULT_RESPONSE_FIELD,
        help="Response field containing the normalized species name.",
    )
    args = parser.parse_args()

    kwargs = vars(args)
    process_json_lines_file(**kwargs)
