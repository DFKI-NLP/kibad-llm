# Welcome

## Description

A short description of the project.

## Table of Contents

- [General project overview](root-readme)
- [LLM usage instructions](models-readme)
- [Faktencheck database instructions](podman-readme)

## Commands

### Generating the docs

Use [mkdocs](http://www.mkdocs.org/) structure to update the documentation.

Build locally with:

```
mkdocs build
```

Serve locally with:

```
uv run mkdocs serve
```

Add any missing python files with:

```
uv run -m kibad_llm.utils.build_docs
```

## Tools

- [eval-dashboard](eval-dashboard.html): view and compare evaluation results
