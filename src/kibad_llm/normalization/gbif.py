"""GBIF name normalization helpers.

Functions:
    normalize_spezies: Resolve a scientific name to GBIF's canonical name.
    normalize_spezies_batch: Resolve multiple scientific names in one GBIF request.
"""

import requests

GBIF_SPECIES_MATCH_URL = "https://api.gbif.org/v1/species/match"
GBIF_SPECIES_BATCH_MATCH_URL = "https://api.gbif.org/v2/species/match"


def normalize_spezies(
    name: str,
    min_confidence: float | None = None,
    query_param: str = "scientificName",
    response_field: str = "canonicalName",
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
    query_param: str = "scientificName",
    response_field: str = "canonicalName",
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
    """
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
    """Validate an optional GBIF confidence percentage."""
    if min_confidence is not None and not 0 <= min_confidence <= 100:
        raise ValueError("min_confidence must be between 0 and 100")


def _normalize_match_result(
    result: object,
    min_confidence: float | None,
    response_field: str,
) -> str | None:
    """Normalize one GBIF Species Match API result."""
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
