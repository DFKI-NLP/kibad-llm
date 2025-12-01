# kibad llm

<a target="_blank" href="https://cookiecutter-data-science.drivendata.org/">
    <img src="https://img.shields.io/badge/CCDS-Project%20template-328F97?logo=cookiecutter" />
</a>

A short description of the project.

## Quickstart

### Setup

This project requires [uv](https://docs.astral.sh/uv/). If it is not already installed, please see the [installation guide](https://docs.astral.sh/uv/getting-started/installation/).

```bash
# clone project
git clone https://github.com/DFKI-NLP/kibad-llm
cd kibad-llm

# create a Python environment and install dependencies
uv sync

# (optional) copy the .env.example file to .env and adjust environment variables as needed
cp .env.example .env
```

## Usage

IMPORTANT:

All commands below assume that you are in the root directory of this project (where this `README.md` is located).

Also, if you're new to `uv`:

In places where you used to use `python`, with `uv` you tend to write `uv run` instead. <br>
What used to be `source .venv/bin/activate` and then `python your-script.py first-arg second-arg` now is reduced to `uv run your-script.py first-arg second-arg`.

### PDF Download Based on Zotero Groups

It is possible to download papers using the open access url from Semantic Scholar.

#### Prerequisites

An export of a Zotero group as CSV file, see [data/external/zotero](data/external/zotero) for the "Faktencheck Artenvielfalt" groups. Information how to export a Zotero group can be found in the [Zotero documentation](https://www.zotero.org/support/kb/exporting).

#### Downloading Papers

The script `zotero_download` uses a CSV file with an exported Zotero
group. It can search the open-access url using the DOI of the paper, the title
or a direct url found in the CSV. It downloads the papers and stores them in a
local directory.

For additional information (including default parameters), call:

```bash
uv run -m kibad_llm.data_integration.zotero_download --help
```

To start the download of open-access papers with default parameters, call:

```bash
uv run -m kibad_llm.data_integration.zotero_download
```

### Faktencheck Postgres to Json Conversion

#### Prerequisites

The following environment variables need to be set in a `.env` file in the root directory:

```
# docker-compose credentials for faktencheck database
DB_USER=<username-here>
DB_PASSWORD=<password-here>
```

Then, run the faktencheck database with podman (see [podman/faktencheck-db/README.md](./podman/faktencheck-db/README.md) for instructions).

#### DB conversion

Run the following command to convert the faktencheck database to json files:

```bash
uv run -m kibad_llm.data_integration.db_converter
```

This will create a `data/interim/faktencheck-db` directory with json files.

Call `uv run -m kibad_llm.data_integration.db_converter --help` for more options.

#### Syncing Nextcloud PDFs with the cluster storage

Run the following command to synch the Nextcloud folder at
https://cloud.dfki.de/owncloud/index.php/s/dPc2BSDDEAT4R2W?path=%2FPDFs%20Literaturdatenbank with the PDF directory
on the cluster at /ds/text/kiba-d/zotero_literaturdatenbank/ .

```bash
uv run -m kibad_llm.data_integration.synch_nextcloud_with_cluster
```

### Information Extraction from PDFs

#### Prerequisite: LLM Hosting

Follow the instructions [here for a quickstart](./models/README.md#quickstart), [here for an all-in-one script](./models/README.md#all-in-one-run-script) or [here for general instructions on uv and the cluster](./models/README.md#the-two-ways-to-use-uv-on-pegasus).

#### Inference

The information extraction pipeline can be run with:

```bash
uv run -m kibad_llm.predict pdf_directory=path/to/pdf/files
```

This will process all PDF files in `pdf_directory` and save the result in a JSON line file.

See [configs/predict](./configs/predict.yaml) for further information and options.

IMPORTANT: Relevant inference setups should be defined in their own `experiment` config. This allows to easily reproduce results later on by adding `experiment=<experiment_config>` to the command line call. For example, to run the experiment with two schemata ([configs/experiment/two_schemata.yaml](./configs/experiment/two_schemata.yaml)), use:

```bash
uv run -m kibad_llm.predict pdf_directory=path/to/pdf/files \
experiment=two_schemata
```

See [configs/experiment](./configs/experiment) for available experiment configs.

#### Evaluation

To evaluate the information extraction results against gold reference data, run:

```bash
uv run -m kibad_llm.evaluate \
dataset.predictions.file=path/to/predictions.jsonl
```

Per default, this uses `dataset=faktencheck_predictions_with_references` with `data/interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl` as reference data and calculates micro averaged precision, recall and F1-score for all fields in the Faktencheck database (i.e., `metric=f1_micro`, see [configs/metric/f1_micro.yaml](./configs/metric/f1_micro.yaml) for details). See [configs/metric](./configs/metric) for other available metrics.

To evaluate against a different dataset, e.g. organism trends, set `dataset=organism_trends_predictions_with_references`. See [configs/dataset](./configs/dataset) for available datasets.

See [configs/evaluate.yaml](./configs/evaluate.yaml) for further information and options.

Note: The `confusion_matrix` metric calculates the confusion matrix just for a single field, which needs to be specified (`metric.field=<field>`). To evaluate multiple fields at once, use multirun below.

#### Multirun

Hydra multirun can be used with both inference and evaluation to systematically explore multiple configurations in one go. It is enabled by passing comma-separated values to one or more parameters and adding `--multirun` (or `-m`) to the command line. Hydra will then execute one run for each resulting parameter combination (see the [Hydra multirun docs](https://hydra.cc/docs/tutorials/basic/running_your_app/multi-run/)).

For example, to compare the default guided decoding setup (`extractor=simple_with_schema`) with an unguided setup (`extractor=simple`), you can run:

```bash
uv run -m kibad_llm.predict \
  pdf_directory=path/to/pdf/files \
  extractor=simple_with_schema,simple \
  --multirun
```

Each multirun produces a `job_return_value.json` (a nested dictionary) and a `job_return_value.md` file with the combined output of all runs (e.g., output paths for inference or metric scores for evaluation). The top-level keys in the JSON / the `job_id` column in the Markdown summarize only those overrides that differ between runs.

For inference, complex setups are best managed via dedicated `experiment` configs; otherwise, Hydra will generate all combinations of the provided overrides, which may not be intended.

For evaluation, you can additionally request an aggregated result over all runs (e.g., mean and standard deviation across multiple non-deterministic runs or different seeds). To do so, add the `hydra.callbacks.save_job_return.integrate_multirun_result=true` override:

```bash
uv run -m kibad_llm.evaluate \
  dataset.predictions.file=path/to/A/predictions.jsonl,path/to/B/predictions.jsonl,path/to/C/predictions.jsonl \
  hydra.callbacks.save_job_return.integrate_multirun_result=true \
  --multirun
```

This will create `job_return_value.aggregated.json` and `job_return_value.aggregated.md` alongside the not aggregated outputs, summarizing the metrics across all runs in the multirun.

See [configs/hydra/default.yaml](./configs/hydra/default.yaml) for further configuration options and details on the Hydra callback to create the combined output (`save_job_return`).

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
├── podman
│   └── faktencheck-db <- Instructions and commands for using the faktencheck database
│
├── pyproject.toml     <- Project configuration file with package metadata for
│                         kibad_llm and configuration for tools like black
│
├── uv.lock            <- Do not touch. Managed by uv.
│                         Project state file.
│
├── references         <- Data dictionaries, manuals, and all other explanatory materials.
│
├── reports            <- Generated analysis as HTML, PDF, LaTeX, etc.
│   └── figures        <- Generated graphics and figures to be used in reporting
│
├── requirements.txt   <- The requirements file for reproducing the analysis environment, e.g.
│                         generated with `pip freeze > requirements.txt`
│
├── run_with_llm.sh    <- An all-in-one script for hosting vLLM and running uv against it
│
├── setup.cfg          <- Configuration file for flake8
│
└── kibad_llm          <- Source code for use in this project.
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

### Optional setup

Install the project with development dependencies:

```bash
uv sync --group cicd
```

### Testing and code quality checks

To run code quality checks and static type checking, call:

```bash
uv run pre-commit run -a
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd pre-commit run -a
```

This runs all configured [pre-commit](https://pre-commit.com/) hooks (see [pre-commit-config.yaml](.pre-commit-config.yaml)) on all files. Some hooks may fix issues automatically, others will report issues that need to be fixed manually.

To run all tests, call:

```bash
uv run pytest
# if you have not run 'uv sync --group cicd' previously, use instead
uv run --group cicd pytest
```

The following commands run on GitHub CI (see [tests.yml](.github/workflows/code_quality_and_tests.yml)), but can also be run locally:

```bash
uv run --group cicd pre-commit run -a
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
