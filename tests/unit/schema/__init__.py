"""Shared helpers and model lists for schema unit tests.

Exports ``camel_case_to_snake_case``, ``ALL_MODELS`` (all non-base Pydantic models
from :mod:`kibad_llm.schema.types`), and ``ALL_COMPOUNDS`` (all
:class:`~kibad_llm.schema.types.CompoundFeature` subclasses), used by
:mod:`tests.unit.schema.test_types` and :mod:`tests.unit.schema.test_utils` to
parametrize tests over every schema model.
"""

import re

from kibad_llm.schema import types


def camel_case_to_snake_case(name: str) -> str:
    """Convert CamelCase string to snake_case string."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# get all Pydantic models defined in kibad_llm.schema.types, excluding Enums
ALL_MODELS = [
    obj
    for obj in vars(types).values()
    if isinstance(obj, type)
    and issubclass(obj, types.BaseEcosystemStudyFeatures)
    and obj is not types.BaseEcosystemStudyFeatures
]

ALL_COMPOUNDS = [
    obj
    for obj in vars(types).values()
    if isinstance(obj, type)
    and issubclass(obj, types.CompoundFeature)
    and obj is not types.CompoundFeature
]
