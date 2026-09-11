# Experiment contribution guidelines

Use this guide when you create, run, evaluate, or document reproducible experiments for `kibad-llm`.

## Table of contents

- [Setup](#setup)
- [Datasets](#datasets)
- [Planning](#planning)
- [Execution](#execution)
    - [Choose a name](#choose-a-name)
    - [Prepare the experiment folder](#prepare-the-experiment-folder)
    - [Run predictions](#run-predictions)
    - [Run evaluations](#run-evaluations)
    - [Inspect results in the eval dashboard](#inspect-results-in-the-eval-dashboard)
- [Describe and interpret results](#describe-and-interpret-results)
- [Finalize the documentation](#finalize-the-documentation)
- [Result locations](#result-locations)

## Setup

Follow the general setup instructions in the [USAGE.md](USAGE.md) and [CONTRIBUTING.md](CONTRIBUTING.md#setup).

For prediction runs, also follow [models/README.md](/models/README.md). Cluster prediction experiments usually should use the `in_process` LLM variants and the `run_in_process.sh` helper.

If a prediction run needs API keys or model-download credentials, create `.env` from `.env.example` and set the required variables there. Do not commit secrets.

## Datasets

See [data/readme.md](/data/readme.md) for a description of the various PDF datasets and ground truth reference files that are currently available, as well as their
storage locations.

## Planning

Before starting a new experiment:

- Check the existing overview table in [kibad-llm-results:/readme.md](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md). Use the latest related experiments as references for naming, command structure, folder layout, and result documentation.
- Prefer a dedicated config under `configs/experiment/` when the setup is not trivial.
- Decide which input datasets (pdf directory) and ground truth files you need
- Keep predictions and evaluations scoped to the research question you want to answer.
- Decide which prediction and evaluation commands are needed before creating result artefacts.

## Execution

### Clone the repo

Experiments belong in the [kibad-llm-results](https://github.com/DFKI-NLP/kibad-llm-results) repo.
It is recommended to clone into /data/results of the kibad-llm repo.

```bash
# from the kibad-llm repo root
git clone git@github.com:DFKI-NLP/kibad-llm-results.git ./data/results
```

### Choose a name

Choose a descriptive experiment name for your branch:

```text
experiment/[descriptive_text]
```

### Get an ID

Add your new experiment to the [kibad-llm-results:/readme.md](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md), commit, push, and create a PR.

Use the PR ID to form your experiments ID. Make sure to pad the ID to be triple digits.

```text
[pr_id]_[descriptive_text]
example:
012_reasoning_vs_no_reasoning
```

> [!IMPORTANT]
> Use the same `experiment_id` value in every `predict` and `evaluate` command that belongs to the experiment.

The experiment_id determines the experiment subfolders under:

- `logs/<experiment_id>` for run logs,
- `predictions/<experiment_id>` for generated prediction outputs, and
- `data/results/logs/<experiment_id>` and `data/results/predictions/<experiment_id>` for committed result artefacts.

### Prepare the experiment folder

Create the committed result folder:

```bash
mkdir -p data/results/logs/<experiment_id>
```

Create the experiment readme `data/results/logs/<experiment_id>/readme.md` with:

- a first-level heading with the experiment_id
- a short description of the goal, motivation, and hypothesis,
- a `Prediction` section when prediction commands were run,
- an `Evaluation` section when evaluation commands were run, and
- each executed command together with its printed result location (use repo-relative paths, if possible, to ease reproducibility).

Use result locations as printed by the command, for example:

```text
result location: logs/481_faktencheck_core/evaluate/multiruns/2026-05-26_14-21-18
```

### Step-by-step Guide

Set up the kibad-llm-results like so:

```bash
cd <path/to/kibad-llm-results>

# Get clean, up-to-date copy of main
git checkout main
git pull
# Create branch
git switch -c experiment/<your_descriptive_experiment_name>

# Add a line for your experiment to the readme.md. No need to fill in the placeholders just yet. Do that when you do have all the info.
echo '| [<experiment_id>](logs/<experiment_id>) | <yyyy-MM-dd> | https://github.com/DFKI-NLP/kibad-llm/pull/<new_pr_id> | <your_descriptive_text> |' >> readme.md

# Get an ID for your experiment
git commit -m "Add stub for experiment in readme.md"
git push
# Create PR to get your experiment_id: [pr_id]_[your_descriptive_experiment_name]. Make sure the ID is padded with 0 to triple digits.
```

- Edit `kibad-llm-results:/logs/<experiment_id>/README.md` as described [above](/docs/CONTRIBUTING-EXPERIMENTS.md#prepare-the-experiment-folder)

- Finalize your line in [kibad-llm-results:/readme.md](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md):

```bash
# Add updated readme's
cd <path/to/kibad-llm-results>
git add logs/<experiment_id>/README.md
git add readme.md
git commit -m "update readme"
git push
```

### Run predictions

Run prediction experiments according to [models/README.md](/models/README.md), usually with `run_in_process.sh` and `in_process` LLM configs on the cluster.

Always pass the shared experiment name:

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-u "-m kibad_llm.predict \
       name=<experiment_id> \
       experiment/predict=<predict_experiment_config> \
       pdf_directory=<pdf_directory> \
       extractor/llm=<llm_config> \
       seed=42,1337,7331 \
       --multirun"
```

> [!NOTE]
> We want relieble evaluation results, so always set a random seed for prediction runs. Use multiple seeds when possible to get a better estimate of the true performance.

If the run used cluster-local `logs/` and `predictions/`, copy the relevant artefacts into `data/results` from within that directory:

```bash
# copy predictions
scp -r <username>@<host>:path/to/kibad-llm/predictions/<name> predictions/
```

```bash
# copy prediction logs
scp -r <username>@<host>:path/to/kibad-llm/logs/<name> logs/
```

### Run evaluations

Run evaluation commands locally from within `data/results` so they only use committed predictions:

```bash
cd data/results
uv run -m kibad_llm.evaluate \
name=<experiment_id> \
experiment/evaluate=<evaluate_experiment_config> \
prediction_logs=logs/<experiment_id>/predict \
--multirun
```

To evaluate selected prediction runs instead of every run under `logs/<experiment_id>/predict`, pass explicit prediction log paths:

```bash
prediction_logs=[logs/<experiment_id>/predict/multiruns/<timestamp-1>,logs/<experiment_id>/predict/multiruns/<timestamp-2>]
```

Copy local evaluation outputs to the committed result folder (execute from root of kibad-llm-results if repo is cloned at `kibad-llm:/data/results`):

```text
cp -r ../../logs/<experiment_id>/evaluate logs/<name>/evaluate
```

### Inspect results in the eval dashboard

Open the [eval dashboard](https://dfki-nlp.github.io/kibad-llm/eval-dashboard-docs/) and load the new evaluation data, usually:

```text
kibad-llm-results:/logs/<experiment_id>/evaluate
# if repo is cloned at kibad-llm:/data/results:
/data/results/logs/<experiment_id>/evaluate
```

Configure the dashboard so the experiment hypothesis is easy to verify or reject. Download selected figures into:

```text
kibad-llm-results:/logs/<experiment_id>/figures/
# if repo is cloned at kibad-llm:/data/results:
/data/results/logs/<experiment_id>/figures
```

> [!TIP]
> Use subfolders in `figures/` when there are different experiment or evaluation setups that should be logically separated.

> [!IMPORTANT]
> You should include relevant dashboard figures from `figures/` (add subfolders, if appropriate), e.g. `![f1.png](figures/setup_a/f1.png)`, in the respective sections of the experiment readme.

## Describe and interpret results

As mentioned [above](#prepare-the-experiment-folder), you should have already documented the motivation, setup, commands, and result locations in the experiment readme. Now, after inspecting the results, you should also add an `Outcome` section describing the outcome of this experiment textually. This should include a result analysis, the hypothesis evaluation, but also naming any *unexpected* outcome and, finally, derived recommendations wrt. the project, e.g. "the model / feature provides the best results, so we should enable it per default for future experiments" or "this model does not outperform our current top model, but ranks second best overall and improves on the previous model we evaluated, so it's a viable alternative worth keeping in mind".

## Finalize the documentation

Add a row to the overview table in [data/results/readme.md](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md) with:

- the log folder link,
- the date,
- the related PR link, and
- short notes describing the experiment.

## Result locations

Top-level `logs/` and `predictions/` are local or cluster run locations. They should not contain committed repository data.

Committed experiment artefacts belong under:

- `kibad-llm-results:/logs/<experiment_id>` for logs, evaluation outputs, experiment documentation, and figures,
- `kibad-llm-results:/predictions/<experiment_id>` for copied prediction outputs, when prediction was part of the experiment.
