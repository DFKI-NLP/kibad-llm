# Contribution guidelines

Thank you for showing interest, and contributing to the kibad-llm project.

The following guidelines ensure consistency across the project, so please read them thoroughly.

## Table of contents

- [Contribution guidelines](#contribution-guidelines)
    - [Table of contents](#table-of-contents)
    - [General](#general)
    - [🔧 Project Development](#-project-development)
        - [Optional setup](#optional-setup)
        - [Testing and code quality checks](#testing-and-code-quality-checks)
        - [Adding dependencies](#adding-dependencies)
        - [Updating dependencies](#updating-dependencies)
        - [uv known issues](#uv-known-issues)
        - [Documentation](#documentation-hosting)
    - [Documentation](#documentation-general)
        - [Google-style docstring guidelines](#google-style-docstring-guidelines)

## General

- If you need to take notes, do so in NOTES.md. Do not ever commit that file.

## 🔧 Project Development

### Optional setup

Install the project with development dependencies:

```bash
uv sync --group cicd
```

### Testing and code quality checks

To run code quality checks and static type checking, call:

```bash
uv run prek run -a
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd prek run -a
```

This runs all configured [prek](https://prek.j178.dev/) hooks (see [pre-commit-config.yaml](.pre-commit-config.yaml)) on all files. Some hooks may fix issues automatically, others will report issues that need to be fixed manually.

To run all tests, call:

```bash
uv run pytest
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd pytest
```

The following commands run on GitHub CI (see [tests.yml](.github/workflows/code_quality_and_tests.yml)), but can also be run locally:

```bash
uv run --group cicd prek run -a
# run tests *not marked as slow* with coverage and typeguard checks
uv run --group cicd pytest -m "not slow"
```

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

<a id="documentation-hosting"></a>

### Documentation

This project uses [mkdocs](https://www.mkdocs.org/) for documentation, which is hosted on GitHub Pages at https://dfki-nlp.github.io/kibad-llm/.

You can build and serve the documentation locally with:

```bash
uv run --group cicd properdocs serve -w .
```

<a id="documentation-general"></a>

## Documentation

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
