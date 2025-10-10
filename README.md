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

To [add packages as dependencies](https://docs.astral.sh/uv/concepts/projects/dependencies/), use the `uv add` command.

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

### Upgrading dependencies

You can upgrade either one or all packages.

```bash
# upgrade all packages
uv lock --upgrade
# upgrade one package
uv lock --upgrade-package <package>
# upgrade one package to a specific version
uv lock --upgrade-package <package>==<version>
```

### Pegasus - DFKI Cluster

For running your code on Pegasus, you have three options.

#### One package

If all you need is one package, for example when using `vllm serve`, it is recommended to use the `-w your-package` option with a cache on netscratch.

```bash
# first create a cache directory on netscratch
mkdir -p /netscratch/$USER/cache/uv
# run the command with the package and cache
srun --partition=RTXA6000-SLT \
     --job-name=vllm_serve \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --time=1-00:00:00 \
     uv run -w vllm --cache-dir /netscratch/$USER/cache/uv \
            vllm serve "openai/gpt-oss-20b" \
                       --download-dir=/ds/models/llms/cache \
                       --port=18000
```

Alternatively, the cache directory can be set as an environment variable:

```bash
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"
```

#### Set `UV_PROJECT_ENVIRONMENT`

Set up the directory once:

```bash
mkdir -p /netscratch/$USER/cache/uv
mkdir -p /netscratch/$USER/cache/uv-venvs
```

Then set the environment variables for every new shell session:

```bash
export UV_CACHE_DIR="/netscratch/$USER/cache/uv"
export UV_PROJECT_ENVIRONMENT="/netscratch/$USER/cache/uv-venvs/kibad-llm"
```

Using this setup, you run your scripts like you would do locally, except they're prefixed by srun.

```bash
srun --partition=RTXA6000-SLT \
     --job-name=vllm_serve \
     --nodes=1 \
     --ntasks=1 \
     --cpus-per-task=6 \
     --gpus-per-task=1 \
     --mem-per-cpu=4G \
     --time=1-00:00:00 \
     uv run -m your.file.here
```

For more info on the project environment path, please refer to the [docs](https://docs.astral.sh/uv/concepts/projects/config/#project-environment-path).

#### Symlink .venv

First follow the steps outlined in the above section [Set `UV_PROJECT_ENVIRONMENT`](#set-uv_project_environment). <br>
Then run `uv sync` to ensure that all directories are created properly.
Lastly, create both symlinks.

```bash
# link the .venv
ln -s /netscratch/$USER/cache/uv-venvs/kibad-llm ./.venv
# link the cache
ln -s /netscratch/$USER/cache/uv ~/.cache/uv
```

Now you do not need to add the environment variables each time you start up a new shell session. <br>
Running your scripts works the same way as described in the above section [Set `UV_PROJECT_ENVIRONMENT`](#set-uv_project_environment).

### uv known issues

These known issues have their own uv specific fixes. The relevant documentation is linked.

- [Build isolation](https://docs.astral.sh/uv/concepts/projects/config/#build-isolation) - Can lead to runtime errors
- [Conflicting dependencies](https://docs.astral.sh/uv/concepts/projects/config/#conflicting-dependencies)
