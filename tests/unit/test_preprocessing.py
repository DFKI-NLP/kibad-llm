import json

from kibad_llm.config import PROJ_ROOT
from kibad_llm.preprocessing import read_pdf_as_markdown


def test_read_pdf_as_markdown():
    file_name = "25ABQZIH.pdf"

    # get expected markdown from fixture
    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    markdown_expected = markdown_data["text"]

    result = read_pdf_as_markdown(
        file_name=file_name, base_path=PROJ_ROOT / "tests" / "fixtures" / "pdfs"
    )

    assert isinstance(result, dict)
    assert set(result) == {"text"}
    markdown = result["text"]

    assert markdown == markdown_expected
