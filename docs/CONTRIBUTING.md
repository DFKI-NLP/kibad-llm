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
- [Experiments](#experiments)
- [Documentation](#documentation)
    - [Documentation sources](#documentation-sources)
    - [Adding or changing pages](#adding-or-changing-pages)
    - [Links and redirects](#links-and-redirects)
    - [Building and hosting locally](#building-and-hosting-locally)
- [Local checks and CI commands](#local-checks-and-ci-commands)
    - [Troubleshooting](#troubleshooting)
- [Submodules](#submodules)
    - [Submodule data changing flow](#submodule-data-changing-flow)
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
│   ├── results/                <- Git submodule of Checked-in experiment artefacts and derived result bundles that are meant to live
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
│                                  are kept under `data/results/` instead.
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
│                                  versioned directories such as `data/results/` and `data/processed/`.
├── .pre-commit-config.yaml     <- `prek`/pre-commit hook configuration used locally and in CI.
├── justfile                    <- Config file for `just` command runner
├── LICENSE                     <- AGPL-v3 license text for the project.
├── lychee.toml                 <- Documentation link validation configuration.
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
└── uv.lock                     <- Locked dependency set managed by `uv`. Do not touch!
```

## Setup

Install the project with development dependencies:

```bash
uv sync --group cicd
```

Optionally install [`just`](https://github.com/casey/just) for less verbose dev commands.

```
uv tool install rust-just
```

Run `just -l` to see what commands are available.

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
- `experiment/description-here` for experiments (see [CONTRIBUTING-EXPERIMENTS.md](CONTRIBUTING-EXPERIMENTS.md))

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

The source-code guidelines live in [CONTRIBUTING-CODE.md](CONTRIBUTING-CODE.md).

They cover general implementation principles, test layout, source-code documentation standards, fixture regeneration, and dependency changes.

## Experiments

The experiment guidelines live in [CONTRIBUTING-EXPERIMENTS.md](CONTRIBUTING-EXPERIMENTS.md).

They cover how to plan, configure, run, track, and document reproducible experiments for this project.

## Documentation

This project uses [ProperDocs](https://properdocs.org/) for the documentation website, which is hosted on [GitHub Pages](https://dfki-nlp.github.io/kibad-llm/).

Documentation changes should be part of the same PR as the code or workflow changes they describe. For source-code docstring and API reference rules, see [CONTRIBUTING-CODE.md](CONTRIBUTING-CODE.md#documentation).

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

All links outside the `docs` directory are supposed to work on GitHub first:

- Make sure that links that point to files or directories of the repo start with a `/`, e.g. `/docs/CONTRIBUTING-CODE.md` or `/scripts/docs_hooks.py`.

All links inside the `docs` directory are supposed to work in the docs first:

- Make sure that links that point to files or directories _within_ the `docs` do _not_ start with a `/` and are absolute paths to the `/docs/` directory as root, e.g. `reference/kibad_llm/index.md` or `USAGE.md`.<br>
- Make sure that links that point to files or directories _within_ the repo, but _outside_ the `/docs/` are absolute to the repo root and start with a `/`, e.g. `/properdocs.yml`.

All links that live inside the `/docs/` directory and that start with `/` are altered by the [`docs_hooks`](/scripts/docs_hooks.py) script.

Some files live outside the `/docs/` directory, but are hooked into the `/docs/` by use of a linking file like [`/docs/data-readme.md`](https://github.com/DFKI-NLP/kibad-llm/blob/main/docs/data-readme.md).
Those files need to have a regex to fix their links in [`/scripts/docs_hooks.py`](/scripts/docs_hooks.py). Those regexes are built like so:

```
                    Path to source file in repo.
                    |                             Path to destination in the docs.
                    |                             |               Keyword for links that point into the docs website.
                    V                             V               V
(re.compile(r'href="/data/readme\.md(#[^"]*)?'), "data-readme/", "local"),
```

If a public documentation URL changes, add a redirect in `properdocs.yml` so existing links keep working. (This is currently not implemented. Requires the package `mkdocs-redirects`.)

All links in the docs end up being checked by [lychee](https://github.com/lycheeverse/lychee). If any link is broken, CI will fail and block the PR until you fix the link.

You can run the lychee test locally through the normal prek run `uv run --group cicd prek run -a`

### Building and hosting locally

You can build the documentation locally with:

```bash
uv run --group cicd properdocs build -f properdocs.yml
```

You can build and serve the documentation locally with:

```bash
uv run --group cicd properdocs serve -w .
# or
just prop
```

## Local checks and CI commands

To run code quality checks, static type checking and link validation of the docs, call:

```bash
uv run prek run -a
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd prek run -a
# or
just prek
```

This runs all configured [prek](https://prek.j178.dev/) hooks (see [pre-commit-config.yaml](/.pre-commit-config.yaml)) on all files. Some hooks may fix issues automatically, others will report issues that need to be fixed manually.

To run all Python tests with `pytest`:

```bash
uv run pytest
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd pytest
# or
just pytest
```

To run the eval-dashboard JavaScript logic tests:

```bash
node --test tests/unit/eval_dashboard/js/*.test.mjs
# or
just node-test
```

This requires a working Node.js installation. The dashboard runtime modules in `docs/eval-dashboard/assets/js/` are treated as ES modules via the colocated `package.json` file.

To run link checking on the docs:

```bash
uv run --group cicd properdocs build
lychee --config lychee.toml --root-dir ./site "site/**/*.html"
# or in just one line
just lychee
```

This requires a working lychee installation.

The following commands run on GitHub CI (see [code_quality_and_tests.yml](/.github/workflows/code_quality_and_tests.yml)), but can also be run locally:

Use this exact command set before claiming local CI readiness or `CONTRIBUTING.md` test compliance. Running only the checks for the files you touched is often fine while iterating, but do not present that as a full CI-equivalent run.

```bash
uv run --group cicd prek run -a
# the '-m "not slow"' bit is residue, to be cleaned up by a future polishing pr
uv run --group cicd pytest -m "not slow"
node --test tests/unit/eval_dashboard/js/*.test.mjs
uv run --group cicd properdocs build
lychee --config lychee.toml --root-dir ./site "site/**/*.html"
# or run all of the above with just one line
just pr
```

For test design, layout, and fixture regeneration guidance, see [CONTRIBUTING-CODE.md](CONTRIBUTING-CODE.md).

### Troubleshooting

**GitHub rate-limiting lychee:**<br>
The link checking done by lychee may be erroring due to rate-limits put in place by GitHub.<br>
Re-running the command a little later tends to work fine, but is a band-aid fix.<br>
To avoid the GitHub rate-limits altogether:

1. Go to the GitHub [settings](https://github.com/settings/personal-access-tokens) and click `Generate new token`
1. Give it a name and add the permission `Interaction limits` (read-only is enough)
1. Add the token as `GITHUB_TOKEN=...` to your .env

**No lychee with old glibc:**<br>

If your c standard library (e.g. glibc) is too old, you can't run lychee locally. Therefore you need to tell prek to skip the lychee check:

```
SKIP=lychee uv run prek run -a
```

## Submodules

> [!IMPORTANT]
> This repo uses submodules to reduce its footprint. The history, however, still
> carries a lot of removed files, so a plain `git clone` downloads all of them.
> To avoid that, pick a lightweight clone strategy — see the two snippets below.

This repo has a single submodule, `data/results`, which points at the [`kibad-llm-results`](https://github.com/DFKI-NLP/kibad-llm-results) repository. Its tracked branch is recorded as `branch = main` in the `.gitmodules` file, so the `--remote` commands below follow the `main` branch of `kibad-llm-results`.

**`--filter=blob:none` — recommended for development.** A blobless clone keeps the
full commit history and directory tree, but fetches file contents lazily on
demand instead of all at once. History tools (`git log`, `git blame`,
`git bisect`) work normally, and you never download the removed result files
unless you explicitly inspect their old contents.

```bash
git clone --filter=blob:none git@github.com:DFKI-NLP/kibad-llm.git
```

**`--depth 1` — lightest, for consuming only.** A shallow clone fetches just the
latest commit, so it is the fastest and smallest option. It has no history
(`git log`/`blame`/`bisect` cannot reach back) and only the default branch. Use
it when you just want to build or run the latest state, not develop against it.

```bash
git clone --depth 1 git@github.com:DFKI-NLP/kibad-llm.git
```

- Normal cloning ignores submodules: A normal `git clone git@github.com:DFKI-NLP/kibad-llm.git` does not clone any submodules and is hence much faster. (Combine with `--filter=blob:none` or `--depth 1` from above as needed.)

- To clone with submodules run: `git clone -j8 --recurse-submodules git@github.com:DFKI-NLP/kibad-llm.git` with `-j` specifying the number of submodules fetched simultaneously.

- To update submodules, or clone submodules in a repo that was cloned without the submodules `git submodule update --init --recursive`

- You can also do this for one specific submodule by appending `-- <path to submodule>`

- The `kibad-llm` repo stores the exact commit to check out for each submodule.

    - If you want to clone the `kibad-llm` repo with all submodule repos with the latest commit instead of the stored one, use `git clone -j8 --recurse-submodules --remote-submodules git@github.com:DFKI-NLP/kibad-llm.git`
    - If you want to update/ clone submodules with the latest commit instead of the stored one, use `git submodule update --init --recursive --remote`

### Submodule data changing flow

1. enter the submodule and check out a branch to work on: `cd data/results && git switch -c <branch>`. A fresh clone leaves the submodule in detached `HEAD` at the stored commit, so this step is required before you can commit.
1. change the files in the submodule, commit them there, and push the branch to `kibad-llm-results` (`git push -u origin <branch>`) so the commit is reachable for others and CI.
1. back in `kibad-llm`, stage and commit the updated submodule pointer and push, so the superproject records your new submodule commit.

## Misc

If you need to take notes, do so in NOTES.md.
