# Add PDF dataset statistics command

Add `uv run -m kibad_llm.statistics.pdf` to summarize document counts, PDF pages, and markdown characters across PDF folders and converted JSONL files, optionally joined to the Faktencheck metadata CSV. Output is aggregate JSON or Markdown, optionally grouped by input folder or metadata column, with percentages of each retained total. Without `--metadata`, totals and grouping by input folder work without metadata matching; grouping by a CSV column requires `--metadata`.

Identical duplicate metadata and markdown are accepted; conflicts fail. Duplicate PDFs warn and keep the first occurrence. Missing markdown or matches in a supplied metadata CSV fail unless `--skip-missing-metadata-or-md` is supplied. PyMuPDF is the default page reader; `--dont-use-pymupdf` enables an approximate standard-library counter. The PR includes usage and API documentation and 18 regression tests. No dependency or migration changes are required. No linked issue or dependent PR.

## Reviewer testing

```bash
uv run --group cicd pytest tests/unit/statistics/test_pdf.py
uv run -m kibad_llm.statistics.pdf --help
```

## Reproducing the examples

Run the commands from the `kibad-llm` repository root after `uv sync`. The inputs require access to the DFKI cluster, the private results repository, and the metadata spreadsheet; they are not included in this repository.

### PDF files

`data/cluster-mirror` is a local copy of selected directories under `/ds/text/kiba-d/` on the DFKI cluster. See [data/readme.md](/data/readme.md#dfki-cluster) for dataset origins. Replace `USER@CLUSTER_HOST` with your cluster SSH login and copy the two test sets:

```bash
mkdir -p data/cluster-mirror/splits/test data/cluster-mirror/test-set-AuO-WVC
rsync -a USER@CLUSTER_HOST:/ds/text/kiba-d/splits/test/ data/cluster-mirror/splits/test/
rsync -a USER@CLUSTER_HOST:/ds/text/kiba-d/test-set-AuO-WVC/ data/cluster-mirror/test-set-AuO-WVC/
```

On the cluster itself, the original `/ds/text/kiba-d/...` paths can be passed directly as `--pdf-path` instead.

### Converted markdown

Clone the private [kibad-llm-results repository](https://github.com/DFKI-NLP/kibad-llm-results) using an account with access:

```bash
git clone git@github.com:DFKI-NLP/kibad-llm-results.git data/kibad-llm-results
```

The captured outputs use results revision `dc7afea1bcc5af89b8e400712b4886079e301256`. The core test markdown is stored under `faktencheck/test/`; the AuO markdown lives under `faktencheck/test-set-AuO-WVC/`.

### Metadata CSV

Open the [Faktencheck literature spreadsheet](https://docs.google.com/spreadsheets/d/1wiBPKG4SmiSNppC1-_qXzz__GIuxa3-C/edit?rtpof=true&gid=1666146796#gid=1666146796), select its first sheet (gid `1666146796`), and use **File → Download → Comma-separated values (.csv)** to export the current sheet. Create `data/external/faktencheck-db/` if needed and save this freshly downloaded CSV there as:

```text
Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv
```

The outputs below were rerun on 2026-10-28 using the corrected CSV export with 4,748 metadata rows (SHA-256: `4e4c5657f39a25982c932263e9ff8721b58244632c8053fd6c6cce05c240ec08`). Later spreadsheet edits or dataset updates can change the results. The tables show stdout in full; expandable sections contain every warning line from stderr. The package's timestamped startup INFO message is omitted.

## Core schema test set

```bash
uv run -m kibad_llm.statistics.pdf \
  --pdf-path data/cluster-mirror/splits/test \
  --markdown data/kibad-llm-results/data/processed/faktencheck/test \
  --metadata "data/external/faktencheck-db/Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv" \
  --group-by "Item Type" \
  --skip-missing-metadata-or-md
```

500 input PDFs; all 500 retained.

| Group           | Documents |       % | Pages |       % | Markdown characters |       % |
| --------------- | --------: | ------: | ----: | ------: | ------------------: | ------: |
| Total           |       500 | 100.00% | 14069 | 100.00% |            49373192 | 100.00% |
| book            |        11 |   2.20% |  1626 |  11.56% |             4861600 |   9.85% |
| bookSection     |         6 |   1.20% |   246 |   1.75% |              754746 |   1.53% |
| conferencePaper |         2 |   0.40% |    21 |   0.15% |               66289 |   0.13% |
| dataset         |         1 |   0.20% |     1 |   0.01% |                6356 |   0.01% |
| document        |         3 |   0.60% |   130 |   0.92% |              303347 |   0.61% |
| journalArticle  |       441 |  88.20% |  7990 |  56.79% |            31624816 |  64.05% |
| report          |        29 |   5.80% |  3476 |  24.71% |            10429185 |  21.12% |
| statute         |         3 |   0.60% |   318 |   2.26% |              770966 |   1.56% |
| thesis          |         1 |   0.20% |   169 |   1.20% |              448371 |   0.91% |
| webpage         |         3 |   0.60% |    92 |   0.65% |              107516 |   0.22% |

No warnings were emitted.

## Organism trends test set (Agrar- und Offenland)

```bash
uv run -m kibad_llm.statistics.pdf \
  --pdf-path data/cluster-mirror/test-set-AuO-WVC \
  --markdown data/kibad-llm-results/data/processed/faktencheck/test-set-AuO-WVC \
  --metadata "data/external/faktencheck-db/Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv" \
  --group-by "Item Type" \
  --skip-missing-metadata-or-md
```

430 input PDFs; 4 skipped for missing metadata; 426 retained.

| Group           | Documents |       % | Pages |       % | Markdown characters |       % |
| --------------- | --------: | ------: | ----: | ------: | ------------------: | ------: |
| Total           |       426 | 100.00% | 13110 | 100.00% |            46884787 | 100.00% |
| book            |        18 |   4.23% |  2469 |  18.83% |             8615093 |  18.38% |
| bookSection     |         6 |   1.41% |   298 |   2.27% |              768213 |   1.64% |
| conferencePaper |         1 |   0.23% |    13 |   0.10% |               41540 |   0.09% |
| dataset         |         1 |   0.23% |     1 |   0.01% |                6356 |   0.01% |
| document        |         4 |   0.94% |    56 |   0.43% |              184979 |   0.39% |
| journalArticle  |       371 |  87.09% |  5933 |  45.26% |            23004575 |  49.07% |
| report          |        22 |   5.16% |  4103 |  31.30% |            13489995 |  28.77% |
| thesis          |         1 |   0.23% |   200 |   1.53% |              568511 |   1.21% |
| webpage         |         2 |   0.47% |    37 |   0.28% |              205525 |   0.44% |

<details>
<summary>All 4 warnings (stderr)</summary>

```text
Warning: data/cluster-mirror/test-set-AuO-WVC/Albrecht_Bachthaler_1990.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Engler2002.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Heinrich1998.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Nentwig1988.pdf: missing metadata; skipping PDF
```

</details>

## Validation

<details>
<summary>Click to expand</summary>

- `uv run --group cicd prek run -a`: passed all hooks.
- `uv run --group cicd pytest -m "not slow"`: 639 passed, 1 deselected.
- `node --test tests/unit/eval_dashboard/js/*.test.mjs`: 207 passed.
- `uv run --group cicd properdocs build`: passed.
- `lychee --config lychee.toml --root-dir ./site "site/**/*.html"`: passed, 0 errors.

</details>

## TODO

- [ ] remove CURRENT-PR.md before merge
