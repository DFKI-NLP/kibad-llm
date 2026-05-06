"""Test package root — exposes ``FIXTURE_DATA_ROOT`` for locating shared fixture files."""

from kibad_llm.config import PROJ_ROOT

FIXTURE_DATA_ROOT = PROJ_ROOT / "tests" / "fixtures"
