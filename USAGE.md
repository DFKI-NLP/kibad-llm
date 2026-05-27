# Usage Instructions

> [!WARNING]
> All commands below assume that you are in the root directory of this project (where this `README.md` is located).

> [!TIP]
> If you're new to `uv`:
> In places where you used to use `python`, with `uv` you tend to write `uv run` instead.
> What used to be `source .venv/bin/activate` and then `python your-script.py first-arg second-arg` now is reduced to `uv run your-script.py first-arg second-arg`.

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
uv run -m kibad_llm.predict \
pdf_directory=path/to/pdf/files
```

This will process all PDF files in `pdf_directory` and save the result in a JSON line file.

See [configs/predict](./configs/predict.yaml) for further information and options.

**NOTE:** If you plan on using OpenAI API models such as 'gpt_5' or access-restricted Huggingface models such as
'gemma3_27b', you need to set the environment variables `OPENAI_API_KEY` and/or `HF_TOKEN` in your `.env` file.
You can create an Open AI key at https://platform.openai.com/api-keys and Huggingface access tokens at https://huggingface.co/settings/tokens.

IMPORTANT: Relevant inference setups should be defined in their own `experiment/predict` config. This allows to easily reproduce results later on by adding `experiment/predict=<experiment_config>` to the command line call. For example, to run the experiment with two schemata ([configs/experiment/predict/faktencheck_two_schemata.yaml](./configs/experiment/predict/faktencheck_two_schemata.yaml)), use:

```bash
uv run -m kibad_llm.predict \
pdf_directory=path/to/pdf/files \
experiment/predict=faktencheck_two_schemata
```

See [configs/experiment/predict](./configs/experiment/predict) for available experiment configs.

There are inference options in [configs/predict](./configs/predict.yaml) that may significantly speed up the process. Those are disabled per default because they have the potential to overwhelm the provided hardware.

<details>
<summary>Click for more info.</summary>

**`pdf_reader_num_proc: <integer greater 0>`:**<br>
Use this to set the number of parallel processes for converting PDF to Markdown.<br>
Set the variable to a number smaller than the number of available CPU cores to allow other process to run simultaneously.
This is important for execution on personal machines or Pegasus login nodes!<br>
On compute nodes it is recommended to set a large value, like 200. It may be larger than the number of available CPU cores or documents to process.

**`extractor_num_proc: <integer greater 0>`:**<br>
Use this to send more than one simultaneous request to vLLM.

</details>

#### Evaluation

To evaluate the information extraction results against gold reference data, run:

```bash
uv run -m kibad_llm.evaluate \
dataset.predictions.file=path/to/predictions.jsonl
```

Per default, this uses `dataset=faktencheck` with `data/interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl` as reference data and calculates micro averaged precision, recall and F1-score for all fields in the Faktencheck database (i.e., `metric=f1_micro`, see [configs/metric/f1_micro.yaml](./configs/metric/f1_micro.yaml) for details). See [configs/metric](./configs/metric) for other available metrics.

To evaluate against a different dataset, set the `dataset` parameter. For instance, to evaluate organism trends for the forest habitat, use `dataset=organism_trends_forest`. See [configs/dataset](./configs/dataset) for available datasets.

See [configs/evaluate.yaml](./configs/evaluate.yaml) for further information and options.

Note: The `confusion_matrix` metric calculates the confusion matrix just for a single field, which needs to be specified (`metric.field=<field>`). To evaluate multiple fields at once, use multirun below.

Similar as for inference, relevant evaluation setups should be defined in their own `experiment/evaluate` config. For example, to run the evaluation with the F1 scores on the flattened Faktencheck predictions ([configs/experiment/evaluate/faktencheck_f1_micro_flat.yaml](./configs/experiment/evaluate/faktencheck_f1_micro_flat.yaml)), use:

```bash
uv run -m kibad_llm.evaluate \
dataset.predictions.file=path/to/predictions.jsonl \
experiment/evaluate=faktencheck_f1_micro_flat
```

See [configs/experiment/evaluate](configs/experiment/evaluate) for available experiment configs.

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

For evaluation, you can additionally request an aggregated result over all runs (e.g., mean and standard deviation across multiple non-deterministic runs or different seeds). To do so, add the `+hydra.callbacks.save_job_return.multirun_markdown_group_by` override:

```bash
uv run -m kibad_llm.evaluate \
  dataset.predictions.file=path/to/A/predictions.jsonl,path/to/B/predictions.jsonl,path/to/C/predictions.jsonl \
  +hydra.callbacks.save_job_return.multirun_markdown_group_by=overrides.pdf_directory \
  --multirun
```

This also works for multiple columns at once:

```bash
+hydra.callbacks.save_job_return.multirun_markdown_group_by=[column1,column2]
```

See (https://github.com/DFKI-NLP/kibad-llm/pull/241) for details.

Below are more complex examples of using multirun for prediction and evaluation:

For evaluation of multiple predictions we can use this command argument `prediction_logs` which evaluates all prediction files (e.g., from different runs or seeds) in a single execution and aggregates the results. In detail, `prediction_logs` accepts a list of paths and all prediction log files beneath them will be read for the location of actual predictions that are then loaded.

Note: `prediction_logs`s only simplifies path handling; it does not trigger aggregation on its own. Use `multirun_markdown_group_by` (as shown above) if you want to aggregate the loaded results.

```bash
uv run -m kibad_llm.evaluate \
  prediction_logs=[log/path/to/(multi)run/x] \
  --multirun
```

See [configs/hydra/default.yaml](./configs/hydra/default.yaml) for further configuration options and details on the Hydra callback to create the combined output (`save_job_return`).

#### A/B Testing with Multiple Seeds

We can perform a multirun with three different random seeds and A/B testing (see `my_variable`, don't forget to prepend `+` to any variable *not* yet set in the config) like so:

```bash
uv run -m kibad_llm.predict \
    my_variable=value_a,value_b \
    seed=42,1337,7331 \
    --multirun
```

and compute mean and standard deviation like so:

```bash
uv run -m kibad_llm.evaluate \
  prediction_logs=[log/path/to/(multi)run/x] \
  +hydra.callbacks.save_job_return.multirun_markdown_group_by=my_variable \
  --multirun
```
