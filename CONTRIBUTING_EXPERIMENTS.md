# Experiment contribution guidelines

Use this guide when you create, run, evaluate, or document reproducible experiments for `kibad-llm`.

## Table of contents

- [Setup](#setup)
- [Planning](#planning)
- [Execution](#execution)
    - [Choose a name](#choose-a-name)
    - [Prepare the experiment folder](#prepare-the-experiment-folder)
    - [Run predictions](#run-predictions)
    - [Run evaluations](#run-evaluations)
    - [Inspect results in the eval dashboard](#inspect-results-in-the-eval-dashboard)
- [Documentation](#documentation)
- [Result locations](#result-locations)

## Setup

Follow the general setup instructions in the [README.md](/README.md) and [CONTRIBUTING.md](/CONTRIBUTING.md#setup).

For prediction runs, also follow [models/README.md](/models/README.md). Cluster prediction experiments usually should use the `in_process` LLM variants and the `run_in_process.sh` helper.

If a prediction run needs API keys or model-download credentials, create `.env` from `.env.example` and set the required variables there. Do not commit secrets.

## Planning

Before starting a new experiment:

- Check the existing overview table in [data/prediction_results/readme.md](https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/readme.md). Use the latest related experiments as references for naming, command structure, folder layout, and result documentation.
- Prefer a dedicated config under `configs/experiment/` when the setup is not trivial.
- Keep predictions and evaluations scoped to the research question you want to answer.
- Decide which prediction and evaluation commands are needed before creating result artefacts.

## Execution

### Choose a name

Choose a descriptive experiment name:

```text
[issue_or_pr_id]_[descriptive_text]
```

Use the same `name` value in every `predict` and `evaluate` command that belongs to the experiment.

The name determines the experiment subfolders under:

- `logs/<name>` for run logs,
- `predictions/<name>` for generated prediction outputs, and
- `data/prediction_results/logs/<name>` and `data/prediction_results/predictions/<name>` for committed result artefacts.

### Prepare the experiment folder

Create the committed result folder:

```bash
mkdir -p data/prediction_results/logs/<name>
```

Create `data/prediction_results/logs/<name>/readme.md` with:

- a first-level heading with the experiment name, for example `# 481_faktencheck_core`,
- a short description of the goal, motivation, and hypothesis,
- a `Prediction` section when prediction commands were run,
- an `Evaluation` section when evaluation commands were run, and
- each executed command together with its printed result location.

Use result locations as printed by the command, for example:

```text
result location: logs/481_faktencheck_core/evaluate/multiruns/2026-05-26_14-21-18
```

### Run predictions

Run prediction experiments according to [models/README.md](/models/README.md), usually with `run_in_process.sh` and `in_process` LLM configs on the cluster.

Always pass the shared experiment name:

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-u "-m kibad_llm.predict \
       name=<name> \
       experiment/predict=<predict_experiment_config> \
       pdf_directory=<pdf_directory> \
       extractor/llm=<llm_config> \
       seed=42,1337,7331 \
       --multirun"
```

> [!NOTE]
> We want relieble evaluation results, so always set a random seed for prediction runs. Use multiple seeds when possible to get a better estimate of the true performance.

If the run used cluster-local `logs/` and `predictions/`, copy the relevant artefacts into `data/prediction_results` from within that directory:

```bash
# copy predictions
scp -r <username>@<host>:path/to/kibad-llm/predictions/<name> predictions/
```

```bash
# copy prediction logs
scp -r <username>@<host>:path/to/kibad-llm/logs/<name> logs/
```

### Run evaluations

Run evaluation commands locally from within `data/prediction_results` so they only use committed predictions:

```bash
cd data/prediction_results
uv run -m kibad_llm.evaluate \
name=<name> \
experiment/evaluate=<evaluate_experiment_config> \
prediction_logs=logs/<name>/predict \
--multirun
```

To evaluate selected prediction runs instead of every run under `logs/<name>/predict`, pass explicit prediction log paths:

```bash
prediction_logs=[logs/<name>/predict/multiruns/<timestamp-1>,logs/<name>/predict/multiruns/<timestamp-2>]
```

Copy local evaluation outputs to the committed result folder:

```text
cp -r logs/<name>/evaluate data/prediction_results/logs/<name>/evaluate
```

### Inspect results in the eval dashboard

Open the [eval dashboard](https://dfki-nlp.github.io/kibad-llm/eval-dashboard/) and load the new evaluation data, usually:

```text
data/prediction_results/logs/<name>/evaluate
```

Configure the dashboard so the experiment hypothesis is easy to verify or reject. Download selected figures into:

```text
data/prediction_results/logs/<name>/figures/
```

## Documentation

Every committed experiment needs a self-contained result description.

In `data/prediction_results/logs/<name>/readme.md`:

- document the motivation, setup, commands, and result locations,
- add an `Outcome` section,
- include relevant dashboard figures from `figures/`, and
- describe the outcome textually, including whether the hypothesis was supported.

Then add a row to the table in [data/prediction_results/readme.md](https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/readme.md) with:

- the log folder link,
- the date,
- the related issue or PR link, and
- short notes describing the experiment.

## Result locations

Top-level `logs/` and `predictions/` are local or cluster run locations. They should not contain committed repository data.

Committed experiment artefacts belong under:

- `data/prediction_results/logs/<name>` for logs, evaluation outputs, experiment documentation, and figures,
- `data/prediction_results/predictions/<name>` for copied prediction outputs, when prediction was part of the experiment.
