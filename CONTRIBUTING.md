# Contribution guidelines

Thank you for your interest in contributing to kibad-llm.

The following guidelines ensure consistency across the project, so please read them thoroughly.

## Table of contents

- [Project organization](#project-organization)
- [Setup](#setup)
- [Contribution requirements](#contribution-requirements)
    - [PR description](#pr-description)
    - [CI/CD](#cicd)
- [Coding guidelines](#coding-guidelines)
    - [General principles](#general-principles)
    - [Tests](#tests)
        - [Unit tests](#unit-tests)
        - [Integration tests](#integration-tests)
        - [Fixture regeneration](#fixture-regeneration)
    - [Documentation](#documentation)
        - [Guidelines](#guidelines)
        - [Google-style docstring guidelines](#google-style-docstring-guidelines)
        - [Linking](#linking)
        - [Hosting locally](#hosting-locally)
    - [Changing dependencies](#changing-dependencies)
        - [Adding dependencies](#adding-dependencies)
        - [Updating dependencies](#updating-dependencies)
        - [uv known issues](#uv-known-issues)
- [Testing and code quality checks](#testing-and-code-quality-checks)
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
├── CONTRIBUTING.md             <- Contribution workflow, testing, and documentation guidelines.
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

PRs need to pass CI/CD. This means that all pre-commit hooks need to pass, as well as all `"not slow"` tests. For more info, check section [Testing and code quality checks](#testing-and-code-quality-checks).

Make sure you add tests for your code. If your tests need to call an LLM, mark them as `"slow"`, and test them separately. `"slow"` tests are not run by CI.

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

## Coding guidelines

### General principles

- Do not hide unexpected behaviour or data mismatches. Handle the cases covered by the relevant code contract, but if inputs or state violate that contract, fail early and communicate that clearly, for example by raising an appropriate exception.
- Do not hesitate to refactor code that is related to the feature or fix you are working on. Reducing duplication and clarifying responsibilities is encouraged, but every refactor should provide a concrete benefit and stay scoped to the current change.
- Tests and code quality checks must pass before committing code or merging PRs. To ensure this, you can run them locally before pushing your code. For more info, check section [Testing and code quality checks](#testing-and-code-quality-checks).

### Tests

Every code change should come with tests that match its scope.

#### Unit tests

- Put unit tests under `tests/unit/`.
- Mirror the file and folder structure from `src/` as closely as possible.
- Use unit tests for the usual focused checks of individual modules, functions, classes, and helpers.

#### Integration tests

- Put integration tests under `tests/integration/`.
- Mirror the relevant file and folder structure from `configs/` as closely as practical.
- Prefer config-file-based tests that exercise the actual Hydra configuration used by the project.

#### Fixture regeneration

Some tests require fixtures, which may need to be refreshed if anything about them changed. Beyond that, tests that require LLM interaction can opt into `llm_chat_replay`, which uses a fixture to simulate the LLM.

To refresh the normal expected test fixtures:

```sh
WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py tests/integration/test_predict.py
```

To also refresh LLM chat replay fixtures, **which requires a running vLLM backend** ([vLLM instructions](./models/README.md)):

```sh
# Regenerate only the fixture for the test you changed. Example: the chunking extractor:
WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py::test_extractor[chunking]

# Never regenerate all fixtures with these flags enabled:
# WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 uv run --group cicd pytest

# It is mandatory to check for unused fixtures in "tests/fixtures/llm_chat" after regeneration:
uv run --group cicd python tests/fixtures/map_llm_chat_usage.py
```

Never run the full test suite with `WRITE_FIXTURE_DATA=1` or `WRITE_LLM_CHAT_FIXTURE_DATA=1`. Regenerate only the fixtures for the tests you intentionally changed.

Note: Adjusting the LLM replay fixtures usually results in different output and, thus, requires regenerating the normal fixture data via `WRITE_FIXTURE_DATA=1`.</br>

If you add a new test that requires LLM interaction, you can require the test to have a working vLLM backend, but it is encouraged to use `llm_chat_replay` instead.

### Documentation

This project uses [ProperDocs](https://properdocs.org/) for documentation, which is hosted on [GitHub Pages](https://dfki-nlp.github.io/kibad-llm/).

#### Guidelines

- All source code files need to be documented at the file level.
- All classes, functions, and methods are required to carry a docstring.
- All docstrings must be fully markdown compatible in the dialect [CommonMark](https://commonmark.org/). (CommonMark is required for use with the static docs provided by ProperDocs) [CommonMark spec](https://spec.commonmark.org/)
    - Do not use Sphinx/reST syntax, but markdown only.
- We use Google-style docstrings. Please refer to the next subsection, or [mkdocstrings Google-style](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-style) to familiarize yourself with them.
- API documentation is generated from docstrings using [mkdocstrings-python](https://mkdocstrings.github.io/python/), which uses the [griffe](https://mkdocstrings.github.io/griffe/) library to parse Python source code and docstrings. Please refer to the [Griffe parsing rules](https://mkdocstrings.github.io/griffe/reference/docstrings/) for more info on what is possible.

#### Google-style docstring guidelines

Consistency is key. So, whilst the Google-style allows for multiple technically equivalent terms, we want to use one of them exclusively. <br>
Therefore, please:

- Use `Args:` to denote parameters. (Technically equivalent terms: Args, Arguments, Params, Parameters) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-parameters)
- Use `Attributes:` for module/ class attributes. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-attributes)
- Use `Classes:` for module classes. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-classes)
- Use `Examples:` (plural is important here!) for one or more examples, possibly including code snippets. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-examples)
- Use `Functions:` for the functions of a module. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-functions)
- Use `Keyword Args:` for keyword arguments. (Technically equivalent terms: Keyword Args, Keyword Arguments, Other Args, Other Arguments, Other Params, Other, Parameters) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-other-parameters)
- Use `Methods:` for the methods of a class. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-functions)
- Use `Modules:` in `__init__.py` for modules of a package. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-modules)
- Use `Raises:` for any errors that may be raised explicitly with the `raises` keyword. (Technically equivalent terms: Exceptions) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-raises)
- Use `Returns:` for return values [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-returns), or `Yields:` if they're yielded. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-yields)
- Use `Warns:` for any warnings that may be logged. This means warnings displayed at runtime. (Technically equivalent terms: Warnings) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-warns)
- Use `Warning:` (singular is important here!) to warn the programmer about something when writing code. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-warns)

Beyond that, make sure you mention `Args:` and `Returns:`/`Yields:` before other keywords like `Warns:` or `Examples`.

#### Linking

You can link python objects that are in the documentation. Those links are clickable on the generated static site.

______________________________________________________________________

**Syntax for absolute links:**

example:

```
[`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor]
```

explanation:

```
[`display text of link - monospace formatting`][module.dir.file.py_obj]
```

______________________________________________________________________

**Syntax for relative links:**

close relation example:

```
[`F1MicroSingleFieldMetric`][..F1MicroSingleFieldMetric]
```

explanation:

```
[`display text of link - monospace formatting`][..py_obj]
```

This link is in a class docstring and references a class in the same file.
In `..F1MicroSingleFieldMetric` the first dot refers to the class in which the docstring is written.
The second dot refers to the parent, here being the file.
Then from within this file, refer to `F1MicroSingleFieldMetric`.

______________________________________________________________________

short close relation example:

```
[`..reset`][]
```

explanation:

```
[`display text of link and path of link - monospace formatting`][]
```

This link is in a method docstring and references a different method of the same class.
In `..reset` the first dot refers to the method in which the docstring is written.
The second dot refers to the parent, here being the class to which the method belongs.
Then from within this class, refer to the reset method.
What's special here is that the `..reset` is the display text and link path simultaneously.
This can reduce the amount of writing that's needed, but may be worse for reading.

______________________________________________________________________

broken example:

```
[`MetricWithPrepareEntryAsSet`][...base.MetricWithPrepareEntryAsSet]
```

explanation:

```
[`display text of link - monospace formatting`][...file.py_obj]
```

This link is in a class docstring and references a class in a different file.
In `...base.MetricWithPrepareEntryAsSet` the first dot refers to the class in which the docstring is written.
The second dot refers to the parent, here being the file.
The third refers to the parent, now being the directory.
Then from within this directory, base refers to a file and `MetricWithPrepareEntryAsSet` to a class within it.

This does work in theory, but the class to which this docstring belongs is automatically imported in the `__init__.py` file.
This means that the docstring is also displayed in `__init__.py`, which changes the path resolution.
From there, the first dot refers to the class, the second to the directory, and the third to the parent directory, which is the wrong location.

______________________________________________________________________

Relative links can help with readability/ saving space, but can also be a lot more complex to get perfectly functional.

#### Hosting locally

You can build and serve the documentation locally with:

```bash
uv run --group cicd properdocs serve -w .
```

### Changing dependencies

Any and all dependency change must be explained in the respective PR.

#### Adding dependencies

To [add packages as dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/), use the `uv add` command. <br>
Please make sure to add upper bounds when you can to prevent future breakage.

```bash
uv add httpx
# you can add a specific version
uv add "httpx==0.20"
# an upper or lower bound
uv add "httpx>=0.20"
# or a range
uv add "httpx>=0.20,<1.0"
```

[Changing dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/#changing-dependencies) works just like adding them. <br>
Please keep in mind that you can also add [platform-specific dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/#platform-specific-dependencies).

#### Updating dependencies

You can update either one or all packages.

```bash
# update all packages
uv lock --upgrade
# update one package
uv lock --upgrade-package <package>
# update one package to a specific version
uv lock --upgrade-package <package>==<version>
```

#### uv known issues

These known issues have their own uv specific fixes. The relevant documentation is linked.

- [Build isolation](https://docs.astral.sh/uv/concepts/projects/config/#build-isolation) - Can lead to runtime errors
- [Conflicting dependencies](https://docs.astral.sh/uv/concepts/projects/config/#conflicting-dependencies)

## Testing and code quality checks

To run code quality checks and static type checking, call:

```bash
uv run prek run -a
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd prek run -a
```

This runs all configured [prek](https://prek.j178.dev/) hooks (see [pre-commit-config.yaml](.pre-commit-config.yaml)) on all files. Some hooks may fix issues automatically, others will report issues that need to be fixed manually.

To run all tests with `pytest`:

```bash
uv run pytest
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd pytest
```

The following commands run on GitHub CI (see [code_quality_and_tests.yml](.github/workflows/code_quality_and_tests.yml)), but can also be run locally:

```bash
uv run --group cicd prek run -a
# the '-m "not slow"' bit is residue, to be cleaned up by a future polishing pr
uv run --group cicd pytest -m "not slow"
```

For test design, layout, and fixture regeneration guidance, see [Coding guidelines](#coding-guidelines).

## Misc

If you need to take notes, do so in NOTES.md.
