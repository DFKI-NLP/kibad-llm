## Documentation

- All python files need to be documented at the file level.
- All python classes, functions, and methods are required to carry a docstring.
- All docstrings must be fully markdown compatible in the dialect [CommonMark](https://commonmark.org/). (CommonMark is required for use with the static docs provided by ProperDocs) [CommonMark spec](https://spec.commonmark.org/)
    - All markdown files must also be compatible with the GitHub Flavored Markdown. (Since GFM is a superset of CommonMark, this should be a given) [GitHub Flavored Markdown spec](https://github.github.com/gfm/)
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
- Use `Functions:`/`Methods:` for module functions / class methods. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-functions)
- Use `Keyword Args:` for keyword arguments. (Technically equivalent terms: Keyword Args, Keyword Arguments, Other Args, Other Arguments, Other Params, Other, Parameters) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-other-parameters)
- Use `Modules:` in `__init__.py` for modules of a package. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-modules)
- Use `Raises:` for any errors that may be raised. (Technically equivalent terms: Exceptions) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-raises)
- Use `Returns:` for return values [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-returns), or `Yields:` if they're yielded. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-yields)
- Use `Warns:` for any warnings that may be logged. (Technically equivalent terms: Warnings) [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-warns)
- Use `Warning:` (singular is important here!) to warn about something. [ref](https://mkdocstrings.github.io/griffe/reference/docstrings/#google-section-warns)

Beyond that, make sure you mention `Args:` and `Returns:`/`Yields:` before other keywords like `Warns:` or `Examples`, unless those other keywords are much more important.

## Project quality

To ensure basic quality automatically, the CI/CD pipeline with `prek` must pass without errors. You can run it locally: `uv run --group cicd prek run -a`

Additionally, code should have tests. The tests must pass for a PR to be merged. Slow tests must be marked as such and be tested separately.

The CI/CD pipeline doesn't run slow tests, but if your PR adds slow tests, they have to pass too.

## General

- If you need to take notes, do so in NOTES.md. Do not ever commit that file.
