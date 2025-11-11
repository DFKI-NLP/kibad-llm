from enum import Enum
import re

from pydantic import BaseModel

from kibad_llm.schema import types


def camel_case_to_snake_case(name: str) -> str:
    """Convert CamelCase string to snake_case string."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


# get all Pydantic models defined in kibad_llm.schema.types, excluding Enums
ALL_MODELS = [
    obj
    for obj in vars(types).values()
    if isinstance(obj, type)
    and issubclass(obj, BaseModel)
    and obj is not BaseModel
    and not issubclass(obj, Enum)
]
