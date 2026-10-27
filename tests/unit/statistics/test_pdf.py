"""Regression coverage for the standalone statistics script."""

import csv
import gzip
import importlib.util
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from kibad_llm.statistics import pdf as pdf_stats


class PdfStatsTest(unittest.TestCase):
    """Check input joins, duplicate policies, grouping, and aggregate output."""

    def setUp(self):
        """Create nested PDF and markdown inputs and stub page counting."""
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.folders = [self.root / "alpha", self.root / "beta"]
        for folder in self.folders:
            folder.mkdir()
        (self.folders[0] / "A.pdf").touch()
        nested = self.folders[1] / "nested"
        nested.mkdir()
        (nested / "B.pdf").touch()
        self.metadata = self.root / "metadata.csv"
        self.write_metadata([["A", "en"], ["B", ""]])
        self.markdown = self.root / "markdown"
        deep = self.markdown / "nested" / "deep"
        deep.mkdir(parents=True)
        (self.markdown / "a.jsonl").write_text(
            json.dumps({"file_name": "A.pdf", "text": "ä\n"}) + "\n", encoding="utf-8"
        )
        with gzip.open(deep / "b.jsonl.gz", "wt", encoding="utf-8") as stream:
            stream.write(json.dumps({"file_name": "B.pdf", "text": "abc"}) + "\n")
        (deep / "ignored.txt").write_text("not JSON", encoding="utf-8")
        self.argv = [
            "--pdf-path",
            *map(str, self.folders),
            "--markdown",
            str(self.markdown),
            "--metadata",
            str(self.metadata),
        ]
        counter = patch.object(
            pdf_stats, "count_pages", side_effect=lambda path, _: {"A": 2, "B": 3}[path.stem]
        )
        self.count_pages = counter.start()
        self.addCleanup(counter.stop)

    def write_metadata(self, rows):
        """Replace the metadata fixture with the supplied rows.

        Args:
            rows (list[list[str]]): Metadata key and language pairs.
        """
        with self.metadata.open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.writer(stream)
            writer.writerow(["Key", "Language"])
            writer.writerows(rows)

    def collect(self, *options):
        """Collect a report using the fixture inputs and extra CLI options.

        Args:
            *options (str): Additional argument strings.

        Returns:
            report (dict): Aggregate report for the fixture inputs.
        """
        return pdf_stats.collect(pdf_stats.parse_args([*self.argv, *options]))

    def test_recursive_gzip_totals_and_metadata_percentages(self):
        """Count Unicode characters and load nested gzip files into CSV groups."""
        report = self.collect("--group-by", "Language")
        self.assertEqual(report["total"]["documents"], 2)
        self.assertEqual(report["total"]["pages"], 5)
        self.assertEqual(report["total"]["markdown_characters"], 5)
        empty, english = report["groups"]
        self.assertEqual(empty["group"], "")
        self.assertEqual(english["group"], "en")
        self.assertEqual(english["documents_percent"], 50)
        self.assertEqual(english["pages_percent"], 40)
        self.assertEqual(english["markdown_characters_percent"], 40)
        self.assertTrue(self.count_pages.call_args.args[1])

    def test_pdf_path_groups_use_input_folders(self):
        """Attribute nested PDFs to their supplied input folder."""
        report = self.collect("--group-by", "pdf-path")
        self.assertEqual([row["group"] for row in report["groups"]], list(map(str, self.folders)))

    def test_identical_metadata_rows_are_accepted(self):
        """Accept repeated metadata rows without counting a document twice."""
        self.write_metadata([["A", "en"], ["A", "en"], ["B", ""]])
        self.assertEqual(self.collect()["total"]["documents"], 2)

    def test_conflicting_metadata_fails(self):
        """Reject differing metadata rows for the same key."""
        self.write_metadata([["A", "en"], ["A", "de"]])
        with self.assertRaisesRegex(ValueError, "conflicting content for 'A'"):
            self.collect()

    def test_identical_markdown_is_accepted_across_explicit_and_folder_inputs(self):
        """Accept identical markdown despite differences in unused prediction fields."""
        duplicate = self.root / "duplicate.jsonl"
        duplicate.write_text(
            json.dumps({"file_name": "A.pdf", "text": "ä\n", "structured": {}}) + "\n",
            encoding="utf-8",
        )
        report = self.collect("--markdown", str(duplicate))
        self.assertEqual(report["total"]["markdown_characters"], 5)

    def test_conflicting_markdown_fails_even_with_same_character_count(self):
        """Compare markdown content rather than only its character count."""
        (self.markdown / "duplicate.jsonl").write_text(
            json.dumps({"file_name": "A.pdf", "text": "ab"}) + "\n", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "conflicting content for 'A.pdf'"):
            self.collect()

    def test_duplicate_pdfs_warn_and_keep_first_input_folder(self):
        """Warn about duplicate PDF stems and keep the first folder's counts."""
        (self.folders[1] / "A.pdf").touch()
        with patch("sys.stderr", new_callable=io.StringIO) as stderr:
            report = self.collect("--group-by", "pdf-path", "--pdf-path", str(self.folders[0]))
        self.assertEqual(report["total"]["documents"], 2)
        self.assertEqual(report["groups"][0]["pages"], 2)
        self.assertEqual(stderr.getvalue().count("Duplicate PDF"), 2)
        self.assertEqual(self.count_pages.call_count, 2)

    def test_missing_metadata_or_markdown_fails_or_warns_and_skips(self):
        """Fail on missing matches by default and skip them only when requested."""
        for missing in ("metadata", "markdown"):
            with self.subTest(missing=missing):
                self.write_metadata(
                    [["A", "en"]] if missing == "metadata" else [["A", "en"], ["B", ""]]
                )
                if missing == "markdown":
                    (self.markdown / "a.jsonl").unlink()
                with self.assertRaisesRegex(ValueError, f"missing {missing}"):
                    self.collect()
                with patch("sys.stderr", new_callable=io.StringIO) as stderr:
                    report = self.collect("--skip-missing-metadata-or-md")
                self.assertEqual(report["total"]["documents"], 1)
                self.assertEqual(report["total"]["documents_percent"], 100)
                self.assertIn(f"missing {missing}", stderr.getvalue())

    def test_empty_markdown_and_zero_totals(self):
        """Retain empty markdown and produce zero percentages for empty totals."""
        for file in self.markdown.rglob("*.jsonl*"):
            file.unlink()
        (self.markdown / "empty.jsonl").write_text(
            json.dumps({"file_name": "A.pdf", "text": ""}) + "\n", encoding="utf-8"
        )
        self.write_metadata([["A", "en"]])
        with patch("sys.stderr", new_callable=io.StringIO):
            report = self.collect("--skip-missing-metadata-or-md")
        self.assertEqual(report["total"]["documents"], 1)
        self.assertEqual(report["total"]["markdown_characters_percent"], 0)
        (self.folders[0] / "A.pdf").unlink()
        with patch("sys.stderr", new_callable=io.StringIO):
            report = self.collect("--skip-missing-metadata-or-md")
        self.assertTrue(all(value == 0 for value in report["total"].values()))

    def test_unknown_csv_column_fails(self):
        """Reject a grouping column absent from the metadata CSV."""
        with self.assertRaisesRegex(ValueError, "Unknown --group-by"):
            self.collect("--group-by", "Missing")

    def test_json_output_contains_only_aggregates(self):
        """Print valid JSON without individual PDF records."""
        with (
            patch("sys.argv", ["pdf.py", *self.argv, "--format", "json"]),
            patch("sys.stdout", new_callable=io.StringIO) as stdout,
        ):
            pdf_stats.main()
        report = json.loads(stdout.getvalue())
        self.assertEqual(report["groups"], [])
        self.assertEqual(report["total"]["documents"], 2)
        self.assertNotIn("A.pdf", stdout.getvalue())

    def test_markdown_escapes_group_labels(self):
        """Escape table delimiters and newlines and label empty CSV groups."""
        self.write_metadata([["A", "en|de\nfr"], ["B", ""]])
        with patch("sys.stdout", new_callable=io.StringIO) as stdout:
            pdf_stats.print_markdown(self.collect("--group-by", "Language"))
        self.assertIn(r"en\|de<br>fr", stdout.getvalue())
        self.assertIn("(empty)", stdout.getvalue())
        self.assertNotIn("A.pdf", stdout.getvalue())


class PageCountTest(unittest.TestCase):
    """Check reader selection and page counts for compressed PDF objects."""

    def test_dependency_free_counter_and_flags(self):
        """Default to PyMuPDF and reject zero matches in the approximate reader."""
        self.assertTrue(
            pdf_stats.parse_args(
                ["--pdf-path", ".", "--markdown", ".", "--metadata", "m.csv"]
            ).use_pymupdf
        )
        for option in ("--dont-use-pymupdf", "--dont-use-pymudf"):
            self.assertFalse(
                pdf_stats.parse_args(
                    ["--pdf-path", ".", "--markdown", ".", "--metadata", "m.csv", option]
                ).use_pymupdf
            )
        with TemporaryDirectory() as folder:
            path = Path(folder) / "test.pdf"
            path.write_bytes(b"/Type /Pages /Type /Page\n/Type/Page\n")
            self.assertEqual(pdf_stats.count_pages(path, False), 2)
            path.write_bytes(b"/Type /Pages")
            with self.assertRaisesRegex(ValueError, "no uncompressed page objects"):
                pdf_stats.count_pages(path, False)

    @unittest.skipUnless(importlib.util.find_spec("pymupdf"), "PyMuPDF is not installed")
    def test_pymupdf_counts_compressed_page_objects(self):
        """Read compressed page objects that the marker approximation cannot find."""
        import pymupdf

        with TemporaryDirectory() as folder:
            path = Path(folder) / "compressed.pdf"
            with pymupdf.open() as document:
                document.new_page()
                document.new_page()
                document.save(path, use_objstms=1, deflate=True)
            self.assertEqual(pdf_stats.count_pages(path, True), 2)
            with self.assertRaises(ValueError):
                pdf_stats.count_pages(path, False)


if __name__ == "__main__":
    unittest.main()
