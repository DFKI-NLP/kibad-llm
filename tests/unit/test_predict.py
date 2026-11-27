"""Tests for `kibad_llm.predict`."""

from contextlib import nullcontext
from functools import partial

from datasets import Dataset

from kibad_llm import predict as predict_module
from kibad_llm import preprocessing
from kibad_llm.predict import convert_pdfs_to_markdown
from kibad_llm.preprocessing import read_pdf_as_markdown_via_pymupdf4llm
from tests.unit.test_preprocessing import _write_pdf_without_unicode_mapping


def test_convert_pdfs_to_markdown_ignores_cache_of_previous_reader(tmp_path, monkeypatch):
    """Markdown cached by an older PDF reader revision is not reused after the reader changed."""
    text = "Land use-induced changes in raised bog peats"
    pdf_dir = tmp_path / "pdfs"
    pdf_dir.mkdir()
    _write_pdf_without_unicode_mapping(pdf_dir / "no_unicode.pdf", text)
    # a dataset backed by cache files, like the one created in `predict`
    Dataset.from_dict({"file_name": ["no_unicode.pdf"]}).save_to_disk(tmp_path / "dataset")
    dataset = Dataset.load_from_disk(tmp_path / "dataset")
    # same as instantiating configs/pdf_reader/pymupdf4llm.yaml
    pdf_reader = partial(read_pdf_as_markdown_via_pymupdf4llm)

    # populate the cache with the previous reader revision (no CID fallback, U+FFFD output)
    monkeypatch.setattr(preprocessing, "_use_cid_for_unknown_unicode", nullcontext)
    monkeypatch.setattr(
        predict_module, "PREPROCESSING_VERSION", predict_module.PREPROCESSING_VERSION - 1
    )
    result_old = convert_pdfs_to_markdown(dataset, pdf_reader=pdf_reader, base_path=pdf_dir)
    assert preprocessing.REPLACEMENT_CHARACTER in result_old[0]["text"]
    assert len(dataset.cache_files) > 0

    # rerun with the current reader on the same (cached) dataset
    monkeypatch.undo()
    result_new = convert_pdfs_to_markdown(dataset, pdf_reader=pdf_reader, base_path=pdf_dir)
    assert result_new[0]["text"].strip() == text
    assert result_new.cache_files != result_old.cache_files
