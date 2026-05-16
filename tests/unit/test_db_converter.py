"""Unit tests for :func:`kibad_llm.data_integration.db_converter.format_result`."""

from kibad_llm.data_integration.db_converter import format_result


def test_format_result_single_value() -> None:
    result = ({"result": 42},)
    column_names = ["answer"]
    formatted = format_result(result, column_names)
    assert formatted == {"result": 42}
