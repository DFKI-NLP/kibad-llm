# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

`kibad-llm` is an information-extraction project supporting the [Literaturdatenbank Faktencheck
Artenvielfalt](https://www.feda.bio/de/literaturdatenbank-faktencheck-artenvielfalt/). It uses LLMs to extract
structured information from scientific literature PDFs, via a Hydra-configured pipeline for prediction
(`kibad_llm.predict`) and evaluation (`kibad_llm.evaluate`) against reference data.

Full documentation lives at https://dfki-nlp.github.io/kibad-llm/, sourced from `docs/`. Read these before
larger changes — they are authoritative and detailed:

- `docs/USAGE.md` — how to run PDF download, DB conversion, prediction, evaluation, multirun, A/B testing.
- `docs/CONTRIBUTING.md` — project layout, branch naming, PR requirements, local CI commands, submodules.
- `docs/CONTRIBUTING-CODE.md` — coding principles, test layout, docstring style, dependency changes.
- `docs/CONTRIBUTING-EXPERIMENTS.md` — how to plan/name/run/document a reproducible experiment.
- `docs/data-readme.md` (-> `/data/readme.md`) — dataset and reference-file descriptions.

## Setup

Package/dependency management is via `uv` (**not** poetry/pip, despite `Makefile` referencing poetry — that
Makefile is legacy/unmaintained; prefer the `just` recipes or raw `uv run` commands below).

```bash
uv sync --group cicd        # install with dev/CI dependencies (types, pytest, docs tooling, ...)
cp .env.example .env         # then fill in OPENAI_API_KEY / HF_TOKEN / DB_USER / DB_PASSWORD as needed
```

`just -l` lists convenience recipes (`just` itself defaults to `just pr`, which runs `prek` + tests).

## Common commands

Run everything through `uv run` (or `just`, which wraps the same commands). All commands assume the repo root.

```bash
# Full local CI-equivalent (required before claiming "CI-ready"/"passes local CI"):
uv run --group cicd prek run -a
uv run --group cicd pytest -m "not slow"
node --test tests/unit/eval_dashboard/js/*.test.mjs
uv run --group cicd properdocs build
lychee --config lychee.toml --root-dir ./site "site/**/*.html"
# or just: just pr

# Single test:
uv run pytest tests/unit/extractors/test_base.py::test_extract_from_text

# Prediction pipeline (Hydra entry point):
uv run -m kibad_llm.predict pdf_directory=path/to/pdf/files

# Evaluation pipeline (Hydra entry point):
uv run -m kibad_llm.evaluate dataset.predictions.file=path/to/predictions.jsonl

# Hydra multirun (comma-separated overrides + --multirun), e.g. compare extractors:
uv run -m kibad_llm.predict pdf_directory=path/to/pdf/files extractor=simple_with_schema,simple --multirun
```

`prek` (see `.pre-commit-config.yaml`) runs black, isort, pyupgrade, flake8, nbqa (notebooks), mdformat, bandit,
codespell, zuban-mypy, check-mkdocs, properdocs-build, and lychee. If lychee can't run locally (old glibc), skip
it with `SKIP=lychee uv run prek run -a`.

### Fixture regeneration (extractor/predict tests)

```bash
WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py tests/integration/test_predict.py
# only if you also need to refresh LLM replay fixtures (requires a running vLLM backend, see models/README.md):
WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py::test_extractor[chunking]
# mandatory afterwards — check for now-unused LLM chat fixtures:
uv run --group cicd python tests/fixtures/map_llm_chat_usage.py
```

Never run the full suite with either `WRITE_FIXTURE_DATA` flag set — only regenerate fixtures for the tests you
intentionally changed.

## Architecture

### Two Hydra entry points, one extraction core

The package has two `hydra.main` CLI entry points, both configured from `configs/`:

- `kibad_llm/predict.py` (`configs/predict.yaml`) — reads all PDFs in `pdf_directory`, converts each to markdown
    via a configured `pdf_reader`, runs a configured `extractor` over the text, and writes a JSONL file of
    structured predictions. Uses HuggingFace `datasets.Dataset.map()` for the PDF-read and extraction steps (this
    is also how disk caching and multiprocessing, `pdf_reader_num_proc`/`extractor_num_proc`, are controlled).
- `kibad_llm/evaluate.py` (`configs/evaluate.yaml`) — loads a `dataset` (predictions + references, from
    `configs/dataset/`), runs a configured `metric` over each record, and writes aggregate scores.

Both increment a version constant (`PREDICT_VERSION`, `EVALUATE_VERSION`) whenever the output format changes in
a backwards-incompatible way — bump these alongside such changes.

Every config group under `configs/` (`extractor/`, `dataset/`, `metric/`, `pdf_reader/`, `paths/`, `hydra/`) is
instantiated via `hydra.utils.instantiate`, so config YAML and Python `__init__` signatures must stay in sync.
`configs/experiment/predict/` and `configs/experiment/evaluate/` hold named, reproducible overrides for whole
experiment setups — prefer adding a new experiment config over ad hoc CLI overrides for anything non-trivial.

### Extraction core (`src/kibad_llm/extractors/`)

`extractors/base.py::extract_from_text` is the single-call primitive: builds chat messages from a
`prompt_template` (system/user templates with `{document}`/`{schema_description}` placeholders), optionally
uses JSON-schema guided decoding, calls an `LLM`, validates/parses the JSON response, and can wrap schema
terminals with evidence metadata (`adjust_schema_for_evidence_detection`) to get verbatim anchors for extracted
values, which are then matched back into the source text and stripped back out (`augment_metadata` /
`strip_metadata`) to also produce a metadata-free "clean" structured output.

Higher-level extractors compose this primitive and are all configured under `configs/extractor/`:

- `ChunkingExtractor` (`chunking.py`) — splits long documents (using `chunking_utils/`) and extracts per chunk.
- `UnionExtractor` (`union.py`) — runs multiple passes with different parameter overrides, merges results.
- `ConditionalUnionExtractor` (`conditional.py`) — multi-pass extraction carrying chat history between passes.
- `RepeatingExtractor` (`repeat.py`) — repeats extraction and aggregates via majority vote.

An extractor instance is a `Callable[[text, file_name], dict]`, matching what `predict.py` maps over the
dataset.

### LLM backends (`src/kibad_llm/llms/`)

`llms/base.py::LLM` is the abstract interface (`call_llm_chat_with_guided_decoding` plus response-parsing
helpers). Three implementations, selected via `configs/extractor/llm/`:

- `openai.py` — OpenAI-hosted models (e.g. gpt-5); needs `OPENAI_API_KEY`.
- `openai_like_vllm.py` — externally vLLM-hosted, OpenAI-compatible endpoint (e.g. gpt-oss); see
    `models/README.md` and `run_with_llm.sh` for starting the server.
- `vllm_in_process.py` — vLLM loaded in-process (used on cluster compute nodes via `run_in_process.sh`); needs
    `HF_TOKEN` for gated HF models.

### Schema, dataset, and metrics

- `schema/` — JSON-schema types/helpers (`types.py`, `utils.py`) used to build schema descriptions for prompts
    and to wrap/unwrap evidence metadata.
- `dataset/` — loaders (`csv.py`, `json.py`, `compression.py`, `prediction.py`) that assemble the
    predictions/references pairing consumed by `evaluate.py`; instantiated from `configs/dataset/`.
- `metrics/` — `Metric` implementations (`f1.py`, `tpfpfn.py`, `confusion_matrix.py`, `errors.py`) built around a
    shared `update(prediction, reference, record_id)` / `compute()` interface from `metric.py`; selected via
    `configs/metric/`.
- `data_integration/` — one-off/standalone scripts (not part of the extraction pipeline) for Zotero PDF
    download, Faktencheck Postgres→JSON conversion (`db_converter.py`), scientific-name normalization against
    GBIF (`normalization/`), and Nextcloud↔cluster PDF syncing. See `docs/USAGE.md` for invocation details.

### Result/log layout

Local runs write to top-level `logs/<name>/...` and `predictions/<name>/...` (never committed). Committed
experiment artefacts (from finished experiments) live in the `data/results` git submodule, under
`data/results/logs/<name>` and `data/results/predictions/<name>` — see `docs/CONTRIBUTING-EXPERIMENTS.md` for
the full experiment workflow (naming, submodule branching, eval-dashboard inspection, documentation).

## Repo conventions worth knowing

- **Submodule**: `data/results` is a separate repo (`kibad-llm-results`); it starts in detached HEAD after a
    plain clone, so `git switch -c <branch>` inside it before committing there. See
    `docs/CONTRIBUTING.md#submodules`.
- **Docstrings are mandatory**: every file, class, function, and method needs a Google-style, CommonMark-only
    docstring (no Sphinx/reST) — this is enforced by convention, not currently by CI. See
    `docs/CONTRIBUTING-CODE.md#documentation` for the exact section-heading vocabulary
    (`Args`/`Attributes`/`Raises`/`Warns`/`Warning`/etc.) and the relative-link syntax used for cross-referencing
    Python objects in docs.
- **Tests mirror source layout**: unit tests under `tests/unit/` mirror `src/kibad_llm/`; integration tests
    under `tests/integration/` mirror `configs/` and prefer exercising real Hydra configs
    (`tests/conftest.py::cfg_global`/`cfg_predict`) over ad hoc mocks. Tests needing a live LLM must be marked
    `slow` (excluded from CI) — prefer the `llm_chat_replay` fixture instead.
- **Branch naming**: `feat/`, `fix/`, `hotfix/`, `docs/`, `experiment/` prefixes; alphanumeric + hyphens only, no
    double/trailing hyphens. Pushing to `main` is prohibited; PRs must be reviewed and are squash-merged.
