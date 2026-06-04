# Coding guidelines

## Table of contents

- [General principles](#general-principles)
- [Test design and layout](#test-design-and-layout)
    - [Unit tests](#unit-tests)
    - [Integration tests](#integration-tests)
    - [JavaScript logic tests](#javascript-logic-tests)
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

## General principles

- Do not hide unexpected behaviour or data mismatches. Handle the cases covered by the relevant code contract, but if inputs or state violate that contract, fail early and communicate that clearly, for example by raising an appropriate exception.
- Do not hesitate to refactor code that is related to the feature or fix you are working on. Reducing duplication and clarifying responsibilities is encouraged, but every refactor should provide a concrete benefit and stay scoped to the current change.
- Tests and code quality checks must pass before committing code or merging PRs. To ensure this, you can run them locally before pushing your code. For more info, check section [Local checks and CI commands](/CONTRIBUTING.md#local-checks-and-ci-commands).

## Test design and layout

Every code change should come with tests that match its scope.

Use the commands in [Local checks and CI commands](/CONTRIBUTING.md#local-checks-and-ci-commands) to run the relevant unit, integration, and JavaScript logic tests locally.

### Unit tests

- Put unit tests under `tests/unit/`.
- Mirror the file and folder structure from `src/` as closely as possible.
- Use unit tests for the usual focused checks of individual modules, functions, classes, and helpers.

### Integration tests

- Put integration tests under `tests/integration/`.
- Mirror the relevant file and folder structure from `configs/` as closely as practical.
- Prefer config-file-based tests that exercise the actual Hydra configuration used by the project.

### JavaScript logic tests

- Put browser-free eval-dashboard JavaScript logic tests under `tests/unit/eval_dashboard/js/`.
- If you change files under `docs/eval-dashboard/assets/js/` or `tests/unit/eval_dashboard/js/`, run the relevant eval-dashboard JavaScript logic tests locally.

### Fixture regeneration

Some tests require fixtures, which may need to be refreshed if anything about them changed. Beyond that, tests that require LLM interaction can opt into `llm_chat_replay`, which uses a fixture to simulate the LLM.

To refresh the normal expected test fixtures:

```sh
WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py tests/integration/test_predict.py
```

To also refresh LLM chat replay fixtures, **which requires a running vLLM backend** ([vLLM instructions](/models/README.md)):

```sh
# Regenerate only the fixture for the test you changed. Example: the chunking extractor:
WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 uv run --group cicd pytest tests/integration/test_extractors.py::test_extractor[chunking]

# Never regenerate all fixtures with these flags enabled:
# WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 uv run --group cicd pytest

# It is mandatory to check for unused fixtures in "tests/fixtures/llm_chat" after regeneration:
uv run --group cicd python tests/fixtures/map_llm_chat_usage.py
```

Never run the full test suite with `WRITE_FIXTURE_DATA=1` or `WRITE_LLM_CHAT_FIXTURE_DATA=1`. Regenerate only the fixtures for the tests you intentionally changed.

> [!NOTE]
> Adjusting the LLM replay fixtures usually results in different output and, thus, requires regenerating the normal fixture data via `WRITE_FIXTURE_DATA=1`.

> [!NOTE]
> If your tests need to call an LLM, mark them as `"slow"`, and test them separately. `"slow"` tests are not run by CI. However, it is encouraged to use `llm_chat_replay` instead.

## Documentation

This project uses [ProperDocs](https://properdocs.org/) for documentation, which is hosted on [GitHub Pages](https://dfki-nlp.github.io/kibad-llm/).

### Guidelines

- All source code files need to be documented at the file level.
- All classes, functions, and methods are required to carry a docstring.
- All docstrings must be fully markdown compatible in the dialect [CommonMark](https://commonmark.org/). (CommonMark is required for use with the static docs provided by ProperDocs) [CommonMark spec](https://spec.commonmark.org/)
    - Do not use Sphinx/reST syntax, but markdown only.
- We use Google-style docstrings. Please refer to the next subsection, or [mkdocstrings Google-style](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-style) to familiarize yourself with them.
- API documentation is generated from docstrings using [mkdocstrings-python](https://mkdocstrings.github.io/python/), which uses the [griffe](https://mkdocstrings.github.io/griffe/) library to parse Python source code and docstrings. Please refer to the [Griffe parsing rules](https://mkdocstrings.github.io/griffe/reference/docstrings/) for more info on what is possible.

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

### Linking

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
