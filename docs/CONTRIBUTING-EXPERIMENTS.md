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

- Check the existing overview table in [kibad-llm-results/readme.md](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md). Use the latest related experiments as references for naming, command structure, folder layout, and result documentation.
- Prefer a dedicated config under `configs/experiment/` when the setup is not trivial.
- Decide which input datasets (pdf directory) and ground truth files you need
- Keep predictions and evaluations scoped to the research question you want to answer.
- Decide which prediction and evaluation commands are needed before creating result artefacts.

## Preparation

Make sure that the `/data/results` submodule is cloned and checked out on a new branch for the experiment.
See [submodules](CONTRIBUTING.md#submodules) for general instructions and refer to this section for the [submodule data changing flow](CONTRIBUTING.md#submodule-data-changing-flow).

## Execution

### Choose a name

> [!TIP]
> Create a draft PR early in the experiment process to get the PR ID before naming run outputs.

Choose a descriptive experiment name:

```text
[pr_id]_[descriptive_text]
```

> [!IMPORTANT]
> Use the same `name` value in every `predict` and `evaluate` command that belongs to the experiment.

The name determines the experiment subfolders under:

- `logs/<name>` for run logs,
- `predictions/<name>` for generated prediction outputs, and
- `data/results/logs/<name>` and `data/results/predictions/<name>` for committed result artefacts.

### Prepare the experiment folder

Create the committed result folder:

```bash
mkdir -p data/results/logs/<name>
```

Create the experiment readme `data/results/logs/<name>/readme.md` with:

- a first-level heading with the experiment name, for example `# 481_faktencheck_core`,
- a short description of the goal, motivation, and hypothesis,
- a `Prediction` section when prediction commands were run,
- an `Evaluation` section when evaluation commands were run, and
- each executed command together with its printed result location (use repo-relative paths, if possible, to ease reproducibility).

Use result locations as printed by the command, for example:

```text
result location: logs/481_faktencheck_core/evaluate/multiruns/2026-05-26_14-21-18
```

### Step-by-step Guide

Since the process for preparing the branches in the main repo and submodule is a bit tricky, here is a step-by-step
guide of bash commands, up to and including the creation of experiment readme. We assume that you name the
branch `experiment/your_descriptive_experiment_name` as chosen above, i.e. `[pr_id]_[descriptive_text]`. However,
this requires that you know the PR id before you can actually create the PR, see the optional instruction below. Feel
free to name the branch using a `descriptive_experiment_name` that does not include the PR id.

**Optional:** To get the 'correct' PR ID before committing and creating a PR, have a look at the **open and closed**
[Issues](https://github.com/DFKI-NLP/kibad-llm/issues) and [Pull Requests](https://github.com/DFKI-NLP/kibad-llm/pulls), and use as
your PR ID max(issue_ids,pull_request_ids) + 1 (Github issue and PR ids use the same counter).
However, this can be error-prone, so it's fine to name the branch without the `pr_id`.

```bash
cd <path/to/kibad-llm>

# Get clean, up-to-date copy of main
git checkout main
git pull
cd data/results
git checkout main
git pull
cd ../..
# Create branches
# <your_descriptive_experiment_name> = [pr_id]_[descriptive_text]
# new_pr_id = max(open_or_closed_issue_id_in_kibad_llm OR open_or_closed_pr_id_in_kibad_llm) + 1
# since this is error-prone, you can leave away the pr_id part
git switch -c experiment/<your_descriptive_experiment_name>
cd data/results
git switch -c experiment/<your_descriptive_experiment_name>

# Add empty readme.md and push branches upstream
mkdir -p logs/<your_descriptive_experiment_name>
touch logs/<your_descriptive_experiment_name>/README.md
git add logs/<your_descriptive_experiment_name>/README.md
git commit -m "initial commit of experiment branch"
git push --set-upstream origin experiment/<your_descriptive_experiment_name>
cd ../..
git add data/results
git commit -m "initial commit of experiment branch"
git push --set-upstream origin experiment/<your_descriptive_experiment_name>
```

- Go to https://github.com/DFKI-NLP/kibad-llm -> Create new draft PR

- Go to https://github.com/DFKI-NLP/kibad-llm-results/ -> Create new draft PR that references the kibad-llm PR in the description

- Edit \`data/results/logs/experiment/\<your_descriptive_experiment_name>/README.md as described [above](https://github.com/DFKI-NLP/kibad-llm/blob/main/docs/CONTRIBUTING-EXPERIMENTS.md#prepare-the-experiment-folder)

- Add a line to [data/results/readme.md](https://github.com/DFKI-NLP/kibad-llm-results/blob/main/readme.md):

    `| [<your_descriptive_experiment_name>](logs/<your_descriptive_experiment_name>) | <yyyy-MM-dd> | https://github.com/DFKI-NLP/kibad-llm/pull/<new_pr_id> | <your_descriptive_text> |`

```bash
# Add updated readme's
cd data/results
git add logs/<your_descriptive_experiment_name>/README.md
git add readme.md
git commit -m "update readme"
git push
cd ../..
git add data/results
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
       name=<name> \
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
name=<name> \
experiment/evaluate=<evaluate_experiment_config> \
prediction_logs=logs/<name>/predict \
--multirun
```

To evaluate selected prediction runs instead of every run under `logs/<name>/predict`, pass explicit prediction log paths:

```bash
prediction_logs=[logs/<name>/predict/multiruns/<timestamp-1>,logs/<name>/predict/multiruns/<timestamp-2>]
```

Copy local evaluation outputs to the committed result folder (execute from `data/results`):

```text
cp -r ../../logs/<name>/evaluate logs/<name>/evaluate
```

### Inspect results in the eval dashboard

Open the [eval dashboard](https://dfki-nlp.github.io/kibad-llm/eval-dashboard-docs/) and load the new evaluation data, usually:

```text
data/results/logs/<name>/evaluate
```

Configure the dashboard so the experiment hypothesis is easy to verify or reject. Download selected figures into:

```text
data/results/logs/<name>/figures/
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

- `data/results/logs/<name>` for logs, evaluation outputs, experiment documentation, and figures,
- `data/results/predictions/<name>` for copied prediction outputs, when prediction was part of the experiment.
