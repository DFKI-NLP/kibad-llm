# kibad llm documentation!

## Description

A short description of the project.

## Commands

### Generating the docs

Use [mkdocs](http://www.mkdocs.org/) structure to update the documentation.

Build locally with:

```
mkdocs build
```

Serve locally with:

```
uv run mkdocs serve -f docs/mkdocs.yml
```

Add any missing python files with:

```
uv run -m kibad_llm.utils.build_docs
```

## Tools

- [eval-dashboard](eval-dashboard.html): view and compare evaluation results
