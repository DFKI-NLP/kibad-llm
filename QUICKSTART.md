# Quickstart

A cheat sheet for getting `kibad-llm` running and understanding how it fits together. This project uses LLMs
to extract structured information from scientific literature PDFs, supporting the
[Literaturdatenbank Faktencheck Artenvielfalt](https://www.feda.bio/de/literaturdatenbank-faktencheck-artenvielfalt/).
For anything not covered here, see [Where to go deeper](#where-to-go-deeper) below.

## Setup

Requires [uv](https://docs.astral.sh/uv/) ([install guide](https://docs.astral.sh/uv/getting-started/installation/)).

```bash
git clone https://github.com/DFKI-NLP/kibad-llm
cd kibad-llm

uv sync --group cicd        # installs the project plus dev/CI tooling (lint, test, docs)
cp .env.example .env         # then fill in the variables you need, see below
```

`.env` variables (all optional, only needed for the features that use them):

- `OPENAI_API_KEY` — required to run extraction with OpenAI-hosted models (e.g. `gpt_5`). Create a key at
  [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
- `HF_TOKEN` — required for access-restricted Hugging Face models (e.g. `gemma3_27b`), and for the in-process
  vLLM backend. Create a token at [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens).
- `VLLM_DOWNLOAD_DIR` — optional, where in-process vLLM caches downloaded model weights.
- `DB_USER` / `DB_PASSWORD` — only needed for the Faktencheck Postgres database, see
  [podman/faktencheck-db/README.md](/podman/faktencheck-db/README.md).

> [!TIP]
> If you're new to `uv`: wherever you'd normally write `python ...`, write `uv run python ...` (or, for the
> project's own CLI entry points, `uv run -m kibad_llm....`) — no need to manually activate a virtualenv.

## Getting data in

- **PDFs from Zotero**: `uv run -m kibad_llm.data_integration.zotero_download` downloads open-access papers
  found via Semantic Scholar from an exported Zotero-group CSV (see
  [data/external/zotero](/data/external/zotero)). Details:
  [docs/USAGE.md § PDF Download](/docs/USAGE.md#pdf-download-based-on-zotero-groups).
- **Faktencheck reference data**: the ground-truth database lives in Postgres. Start it with Podman (see
  [podman/faktencheck-db/README.md](/podman/faktencheck-db/README.md)), then convert it to JSON with
  `uv run -m kibad_llm.data_integration.db_converter`. Scientific names in the converted data can be normalized
  against GBIF via `uv run -m kibad_llm.normalization.cli gbif ...`. Details:
  [docs/USAGE.md § Faktencheck Postgres to Json Conversion](/docs/USAGE.md#faktencheck-postgres-to-json-conversion).
- **What's already available**: [data/readme.md](/data/readme.md) documents the existing PDF sets and
  reference/ground-truth files, so check there before re-downloading or re-converting anything.

## Running the extraction pipeline

### Prerequisite: host an LLM

Prediction needs a running LLM backend, chosen per extractor config under
[configs/extractor/llm/](/configs/extractor/llm/):

- **OpenAI-hosted** (e.g. `gpt_5`) — just needs `OPENAI_API_KEY`, no separate hosting step.
- **External vLLM server** (`*_in_process.yaml`'s sibling, an OpenAI-compatible endpoint you start yourself) —
  see [models/README.md](/models/README.md) and `run_with_llm.sh`.
- **In-process vLLM** (`*_in_process.yaml`, model loaded inside the same process; used on the DFKI cluster via
  `run_in_process.sh`) — needs `HF_TOKEN` for gated models.

Follow [models/README.md § Quickstart](/models/README.md#quickstart) or
[§ All-in-one run script](/models/README.md#all-in-one-run-script) to get one running.

### Run a prediction

```bash
uv run -m kibad_llm.predict pdf_directory=path/to/pdf/files
```

Converts every PDF in `pdf_directory` to markdown, runs the configured `extractor` over it, and writes a JSONL
predictions file. Options live in [configs/predict.yaml](/configs/predict.yaml); `pdf_reader_num_proc` and
`extractor_num_proc` control parallelism (keep them modest on shared/personal machines, large on compute
nodes). For a reproducible setup, use a named config instead of ad hoc overrides:

```bash
uv run -m kibad_llm.predict pdf_directory=path/to/pdf/files experiment/predict=faktencheck_two_schemata
```

See [configs/experiment/predict](/configs/experiment/predict) for available experiment configs and
[docs/USAGE.md § Inference](/docs/USAGE.md#inference) for the full picture.

### Run an evaluation

```bash
uv run -m kibad_llm.evaluate dataset.predictions.file=path/to/predictions.jsonl
```

Scores predictions against reference data. Defaults to `dataset=faktencheck` and `metric=f1_micro`
(micro-averaged precision/recall/F1 over all fields); swap either via `dataset=<name>` /
`metric=<name>` — see [configs/dataset](/configs/dataset) and [configs/metric](/configs/metric). As with
prediction, prefer a named `experiment/evaluate=<config>` for anything you'll want to reproduce (see
[configs/experiment/evaluate](/configs/experiment/evaluate)). Full details, including the
`confusion_matrix` metric's per-field requirement:
[docs/USAGE.md § Evaluation](/docs/USAGE.md#evaluation).

### Multirun and A/B testing

Both entry points support [Hydra multirun](https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/):
pass comma-separated values for one or more parameters plus `--multirun` (`-m`), and Hydra runs every
combination — e.g. `extractor=simple_with_schema,simple --multirun` to compare guided vs. unguided decoding, or
`seed=42,1337,7331 --multirun` for repeated runs. Add
`+hydra.callbacks.save_job_return.multirun_markdown_group_by=<column(s)>` to `evaluate` to get aggregated
mean/std across runs. See [docs/USAGE.md § Multirun](/docs/USAGE.md#multirun) for worked examples.

## Inspect results

Runs write to `logs/<name>/...` and `predictions/<name>/...` locally (git-ignored). Each run produces a
`job_return_value.json`/`.md` with output paths or metric scores; multiruns get a combined summary. Finished,
committed experiments live in the `data/results` submodule instead — see
[Repo conventions](#repo-conventions) below. Browse and compare runs (local, from the repo, or from a GitHub
URL) in the build-free [evaluation dashboard](/docs/eval-dashboard-docs.md).

## How it fits together

Everything is wired through Hydra config groups under [configs/](/configs/) via `_target_`, so adding a new
LLM, extractor, metric, or dataset means adding both a Python class/function and a matching YAML.

- **Extractors** ([src/kibad_llm/extractors/](/src/kibad_llm/extractors/)) all share the contract
  `(text, file_name) -> dict` and compose: a single LLM call at the core (builds a prompt from a schema derived
  from the pydantic models in [src/kibad_llm/schema/types.py](/src/kibad_llm/schema/types.py), optionally with
  guided decoding), wrapped by `ChunkingExtractor` (splits long documents), `UnionExtractor` /
  `ConditionalUnionExtractor` (multiple passes, merged or chained), and `RepeatingExtractor` (majority vote).
- **LLM backends** ([src/kibad_llm/llms/](/src/kibad_llm/llms/)) share one interface over the three hosting
  options described above (`openai.py`, `openai_like_vllm.py`, `vllm_in_process.py`).
- **Evaluation** ([src/kibad_llm/evaluate.py](/src/kibad_llm/evaluate.py)) pairs a `dataset` (predictions +
  references, matched on file name / record id, see [src/kibad_llm/dataset/](/src/kibad_llm/dataset/)) with a
  `metric` implementing `reset`/`update`/`compute` (see [src/kibad_llm/metrics/](/src/kibad_llm/metrics/)).
- **Data integration** ([src/kibad_llm/data_integration/](/src/kibad_llm/data_integration/)) holds the
  standalone Zotero/Postgres/GBIF/Nextcloud scripts mentioned above — these aren't part of the extraction
  pipeline itself.

## Testing and before a PR

```bash
just pr          # prek (lint/format/docs) + the full test suite — run this before claiming CI-readiness
just prek         # just the lint/format/docs checks
just pytest       # just the Python tests
just node-test    # eval-dashboard JS logic tests (needs Node)
just prop         # serve the docs locally
```

`just -l` lists everything, including the raw `uv run ...`/`lychee` invocations these recipes wrap. A single
test: `uv run pytest tests/unit/extractors/test_base.py::test_extract_from_text`. Tests hitting a real LLM must
be marked `slow` (excluded from the default run) — prefer the `llm_chat_replay` fixture instead. If you touch a
test that uses recorded fixtures, regenerate only that test's fixtures:

```bash
WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py tests/integration/test_predict.py
uv run --group cicd python tests/fixtures/map_llm_chat_usage.py   # mandatory afterwards: flags now-unused fixtures
```

Never set `WRITE_FIXTURE_DATA`/`WRITE_LLM_CHAT_FIXTURE_DATA` for a full test-suite run — only for the tests you
intentionally changed.

## Repo conventions

- **Docstrings are mandatory** on every file, class, function, and method — Google-style, CommonMark only (no
  Sphinx/reST). See [docs/CONTRIBUTING-CODE.md § Documentation](/docs/CONTRIBUTING-CODE.md#documentation).
- **Tests mirror source layout**: `tests/unit/` mirrors `src/kibad_llm/`, `tests/integration/` mirrors
  `configs/` and prefers real Hydra configs over mocks.
- **Branch naming**: `feat/`, `fix/`, `hotfix/`, `docs/`, `experiment/` prefixes, alphanumeric + hyphens only.
  Pushing to `main` is prohibited; PRs are reviewed and squash-merged.
- **`data/results` is a separate git submodule** (committed experiment artefacts, logs and predictions). It
  starts in detached HEAD after a plain clone — run `git switch -c <branch>` inside it before committing there.
- **`uv.lock`** is managed via `uv add`/`uv lock`, never hand-edited; explain dependency changes in the PR.
- **Windows**: `uv sync --group cicd` fails there (`vllm` → `ray` ships no `win_amd64` wheels). Run
  lint/test/docs commands on Linux/macOS, WSL, or the cluster.
- For planning, naming, and documenting a full reproducible experiment (not just a one-off run), see
  [docs/CONTRIBUTING-EXPERIMENTS.md](/docs/CONTRIBUTING-EXPERIMENTS.md).

## Where to go deeper

- [docs/USAGE.md](/docs/USAGE.md) — the full walkthrough: PDF download, DB conversion, prediction, evaluation,
  multirun and A/B testing, all with complete option lists.
- [docs/CONTRIBUTING.md](/docs/CONTRIBUTING.md) — full directory map, PR workflow, docs-site rules, submodule
  handling, the complete local-CI command set.
- [docs/CONTRIBUTING-CODE.md](/docs/CONTRIBUTING-CODE.md) — coding principles, test layout, docstring/linking
  conventions, fixture regeneration, dependency changes.
- [docs/CONTRIBUTING-EXPERIMENTS.md](/docs/CONTRIBUTING-EXPERIMENTS.md) — how to plan, name, run, and document
  a reproducible experiment.
- [data/readme.md](/data/readme.md) — description of the datasets and reference files available.
- [dfki-nlp.github.io/kibad-llm](https://dfki-nlp.github.io/kibad-llm/) — the rendered documentation site with
  all of the above, plus the auto-generated code reference.
