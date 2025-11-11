import re

from kibad_llm.schema.types import (
    EcosystemStudyFeaturesSimple,
    EcosystemStudyFeaturesWithoutCompounds,
)


def camel_case_to_snake_case(name: str) -> str:
    """Convert CamelCase string to snake_case string."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


ALL_MODELS = [EcosystemStudyFeaturesSimple, EcosystemStudyFeaturesWithoutCompounds]
