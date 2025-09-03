"""This module contains the query types for the database."""

from enum import Enum
from typing import Any


class ListableEnum(Enum):
    """An Enum class whose values can be converted into a list."""
    @classmethod
    def list(cls) -> list[Any]:
        """
        Converts the Enum values into a list.

        Returns:
            list[Any]: a list of the Enum values
        """
        return list(map(lambda c: c.value, cls))


class Queries(ListableEnum):
    """A class representing the queries for the database."""
    SINGLE: str = "SELECT * FROM users"


class QueryTypes(ListableEnum):
    """A class representing the query types for the database."""
    SINGLE: str = "single"


if __name__ == "__main__":
    raise NotImplementedError
