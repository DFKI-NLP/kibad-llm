"""Scientific-name normalization helpers.

Modules:
    gbif: Resolve scientific names against the GBIF Species Match API.
"""

from .gbif import normalize_spezies, normalize_spezies_batch

__all__ = [
    "normalize_spezies",
    "normalize_spezies_batch",
]
