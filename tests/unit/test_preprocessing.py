import json

from kibad_llm.config import PROJ_ROOT
from kibad_llm.preprocessing import read_pdf_as_markdown_via_pymupdf4llm
from tests.conftest import WRITE_FIXTURE_DATA


def test_read_pdf_as_markdown_via_pymupdf4llm():
    file_name = "25ABQZIH.pdf"

    result = read_pdf_as_markdown_via_pymupdf4llm(
        file_name=file_name, base_path=PROJ_ROOT / "tests" / "fixtures" / "pdfs"
    )

    assert isinstance(result, str)

    markdown_path = PROJ_ROOT / "tests" / "fixtures" / "markdown" / f"{file_name}.json"

    if WRITE_FIXTURE_DATA:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        # write fixture data
        with open(markdown_path, "w") as f:
            json.dump({"text": result}, f, indent=4, ensure_ascii=False)

    # get expected markdown from fixture
    with open(markdown_path) as f:
        markdown_data = json.load(f)
    result_expected = markdown_data["text"]

    assert result == result_expected
