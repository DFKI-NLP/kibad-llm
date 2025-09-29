# kibad llm

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

A short description of the project.

## Quickstart

### Setup

This project requires [Poetry](https://python-poetry.org/). If it is not already installed, please see the [installation guide](https://python-poetry.org/docs/#installation).

```bash
# clone project
git clone https://github.com/DFKI-NLP/kibad-llm
cd kibad-llm

# create a Python environment and install dependencies
poetry install

# (optional) copy the .env.example file to .env and adjust environment variables as needed
cp .env.example .env
```

NOTE: If the installation gets stuck, try if disabling experimental parallel installer helps
([source](https://github.com/python-poetry/poetry/issues/3352#issuecomment-732761629)):
`poetry config experimental.new-installer false`

## Usage

## Project Organization

```
├── LICENSE            <- Open-source license if one is chosen
├── Makefile           <- Makefile with convenience commands like `make data` or `make train`
├── README.md          <- The top-level README for developers using this project.
├── data
│   ├── external       <- Data from third party sources.
│   ├── interim        <- Intermediate data that has been transformed.
│   ├── processed      <- The final, canonical data sets for modeling.
│   └── raw            <- The original, immutable data dump.
│
├── docs               <- A default mkdocs project; see www.mkdocs.org for details
│
├── models             <- Trained and serialized models, model predictions, or model summaries
│
├── notebooks          <- Jupyter notebooks. Naming convention is a number (for ordering),
│                         the creator's initials, and a short `-` delimited description, e.g.
│                         `1.0-jqp-initial-data-exploration`.
│
├── pyproject.toml     <- Project configuration file with package metadata for
│                         kibad_llm and configuration for tools like black
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── setup.cfg          <- Configuration file for flake8
│
└── kibad_llm   <- Source code for use in this project.
    │
    ├── __init__.py             <- Makes kibad_llm a Python module
    │
    ├── config.py               <- Store useful variables and configuration
    │
    ├── dataset.py              <- Scripts to download or generate data
    │
    ├── features.py             <- Code to create features for modeling
    │
    ├── modeling
    │   ├── __init__.py
    │   ├── predict.py          <- Code to run model inference with trained models
    │   └── train.py            <- Code to train models
    │
    └── plots.py                <- Code to create visualizations
```

______________________________________________________________________

## 🔧 Project Development

### Setup

Install the project with development dependencies:

```bash
poetry install --with dev
```

### Testing and code quality checks

To run code quality checks and static type checking, call:

```bash
pre-commit run -a
```

To run all tests, call:

```bash
pytest
```

The following commands run on GitHub CI (see [tests.yml](.github/workflows/code_quality_and_tests.yml)), but can also be run locally:

```bash
pre-commit run -a
# run tests *not marked as slow* with coverage and typeguard checks
pytest -m "not slow" --cov --cov-report=term-missing --typeguard-packages=kibad-llm
```

### Updating Dependencies

Call this to update individual packages:

```bash
poetry update <package>
```

Then, commit the modified lock file to persist the state.
