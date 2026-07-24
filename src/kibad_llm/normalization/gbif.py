"""GBIF name normalization helpers.

Functions:
    normalize_spezies: Resolve a scientific name to GBIF's canonical name.
    normalize_spezies_batch: Resolve multiple scientific names in one GBIF request.
"""

import argparse
from collections.abc import Callable
from functools import partial

import requests

GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_SPECIES_BATCH_MATCH_URL = "https://api.gbif.org/v2/species/match"
DEFAULT_QUERY_PARAM = "scientificName"
DEFAULT_RESPONSE_FIELD = "canonicalName"


def normalize_spezies(
    name: str,
    min_confidence: int | None = None,
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
    min_confidence: int | None = None,
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
        "--response-field",
        default=DEFAULT_RESPONSE_FIELD,
        help="Response field containing the normalized species name.",
    )


def create_normalizer(arguments: argparse.Namespace) -> Callable[[str], str | None]:
    """Create a GBIF normalizer from parsed command-line arguments."""
    return partial(
        normalize_spezies,
        min_confidence=arguments.min_confidence,
        query_param=arguments.query_param,
        response_field=arguments.response_field,
    )
