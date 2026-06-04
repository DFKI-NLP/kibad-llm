# Contribution guidelines

Thank you for your interest in contributing to kibad-llm.

The following guidelines ensure consistency across the project, so please read them thoroughly.

## Table of contents

- [Project organization](#project-organization)
- [Setup](#setup)
- [Contribution requirements](#contribution-requirements)
    - [PR description](#pr-description)
    - [CI/CD](#cicd)
- [Source code](#source-code)
- [Documentation](#documentation)
    - [Documentation sources](#documentation-sources)
    - [Adding or changing pages](#adding-or-changing-pages)
    - [Links and redirects](#links-and-redirects)
    - [Building and hosting locally](#building-and-hosting-locally)
- [Local checks and CI commands](#local-checks-and-ci-commands)
- [Misc](#misc)

## Project Organization

High-level overview of contributor-relevant paths (local caches and other generated dot-directories are omitted):

```text
├── .github/                    <- GitHub workflows and repository automation.
├── configs/                    <- Hydra configuration tree for prediction, evaluation, datasets, metrics, paths,
│   │                              PDF reading, and experiments.
│   ├── dataset/                <- Dataset configs for references and prediction inputs.
│   ├── experiment/             <- Reproducible experiment presets for `predict` and `evaluate`.
│   ├── extractor/              <- Extractor composition, prompt, schema, LLM, and request-parameter configs.
│   ├── hydra/                  <- Hydra defaults and logging/callback configuration.
│   ├── metric/                 <- Evaluation metric configs.
│   ├── paths/                  <- Centralized input/output path defaults for runs.
│   ├── pdf_reader/             <- PDF-to-markdown reader configs.
│   ├── evaluate.yaml           <- Top-level Hydra config for evaluation runs: selects paths, datasets, metrics,
│   │                              optional experiment presets, and multi-run settings for evaluating prediction
│   │                              outputs against references.
│   └── predict.yaml            <- Top-level Hydra config for prediction runs: selects paths, PDF reader,
│                                  extractor, optional experiment presets, and runtime/output settings for batch
│                                  PDF-to-JSONL extraction.
│
├── data/                       <- Local data area for source inputs and derived datasets.
│   ├── external/               <- Third-party inputs such as exported Zotero data.
│   ├── interim/                <- Intermediate converted data such as DB-to-JSON exports used for evaluation.
│   ├── prediction_results/     <- Checked-in experiment artefacts and derived result bundles that are meant to live
│   │                              in Git.
│   ├── processed/              <- Versioned processed datasets kept in Git when useful for reproducibility.
│   └── raw/                    <- Immutable source data dumps (not yet used).
│
├── docs/                       <- ProperDocs source files for the published documentation site.
├── logs/                       <- Local/generated Hydra run logs and experiment metadata; created when executing
│                                  prediction or evaluation pipelines. This top-level directory should never contain
│                                  committed data and may be symlinked to shared storage on the cluster.
├── models/                     <- LLM runtime documentation and config files (for example `vllm.env` and logging
│                                  config), not model weights themselves.
├── notebooks/                  <- Analysis notebooks such as multirun evaluation plotting.
├── podman/
│   └── faktencheck-db/         <- Podman/Docker Compose setup and instructions for running the local Faktencheck
│                                  PostgreSQL database dump.
├── predictions/                <- Local/generated prediction JSONL outputs grouped by experiment/run; created when
│                                  executing prediction pipelines. This top-level directory should never contain
│                                  committed data and may be symlinked to shared storage on the cluster.
├── references/                 <- Data dictionaries, manuals, and all other explanatory materials (not yet used).
├── reports/
│   └── figures/                <- Legacy/outdated location for generated figures; current checked-in result artefacts
│                                  are kept under `data/prediction_results/` instead.
│
├── src/
│   └── kibad_llm/              <- Main Python package.
│       ├── data_integration/   <- Scripts for Zotero download, DB conversion, vocabulary extraction, and file syncing.
│       ├── dataset/            <- Dataset loaders/utilities for CSV, JSON, compressed data, and predictions.
│       ├── extractors/         <- Core extraction pipeline components, including chunking, repetition, unions, and
│       │                          aggregation helpers.
│       ├── hydra_callbacks/    <- Custom Hydra callbacks such as saving combined job return values.
│       ├── llms/               <- LLM backend abstractions for OpenAI, OpenAI-compatible vLLM, and in-process vLLM.
│       ├── metrics/            <- Metric implementations such as F1, TP/FP/FN, and confusion matrices.
│       ├── schema/             <- Schema types and helpers for structured outputs.
│       ├── utils/              <- General helper modules for datasets, logging, job returns, dictionaries, and paths.
│       ├── config.py           <- Shared project paths/constants and `.env` loading.
│       ├── evaluate.py         <- Hydra entry point for metric computation against references.
│       ├── metric.py           <- Shared metric interface/types used by evaluators.
│       ├── predict.py          <- Hydra entry point for PDF-to-structured-prediction runs.
│       └── preprocessing.py    <- PDF/content preprocessing helpers used before extraction.
│
├── scripts/                    <- Repository maintenance scripts, currently focused on building documentation.
│
├── tests/                      <- Unit, integration, and fixture-based tests.
│   ├── fixtures/               <- Static test data, replay fixtures, PDFs, schemas, and expected outputs.
│   ├── integration/            <- End-to-end style tests for extractors, prediction, and evaluation flows.
│   └── unit/                   <- Focused tests for individual modules and utilities.
│
├── .env.example                <- Example environment variables for local setup. Copy to `.env` and fill in the
│                                  values to run locally.
├── .gitignore                  <- Git ignore rules for local/generated data, logs, virtual environments, caches,
│                                  editor settings, and other machine-specific artefacts, while explicitly keeping
│                                  versioned directories such as `data/prediction_results/` and `data/processed/`.
├── .pre-commit-config.yaml     <- `prek`/pre-commit hook configuration used locally and in CI.
├── CONTRIBUTING.md             <- Contribution workflow and repository-level contribution guidelines.
├── CONTRIBUTING_CODE.md        <- Source-code, test, documentation, and dependency guidelines.
├── LICENSE                     <- AGPL-v3 license text for the project.
├── Makefile                    <- Legacy helper targets. TODO: clarify which targets are still maintained now that
│                                  the project uses `uv` instead of `poetry` in most docs.
├── properdocs.yml              <- ProperDocs site configuration and navigation.
├── pyproject.toml              <- Python package metadata, dependencies, and tool configuration.
├── README.md                   <- Short project entry point and quickstart.
├── run_in_process.sh           <- Cluster helper script for running inference/evaluation with in-process vLLM or
│                                  API-based models.
├── run_with_llm.sh             <- Cluster helper script that starts an external vLLM server and then runs `uv` code
│                                  against it.
├── run_with_llm_login_node_exec.sh <- Variant of the previous helper that keeps the `uv` side on the login node.
│                                  TODO: Since this is not used so far, should we remove it?
├── USAGE.md                    <- Detailed usage instructions for data integration, prediction, and evaluation.
└── uv.lock                     <- Locked dependency set managed by `uv`. Do not touch!
```

## Setup

Install the project with development dependencies:

```bash
uv sync --group cicd
```

## Contribution requirements

Pushing to main is prohibited. If you want to contribute code, open a pull request against main.

All contributions need to be documented, both in the [PR description](#pr-description), and in the repo's [Documentation](#documentation).

PRs must be reviewed.

Approved PRs should be squash merged to keep the tree clean.

### PR description

A PR description needs to document:

- the reason and goal of the PR.
- the changes made, and possibly why they were made.
- the issues they work towards closing.
- the PRs they depend on.
- migration instructions, if needed.
- simple testing instructions for reviewers.

### CI/CD

PRs need to pass CI/CD. This currently includes:

- all pre-commit hooks,
- all `"not slow"` Python tests, and
- the browser-free eval-dashboard JavaScript logic tests run with Node.js.

If you state in a PR, review, or commit message that a branch is "CI-ready", "passes local CI", or complies with this document's testing expectations, run the full local CI-equivalent command set from [Local checks and CI commands](#local-checks-and-ci-commands). Running only a changed-area subset of checks is useful for iteration, but is not enough for such a claim.

For more info, check section [Local checks and CI commands](#local-checks-and-ci-commands).

### Branch naming

**Prefixing** <br>
Use

- `feat/description-here` for any new features.
- `docs/description-here` for documentation work. (other branches, e.g. `feat/` are expected to document their features too.)
- `fix/description-here` for (bug)fixes.
- `hotfix/description-here` for urgent fixes.

These prefixes don't just make branch names easier to read, but also allow for colour coding in tools like [lazy git](https://github.com/jesseduffield/lazygit/blob/master/docs/Config.md#custom-branch-color).

**Alphanumeric characters** <br>
Use only alphanumeric characters (a-z, A-Z, 0–9) and hyphens. Avoid punctuation, spaces, underscores, or any non-alphanumeric character.

**No Continuous Hyphens** <br>
Do not use continuous hyphens. `feature--new-login` can be confusing and hard to read.

**No Trailing Hyphens** <br>
Do not end your branch name with a hyphen. For example, `feature-new-login-` is not a good practice.

**Descriptive** <br>
The name should be descriptive and concise, ideally reflecting the work done on the branch.

## Source Code

The source-code guidelines live in [CONTRIBUTING_CODE.md](/CONTRIBUTING_CODE.md).

They cover general implementation principles, test layout, source-code documentation standards, fixture regeneration, and dependency changes.

## Documentation

This project uses [ProperDocs](https://properdocs.org/) for the documentation website, which is hosted on [GitHub Pages](https://dfki-nlp.github.io/kibad-llm/).

Documentation changes should be part of the same PR as the code or workflow changes they describe. For source-code docstring and API reference rules, see [CONTRIBUTING_CODE.md](/CONTRIBUTING_CODE.md#documentation).

### Documentation sources

The documentation website is built from:

- Markdown pages under `docs/`.
- Snippet wrapper pages such as `docs/usage.md`, which include root-level files with `--8<--`.
- The site navigation and redirects in `properdocs.yml`.
- Generated API reference pages from `scripts/build_docs.py`.
- Link rewrites in `scripts/docs_hooks.py` for GitHub-style repository links that need different URLs on the generated website.

### Adding or changing pages

To add a normal documentation page, create a Markdown file under `docs/` and add it to the `nav` section in `properdocs.yml`.

To publish an existing root-level Markdown file, create a small wrapper under `docs/` that includes the source file with a snippet directive, then add that wrapper to `properdocs.yml`.

Keep the main navigation focused. If a topic grows into several pages, use a parent nav entry with descriptive subentries.

The API reference is generated from Python source files by `scripts/build_docs.py`; do not manually edit generated files under `docs/reference/`.

### Links and redirects

Use repository-root links such as `/CONTRIBUTING_CODE.md` when linking to root-level files from snippet-included content. If that link needs to work on the generated website, add or update the corresponding rewrite in `scripts/docs_hooks.py`.

If a public documentation URL changes, add a redirect in `properdocs.yml` so existing links keep working.

### Building and hosting locally

You can build the documentation locally with:

```bash
uv run --group cicd properdocs build -f properdocs.yml
```

You can build and serve the documentation locally with:

```bash
uv run --group cicd properdocs serve -w .
```

## Local checks and CI commands

To run code quality checks and static type checking, call:

```bash
uv run prek run -a
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd prek run -a
```

This runs all configured [prek](https://prek.j178.dev/) hooks (see [pre-commit-config.yaml](.pre-commit-config.yaml)) on all files. Some hooks may fix issues automatically, others will report issues that need to be fixed manually.

To run all Python tests with `pytest`:

```bash
uv run pytest
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd pytest
```

To run the eval-dashboard JavaScript logic tests:

```bash
node --test tests/unit/eval_dashboard/js/*.test.mjs
```

This requires a working Node.js installation. The dashboard runtime modules in `docs/eval-dashboard/assets/js/` are treated as ES modules via the colocated `package.json` file.

The following commands run on GitHub CI (see [code_quality_and_tests.yml](.github/workflows/code_quality_and_tests.yml)), but can also be run locally:

Use this exact command set before claiming local CI readiness or `CONTRIBUTING.md` test compliance. Running only the checks for the files you touched is often fine while iterating, but do not present that as a full CI-equivalent run.

```bash
uv run --group cicd prek run -a
# the '-m "not slow"' bit is residue, to be cleaned up by a future polishing pr
uv run --group cicd pytest -m "not slow"
node --test tests/unit/eval_dashboard/js/*.test.mjs
```

For test design, layout, and fixture regeneration guidance, see [CONTRIBUTING_CODE.md](/CONTRIBUTING_CODE.md).

## Misc

If you need to take notes, do so in NOTES.md.
