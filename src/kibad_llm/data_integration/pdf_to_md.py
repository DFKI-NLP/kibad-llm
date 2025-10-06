"""
This script takes a pdf from the database and converts it to a txt file
It uses the pymupdf package and is not yet modularized
Usage of the converted markdowns is here https://pymupdf.readthedocs.io/en/latest/rag.html
"""

import json
import pathlib

import pymupdf4llm


def convert_pdf_to_text(input_pdf_path, output_md_path):
    md_text = pymupdf4llm.to_markdown(input_pdf_path)
    pathlib.Path(output_md_path).write_bytes(md_text.encode())


def read_jsonl_with_filenames(input_jsonl, output_folder):
    with open(input_jsonl) as input_file:
        for jline in input_file:
            file_name = json.loads(jline)["zotitem_ptr_id"]
            convert_pdf_to_text(f"./{file_name}", f"{output_folder}/{file_name}")


if __name__ == "__main__":
    read_jsonl_with_filenames(
        "data/interim/faktencheck-db/faktencheck-db-converted_2025-08-19.jsonl", "data/processed"
    )
