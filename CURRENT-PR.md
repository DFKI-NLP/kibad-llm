# Add PDF dataset statistics command

Add `uv run -m kibad_llm.statistics.pdf` to summarize document counts, PDF pages, and
markdown characters across PDF folders and converted JSONL files, joined to the
Faktencheck metadata CSV. Output is aggregate JSON or Markdown, optionally grouped by
input folder or metadata column, with percentages of each retained total.

Identical duplicate metadata and markdown are accepted; conflicts fail. Duplicate PDFs
warn and keep the first occurrence. Missing metadata or markdown fails unless
`--skip-missing-metadata-or-md` is supplied. PyMuPDF is the default page reader;
`--dont-use-pymupdf` enables an approximate standard-library counter. The PR includes
usage and API documentation and 14 regression tests. No dependency or migration changes
are required. No linked issue or dependent PR.

## Reviewer testing

```bash
uv run --group cicd pytest tests/unit/statistics/test_pdf.py
uv run -m kibad_llm.statistics.pdf --help
```

## Reproducing the examples

Run the commands from the `kibad-llm` repository root after `uv sync`. The inputs require
access to the DFKI cluster, the private results repository, and the metadata spreadsheet;
they are not included in this repository.

### PDF files

`data/cluster-mirror` is a local copy of selected directories under `/ds/text/kiba-d/`
on the DFKI cluster. See [data/readme.md](/data/readme.md#dfki-cluster) for dataset origins.
Replace `USER@CLUSTER_HOST` with your cluster SSH login and copy the two test sets:

```bash
mkdir -p data/cluster-mirror/splits/test data/cluster-mirror/test-set-AuO-WVC
rsync -a USER@CLUSTER_HOST:/ds/text/kiba-d/splits/test/ data/cluster-mirror/splits/test/
rsync -a USER@CLUSTER_HOST:/ds/text/kiba-d/test-set-AuO-WVC/ data/cluster-mirror/test-set-AuO-WVC/
```

On the cluster itself, the original `/ds/text/kiba-d/...` paths can be passed directly
as `--pdf-path` instead.

### Converted markdown

Clone the private [kibad-llm-results repository](https://github.com/DFKI-NLP/kibad-llm-results)
using an account with access:

```bash
git clone git@github.com:DFKI-NLP/kibad-llm-results.git data/kibad-llm-results
```

The captured outputs use results revision `dc7afea1bcc5af89b8e400712b4886079e301256`.
At that revision, the core test markdown is stored under `faktencheck/test/`. To use the
`faktencheck/splits/test/` path in the example, create a local copy:

```bash
mkdir -p data/kibad-llm-results/data/processed/faktencheck/splits/test
cp data/kibad-llm-results/data/processed/faktencheck/test/predictions.jsonl.gz \
  data/kibad-llm-results/data/processed/faktencheck/splits/test/
```

Alternatively, pass `--markdown data/kibad-llm-results/data/processed/faktencheck/test`
directly. The AuO markdown already lives under `faktencheck/test-set-AuO-WVC/`.

### Metadata CSV

Open the [Faktencheck literature spreadsheet](https://docs.google.com/spreadsheets/d/1p7myxm5yAPq0MALP_GvVSoCf4ODSjU68/edit?gid=1666146796#gid=1666146796),
select its first sheet (gid `1666146796`), and use **File → Download → Comma-separated
values (.csv)** to export the current sheet. Create `data/external/faktencheck-db/` if
needed and save the download there as:

```text
Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv
```

The outputs below were captured on 2026-10-27 using the local CSV export with 2,282
metadata rows. Later spreadsheet edits or dataset updates can change the results.
The tables show stdout in full; expandable sections contain every warning line from
stderr. The package's timestamped startup INFO message is omitted.

## Core schema test set

```bash
uv run -m kibad_llm.statistics.pdf \
  --pdf-path data/cluster-mirror/splits/test \
  --markdown data/kibad-llm-results/data/processed/faktencheck/splits/test \
  --metadata "data/external/faktencheck-db/Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv" \
  --group-by "Item Type" \
  --skip-missing-metadata-or-md
```

500 input PDFs; 5 skipped for missing metadata; 495 retained.

| Group           | Documents |       % | Pages |       % | Markdown characters |       % |
| --------------- | --------: | ------: | ----: | ------: | ------------------: | ------: |
| Total           |       495 | 100.00% | 14014 | 100.00% |            49160257 | 100.00% |
| book            |        11 |   2.22% |  1626 |  11.60% |             4861600 |   9.89% |
| bookSection     |         6 |   1.21% |   246 |   1.76% |              754746 |   1.54% |
| conferencePaper |         2 |   0.40% |    21 |   0.15% |               66289 |   0.13% |
| dataset         |         1 |   0.20% |     1 |   0.01% |                6356 |   0.01% |
| document        |         3 |   0.61% |   130 |   0.93% |              303347 |   0.62% |
| journalArticle  |       437 |  88.28% |  7949 |  56.72% |            31414053 |  63.90% |
| report          |        29 |   5.86% |  3476 |  24.80% |            10429185 |  21.21% |
| statute         |         3 |   0.61% |   318 |   2.27% |              770966 |   1.57% |
| thesis          |         1 |   0.20% |   169 |   1.21% |              448371 |   0.91% |
| webpage         |         2 |   0.40% |    78 |   0.56% |              105344 |   0.21% |

<details>
<summary>All 5 warnings (stderr)</summary>

```text
Warning: data/cluster-mirror/splits/test/2M8D3H87.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/splits/test/P2VGFBIM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/splits/test/P4FN8ZWI.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/splits/test/PEI83BYF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/splits/test/PH6SH5I7.pdf: missing metadata; skipping PDF
```

</details>

## Organism trends test set (Agrar- und Offenland)

```bash
uv run -m kibad_llm.statistics.pdf \
  --pdf-path data/cluster-mirror/test-set-AuO-WVC \
  --markdown data/kibad-llm-results/data/processed/faktencheck/test-set-AuO-WVC \
  --metadata "data/external/faktencheck-db/Faktencheck Artenvielfalt Literaturdatenbank-neu.xlsx - Faktencheck Artenvielfalt Liter.csv" \
  --group-by "Item Type" \
  --skip-missing-metadata-or-md
```

430 input PDFs; 119 skipped for missing metadata; 311 retained.

| Group           | Documents |       % | Pages |       % | Markdown characters |       % |
| --------------- | --------: | ------: | ----: | ------: | ------------------: | ------: |
| Total           |       311 | 100.00% | 11392 | 100.00% |            41179941 | 100.00% |
| book            |        15 |   4.82% |  2179 |  19.13% |             7569377 |  18.38% |
| bookSection     |         6 |   1.93% |   298 |   2.62% |              768213 |   1.87% |
| conferencePaper |         1 |   0.32% |    13 |   0.11% |               41540 |   0.10% |
| dataset         |         1 |   0.32% |     1 |   0.01% |                6356 |   0.02% |
| document        |         4 |   1.29% |    56 |   0.49% |              184979 |   0.45% |
| journalArticle  |       259 |  83.28% |  4505 |  39.55% |            18345445 |  44.55% |
| report          |        22 |   7.07% |  4103 |  36.02% |            13489995 |  32.76% |
| thesis          |         1 |   0.32% |   200 |   1.76% |              568511 |   1.38% |
| webpage         |         2 |   0.64% |    37 |   0.32% |              205525 |   0.50% |

<details>
<summary>All 119 warnings (stderr)</summary>

```text
Warning: data/cluster-mirror/test-set-AuO-WVC/2FGZXCQF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/2LC3TGUC.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/2PC4XTM6.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/2X93WWI7.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/3ZRMQ4RA.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/4EB2FXQT.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/5EDY3ZBA.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/5F8D3S9K.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/5H52U5K3.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/5IS5WVWL.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/5PL8BP9K.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/5YAIBQ9X.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/6AY3ZPEH.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/6GNJEDBH.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/6YJE4V25.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/77QS7ENZ.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/7D6UINFM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/7YSU2PED.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/8IWCS3J6.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/8WDEHG4H.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/93MTUBJK.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/9BHEC934.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/9H4JI3V7.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/A3V37ZGJ.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/A6QHZ8WN.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/A7YB359Z.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/AEXBSVRF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Albrecht_Bachthaler_1990.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/BZ9VT4U2.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/CICX9559.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/CTSMKZSZ.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/CWNR8562.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/CY6WGFFF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/D4URBSFM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/DMV3CC9C.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/DUR7PBEY.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/E9UTINDD.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/EDADDHV3.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/EM9KUWLJ.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/EMJGFNR5.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/EZAHJMIL.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Engler2002.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/FS4XC56S.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/G4P32JKB.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/G8P2BUDM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/GDZ5IDIZ.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/GJFXSS2U.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/GSLW6Z8Y.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/GUZQSANY.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/H4QVLNBD.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/HFRQA4Z9.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/HSVNL4YX.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/HWIBTSCE.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Heinrich1998.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/I6SPA7SB.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/JCJWDNUR.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/JF54B87I.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/JGCE5IZA.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/K3F9HPRW.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/KEBWUAG4.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/KIGI6UA3.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/KURW6KPF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/KYR3L2G5.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/L6A8TIF8.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/LAVCYXMU.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/LD3FUW72.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/LJRVLY6M.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/LU5MISRE.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/M6N3P3V6.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/MJUGJWPS.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/MNLULZBP.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/MPERTLZ8.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/MSC9BKIF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/MXJ7YET8.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/NDZ2SUT3.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/NTJWRS7G.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/NYXFMFKA.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Nentwig1988.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/PH6SH5I7.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/PTJEPIET.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Q3RDFEMM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Q4E8K8D2.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Q84JUIXB.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/QQC4XMAM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/QRMNR2AU.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/RCP477YD.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/RPDVXNGC.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/RRZEFTM6.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/S8A8TRAN.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/S9PCRPBY.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/TECSZ9VH.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/TZ8RW2IT.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/U5ZQC2Z8.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/U9GQQMXR.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/UBCZ83MB.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/UDGFY5NG.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/UL946NX7.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/USQ9AGRF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/UUQJIFFH.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/V3IPXL5J.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/V4YDTX4U.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/V6A4VBGZ.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/V8F5I2CM.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/VBCP6AHU.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/VKY98JWF.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/W35X2UGT.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/WB3CWSCG.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/WV3G4AIU.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/XPWAD5WL.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/XWF6H9Y7.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/XYWHBZ6X.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/XZ3TNC36.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/YGMKNXWW.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/YKAXBJKI.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/YU7JSAZ5.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/YUP79LR6.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/Z4WRX8KG.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/ZGUQZDAR.pdf: missing metadata; skipping PDF
Warning: data/cluster-mirror/test-set-AuO-WVC/ZVXC3I83.pdf: missing metadata; skipping PDF
```

</details>

## Validation

<details>
<summary>Click to expand</summary>

- `uv run --group cicd prek run -a`: passed all hooks.
- `uv run --group cicd pytest -m "not slow"`: 635 passed, 1 deselected.
- `node --test tests/unit/eval_dashboard/js/*.test.mjs`: 207 passed.
- `uv run --group cicd properdocs build`: passed.
- `lychee --config lychee.toml --root-dir ./site "site/**/*.html"`: passed, 0 errors.

</details>
