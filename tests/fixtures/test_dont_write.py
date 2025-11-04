from tests.conftest import WRITE_FIXTURE_DATA


def test_dont_write_fixture_data():
    assert not WRITE_FIXTURE_DATA, "WRITE_FIXTURE_DATA is set to True, please set it to False!"
