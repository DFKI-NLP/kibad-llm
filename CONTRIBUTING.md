# Contribution guidelines

Thank you for your interest in contributing to kibad-llm.

The following guidelines ensure consistency across the project, so please read them thoroughly.

## Table of contents

- [Setup](#setup)
- [Contribution requirements](#contribution-requirements)
    - [PR description](#pr-description)
    - [CI/CD](#cicd)
- [Testing and code quality checks](#testing-and-code-quality-checks)
- [Documentation](#documentation)
    - [Guidelines](#guidelines)
    - [Google-style docstring guidelines](#google-style-docstring-guidelines)
    - [Hosting locally](#hosting-locally)
- [Changing dependencies](#changing-dependencies)
    - [Adding dependencies](#adding-dependencies)
    - [Updating dependencies](#updating-dependencies)
    - [uv known issues](#uv-known-issues)
- [Misc](#misc)

## Setup

Install the project with development dependencies:

```bash
uv sync --group cicd
```

## Contribution requirements

Pushing to main is prohibited. If you want to contribute code, open a pull request against main.

All contributions need to be documented, both in the [PR description](#pr-description), as well as in the repo's [Documentation](#documentation).

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

Some tests require fixtures, which may need to be refreshed if anything about them changed.
Beyond that, tests that require LLM interaction can opt into `llm_chat_replay`, which uses a fixture to simulate the LLM.

To refresh the normal expected test fixtures:

```sh
WRITE_FIXTURE_DATA=1 pytest tests/integration/test_extractors.py tests/integration/test_predict.py
```

Alternatively, also refresh LLM chat replay fixtures:

```sh
WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 pytest tests/integration/test_extractors.py tests/integration/test_predict.py
```
Note: Adjusting the LLM replay fixtures usually results in different output and, thus, requires to regenerate the normal fixture data via `WRITE_FIXTURE_DATA=1`.

If you add a new test that requires LLM interaction, you can require the test to have a working deployment, but it is encouraged to use `llm_chat_replay` instead.

## Documentation

This project uses [ProperDocs](https://properdocs.org/) for documentation, which is hosted on [GitHub Pages](https://dfki-nlp.github.io/kibad-llm/).

### Guidelines

- All python files need to be documented at the file level.
- All python classes, functions, and methods are required to carry a docstring.
- All docstrings must be fully markdown compatible in the dialect [CommonMark](https://commonmark.org/). (CommonMark is required for use with the static docs provided by ProperDocs) [CommonMark spec](https://spec.commonmark.org/)
    - Do not use Sphinx/reST syntax, but markdown only.
- We use Google-style docstrings. Please refer to the next subsection, or [mkdocstrings Google-style](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-style) to familiarize yourself with them.
- Docstrings are generated using [mkdocstrings-python](https://mkdocstrings.github.io/python/), which uses the [griffe](https://mkdocstrings.github.io/griffe/) library. Please refer to the [Griffe parsing rules](https://mkdocstrings.github.io/griffe/reference/docstrings/) for more info on what is possible.

### Google-style docstring guidelines

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

### Hosting locally

You can build and serve the documentation locally with:

```bash
uv run --group cicd properdocs serve -w .
```

## Changing dependencies

Any and all dependency change must be explained in the respective PR.

### Adding dependencies

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

### Updating dependencies

You can update either one or all packages.

```bash
# update all packages
uv lock --upgrade
# update one package
uv lock --upgrade-package <package>
# update one package to a specific version
uv lock --upgrade-package <package>==<version>
```

### uv known issues

These known issues have their own uv specific fixes. The relevant documentation is linked.

- [Build isolation](https://docs.astral.sh/uv/concepts/projects/config/#build-isolation) - Can lead to runtime errors
- [Conflicting dependencies](https://docs.astral.sh/uv/concepts/projects/config/#conflicting-dependencies)

## Misc

If you need to take notes, do so in NOTES.md.
