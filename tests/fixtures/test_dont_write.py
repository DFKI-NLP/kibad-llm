"""Guard test ensuring ``WRITE_FIXTURE_DATA`` is ``False`` before any test run.

This file is collected by pytest directly inside ``tests/fixtures/`` so the guard
runs even when only fixture-adjacent tests are executed.
"""

from tests.conftest import WRITE_FIXTURE_DATA


def test_dont_write_fixture_data():
    assert not WRITE_FIXTURE_DATA, "WRITE_FIXTURE_DATA is set to True, please set it to False!"
