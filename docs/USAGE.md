# Usage Instructions

## Table of Contents

- [Setup](#setup)
- [Datasets](#datasets)
- [PDF Dataset Statistics](#pdf-dataset-statistics)
- [PDF Download Based on Zotero Groups](#pdf-download-based-on-zotero-groups)
    - [Prerequisites](#prerequisites-pdf-download)
    - [Downloading Papers](#downloading-papers)
- [Faktencheck Postgres to Json Conversion](#faktencheck-postgres-to-json-conversion)
    - [Prerequisites](#prerequisites-json-conversion)
    - [DB conversion](#db-conversion)
    - [Scientific-name normalization](#scientific-name-normalization)
    - [Syncing Nextcloud PDFs with the cluster storage](#syncing-nextcloud-pdfs-with-the-cluster-storage)
- [Information Extraction from PDFs](#information-extraction-from-pdfs)
    - [Prerequisite: choose an LLM backend](#prerequisite-choose-an-llm-backend)
    - [Inference](#inference)
        - [Codex extraction backend](#codex-extraction-backend)
    - [Prompt templates and schema descriptions](#prompt-templates-and-schema-descriptions)
        - [Codex file inputs](#codex-file-inputs)
    - [Prediction confidence](#prediction-confidence)
    - [CPU smoke test with a micro LLM](#cpu-smoke-test-with-a-micro-llm)
    - [Token usage in prediction results](#token-usage-in-prediction-results)
    - [Evaluation](#evaluation)
    - [Multirun](#multirun)
    - [A/B Testing with Multiple Seeds](#ab-testing-with-multiple-seeds)

> [!WARNING]
> All commands below assume that you are in the root directory of this project (where this `USAGE.md` is located).

> [!TIP]
> If you're new to `uv`:
> In places where you used to use `python`, with `uv` you tend to write `uv run` instead.
> What used to be `source .venv/bin/activate` and then `python your-script.py first-arg second-arg` now is reduced to `uv run your-script.py first-arg second-arg`.

## Setup

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

## Datasets

See [data/readme.md](/data/readme.md) for an in-depth documentation of the various datasets and ground truth reference files available, as well as other potentially relevant data sources.

## PDF Dataset Statistics

Use `uv run -m kibad_llm.statistics.pdf` to summarize document counts, PDF pages, and
markdown characters from PDF folders, converted JSONL files, and an optional metadata CSV.
Output is JSON or Markdown, with optional grouping by input folder or metadata column.
Grouping by a metadata column requires `--metadata`.
Run `uv run -m kibad_llm.statistics.pdf --help` for input options and counting rules.

## PDF Download Based on Zotero Groups

It is possible to download papers using the open access url from Semantic Scholar.

<a id="prerequisites-pdf-download"></a>

### Prerequisites

An export of a Zotero group as CSV file, see [data/external/zotero](/data/external/zotero) for the "Faktencheck Artenvielfalt" groups. Information how to export a Zotero group can be found in the [Zotero documentation](https://www.zotero.org/support/kb/exporting).

### Downloading Papers

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

## Faktencheck Postgres to Json Conversion

<a id="prerequisites-json-conversion"></a>

### Prerequisites

The following environment variables need to be set in a `.env` file in the root directory:

```
# docker-compose credentials for faktencheck database
DB_USER=<username-here>
DB_PASSWORD=<password-here>
```

Then, run the faktencheck database with podman (see [podman/faktencheck-db/README.md](/podman/faktencheck-db/README.md) for instructions).

### DB conversion

Run the following command to convert the faktencheck database to json files:

```bash
uv run -m kibad_llm.data_integration.db_converter
```

This will create a `data/interim/faktencheck-db` directory with json files.

Call `uv run -m kibad_llm.data_integration.db_converter --help` for more options.

### Scientific-name normalization

Normalize the scientific species names in the converted Faktencheck database with the GBIF Species Match
API:

```bash
uv run -m kibad_llm.normalization.cli gbif \
  --input-paths data/interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl \
  --read-key scientific_name \
  --parent-keys taxa
```

This will read the `scientific_name` values from the `taxa` field in the input file `data/interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl` and write the normalized values to
a new file `faktencheck-db-converted_2025-11-05_scientific_name_normalized.jsonl`. By default, normalized values
are written to `gbif_normalized` in `taxa`. The first positional argument
selects the normalization service; currently, `gbif` is available. The command logs the number of records read
and values successfully normalized.

See `uv run -m kibad_llm.normalization.cli gbif --help` for available options.

> [!TIP]
> This works also on the inference results, e.g., to normalize scientific names extracted from PDFs.

### Syncing Nextcloud PDFs with the cluster storage

Run the following command to synch the Nextcloud folder at
https://cloud.dfki.de/owncloud/index.php/s/dPc2BSDDEAT4R2W?path=%2FPDFs%20Literaturdatenbank with the PDF directory
on the cluster at /ds/text/kiba-d/zotero_literaturdatenbank/ .

```bash
uv run -m kibad_llm.data_integration.synch_nextcloud_with_cluster
```

## Information Extraction from PDFs

<a id="prerequisite-llm-hosting"></a>

### Prerequisite: choose an LLM backend

Choose a backend through the extractor configuration under [configs/extractor/llm](/configs/extractor/llm). For vLLM, follow the instructions [here for a quickstart](/models/README.md#quickstart), [here for an all-in-one script](/models/README.md#all-in-one-run-script) or [here for general instructions on uv and the cluster](/models/README.md#the-two-ways-to-use-uv-on-pegasus). OpenAI-hosted models use `OPENAI_API_KEY`; the [Codex backend](#codex-extraction-backend) uses a separately installed CLI.

### Inference

The information extraction pipeline can be run with:

```bash
uv run -m kibad_llm.predict \
pdf_directory=path/to/pdf/files
```

This will process all PDF files in `pdf_directory` and save the result in a JSON line file. See [data/readme.md](/data/readme.md) for a description of the various PDF datasets available, and their storage locations.

See [configs/predict](/configs/predict.yaml) for further information and options.

**NOTE:** If you plan on using OpenAI API models such as 'gpt_5' or access-restricted Huggingface models such as
'gemma3_27b', you need to set the environment variables `OPENAI_API_KEY` and/or `HF_TOKEN` in your `.env` file.
You can create an Open AI key at https://platform.openai.com/api-keys and Huggingface access tokens at https://huggingface.co/settings/tokens.

IMPORTANT: Relevant inference setups should be defined in their own `experiment/predict` config. This allows to easily reproduce results later on by adding `experiment/predict=<experiment_config>` to the command line call. For example, to run the experiment with two schemata ([configs/experiment/predict/faktencheck_two_schemata.yaml](/configs/experiment/predict/faktencheck_two_schemata.yaml)), use:

```bash
uv run -m kibad_llm.predict \
pdf_directory=path/to/pdf/files \
experiment/predict=faktencheck_two_schemata
```

See [configs/experiment/predict](/configs/experiment/predict) for available experiment configs.

There are inference options in [configs/predict](/configs/predict.yaml) that may significantly speed up the process. Those are disabled per default because they have the potential to overwhelm the provided hardware.

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

#### Codex extraction backend

Install Codex CLI on a Linux host that supports its restricted filesystem sandbox. The backend checks `CODEX_API_KEY` first, then `OPENAI_API_KEY`, including a project key loaded from `.env`. The first available key selects the API project for the run, even if the host also has a saved Codex login.

With both keys unset, the backend uses the file-backed login from `$CODEX_HOME/auth.json`, which defaults to `~/.codex/auth.json`. For ChatGPT sign-in, use a dedicated, writable `CODEX_HOME` for both `codex login` and extraction. The backend writes refreshed credentials back to that file and serializes extraction calls that share it. Reserve that login for extraction to avoid concurrent refreshes by other Codex processes.

Choose an explicit model available to the selected credential with `extractor.llm.model=MODEL`. The default model is an alias. Hosted inference and agent execution can vary across reruns.

```bash
uv run -m kibad_llm.predict \
  name=codex_fixture \
  experiment/predict=faktencheck_core_fields_schema_with_evidence_codex \
  pdf_directory=tests/fixtures/pdfs
```

The preset stages the source Markdown and the evidence-adjusted JSON Schema as files. See [Codex file inputs](#codex-file-inputs) to reference them in a custom prompt. You can override `extractor.llm.reasoning_effort` (default `high`) and `extractor.llm.timeout` (default 600 seconds).

The preset sets `extractor.use_guided_decoding=false`. Note that, per default, the extractor validates the response after inference (`extractor.validate_with_schema=true`). Keep `extractor.request_parameters` empty. Codex rejects guided decoding and additional request parameters before starting the CLI.

Each call launches a fresh ephemeral Codex process in a document workspace. Shell commands have a restricted filesystem profile and no network access. Web search, apps, and plugins are disabled. The backend checks workspace access before inference. If sandboxing is unavailable, the extraction records an error. Use a job-local Hydra run directory on shared filesystems to keep temporary runtime state off shared storage.

The Hydra run directory contains prompts, final responses, execution events, and errors. Keep it with the predictions to retain the execution diagnostics. See [Token usage in prediction results](#token-usage-in-prediction-results) for the usage data recorded in the predictions.

<a id="schema-descriptions-in-prompts"></a>

### Prompt templates and schema descriptions

Put message text in `prompt_template` under `system_message` or `user_message`. Use `{schema}` for inline JSON Schema and `{schema_description}` for a readable description. Template fields can appear in either message. Unrecognized settings in an inline `prompt_template` raise `TypeError`.

OpenAI and vLLM prompts must reference `{document}` for inline source text on the first turn. Follow-ups with history can omit it. See [Codex file inputs](#codex-file-inputs) for how to attach the source document in Codex prompts.

Schema fields are optional even when the extractor uses a schema for guided decoding or output validation. Referencing a schema field requires a schema. When the schema is missing, the backend reports which field requested it. An unknown field raises `MissingBindingError` during rendering.

The readable description is generated by [build_schema_description](/src/kibad_llm/schema/description.py).

Descriptions are assigned a role before formatting:

- A property's `description` appears on its field line, including for inline objects, inline enums, nullable fields, and evidence wrappers.
- Root and nested type descriptions appear on `Beschreibung:` lines. Array item descriptions and non-null branch descriptions belong to their respective types.
- Enum type descriptions, such as those in referenced `$defs`, appear under `Hinweise zu den Werten:`.

`anyOf`/`oneOf` unions whose non-null branches are all objects are rendered as numbered variants (the label before the number is set by the `variant_prefix` argument of `build_schema_description`), also at the root and when nested. Fields that render identically in all variants are listed once; the remaining fields are listed per variant together with the variant's description. A `const` (e.g. a `Literal` discriminator) is shown as a single allowed value. Unions that mix objects with other types still show only the first typed non-null branch, and `allOf` combined with an object union is not supported.

The same annotation is rendered once per field occurrence. Independent annotations with identical wording are preserved, and each use of a shared type retains its documentation. Evidence wrapping keeps field instructions on the wrapper; entering its `content` and `evidence_anchor` properties does not repeat those instructions.

The `include_evidence` option wraps extracted values with an evidence anchor. The bundled evidence config sets `use_wrapped_schema_in_prompt: true` so the model sees the wrapped schema in its prompt.

When migrating an extractor config, Hydra override, or Python call, rename `adjust_schema_for_evidence_detection` to `include_evidence` and `adjust_schema_description_for_evidence_detection` to `use_wrapped_schema_in_prompt`. Keep the same boolean values. Use the recorded code revision to replay older experiments verbatim.

Set `schema_description_kwargs` inside `extractor.prompt_template` to configure the readable description. `include_field_descriptions=False` hides property documentation completely; `type_description_prefix=None` hides root/type documentation; `choices_description_prefix=None` hides enum documentation. These options work at every nesting level. `choices_prefix=None` hides enum values independently of their documentation. The deprecated `include_type_descriptions=False` remains supported.

This is a prompt summary, not a complete JSON Schema validator. Local references, inline objects, arrays, nullable unions, and enum compositions are supported. Enum unions combine choices and enum intersections retain their common choices. General structural unions display a representative non-null branch. Unresolved or recursive references, list-valued `type`, and multi-branch structural `allOf` raise `ValueError` instead of producing an incomplete or infinitely recursive description. Cardinality retains the existing convention: arrays use `0..*`; other fields use `0..1` if a default is present, otherwise `1`.

This template includes the full JSON Schema.

```yaml
prompt_template:
  system_message: |
    Extract the requested information and return JSON matching this schema.
    {schema}
  user_message: "{document}"
```

`use_wrapped_schema_in_prompt` selects the schema for `{schema}`, `{schema_description}`, and Codex's `{schema_filename}` independently of guided decoding. Set it to `false` to use the original schema in templates that explain the wrappers themselves.

#### Codex file inputs

With Codex, use `{document_filename}` to stage the source Markdown as `input.md` and `{schema_filename}` to stage the prompt schema as `schema.json`. Both filename fields are optional on every turn, including the first. Each call starts with a fresh workspace, so reference a filename field again in any follow-up that needs the file. Only replacement fields request files. Literal filenames and escaped braces are treated as text.

```yaml
extractor:
  prompt_template:
    user_message: |
      Lies das Markdown-Dokument aus `{document_filename}`.
      Verwende das JSON-Schema aus `{schema_filename}`.
```

### Prediction confidence

Add `_with_confidence` to an extractor config's Hydra defaults to request an integer score from 1 to 5 for each non-null extracted value. The score expresses how sure the model is that its extracted value is correct. With a bundled extractor, pass `+extractor.include_confidence=true` on the command line. For organism trends, select `extractor/schema=organism_trends`. Set `extractor.include_evidence=false` for scores alone.

Select `extractor/prompt_template=default_with_confidence` to include the full five-level rubric once per turn. Customize the short field description by setting `confidence_description` in the helper. With a bundled extractor, add custom wording using `+extractor.confidence_description`.

For example, a model may return `{"content": "negative", "confidence": 4}` for a trend direction. The JSONL stores these estimates in `structured_with_metadata` for the simple extractor and in `structured_with_metadata_list` for multi-call extractors using the default `return_as_list`. Each score belongs to its individual model response. The `structured` field contains the extraction values used for evaluation.

### CPU smoke test with a micro LLM

Use [SmolLM2-135M-Instruct](https://huggingface.co/HuggingFaceTB/SmolLM2-135M-Instruct) for local pipeline testing. The [model config](/configs/extractor/llm/smollm2_135m_in_process.yaml) uses `kibad_llm.llms.VllmInProcess`, so no model server or API key is needed. The public weights require no Hugging Face token. This 135-million-parameter model is intended for smoke tests; its predictions are not suitable for evaluating extraction quality.

The standard PyPI vLLM package targets GPUs. Install a **CPU build of vLLM 0.12.0** into the project environment instead. For Linux ARM64, the official package index provides a prebuilt CPU wheel, so no compiler or source build is needed:

```bash
uv pip install --torch-backend cpu 'vllm==0.12.0+cpu' \
  --extra-index-url https://wheels.vllm.ai/0.12.0/cpu/
```

The wheel command above is specific to Linux ARM64. For AMD64, vLLM provides the [prebuilt CPU container](https://gallery.ecr.aws/q9t5s3a7/vllm-cpu-release-repo) `public.ecr.aws/q9t5s3a7/vllm-cpu-release-repo:v0.12.0`; the 0.12.0 CPU wheel index currently lists only an ARM64 wheel. Follow the [vLLM CPU installation instructions](https://docs.vllm.ai/en/v0.12.0/getting_started/installation/cpu/) for platform requirements and native CPU builds. Choose a runtime compatible with the project's vLLM version range. Use `uv run --no-sync` afterwards to retain the CPU-specific installation. Plain `uv run` or `uv sync` can restore the GPU package pinned in `uv.lock`.

If vLLM reports `Device string must not be empty`, it has detected no usable device backend. On a CPU-only machine, check that the active environment contains a CPU build of vLLM. The `VLLM_CPU_*` settings below tune that backend; they do not install or select it. `--no-sync` preserves the current installation, so reinstall the CPU runtime first if an earlier sync replaced it.

From the repository root, run:

```bash
export VLLM_CPU_KVCACHE_SPACE=1
export VLLM_CPU_OMP_THREADS_BIND=nobind
export OMP_NUM_THREADS=4
uv run --no-sync -m kibad_llm.predict experiment/predict=micro_llm
```

The [smoke-test preset](/configs/experiment/predict/micro_llm.yaml) processes all four complete PDFs in `tests/fixtures/pdfs`, splits their text into 6,000-character chunks, and predicts the main language (`de`, `en`, or `other`) of each chunk using a small, bounded JSON schema. Chunk predictions are combined by majority vote. Evidence wrappers are disabled. It uses an 8,192-token context, compact JSON decoding, and a 64-token response limit. Results and run metadata are written to the usual `predictions/micro_llm` and `logs/micro_llm` directories. These environment settings limit the KV cache to 1 GiB and use four CPU threads. Override `pdf_directory` to test another directory.

### Token usage in prediction results

Each LLM call records its token usage in `SingleExtractionResult.backend_metadata.usage`.
The simple extractor writes this to `backend_metadata` in the prediction JSONL.
The default chunking, repeat, union, conditional union, and multi-pass configs preserve each
call's metadata in `backend_metadata_list`, in call order. When customizing `return_as_list`,
include `backend_metadata` to retain it.

OpenAI Responses preserves the API's usage fields, including `input_tokens`, `output_tokens`,
`total_tokens`, `input_tokens_details.cached_tokens`, and `output_tokens_details.reasoning_tokens`.
API-hosted vLLM preserves its reported usage, including `prompt_tokens`, `completion_tokens`,
`total_tokens`, and any token details supplied by the server. For example:

```json
{
  "backend_metadata": {
    "usage": {
      "input_tokens": 120,
      "input_tokens_details": {"cached_tokens": 80},
      "output_tokens": 30,
      "output_tokens_details": {"reasoning_tokens": 10},
      "total_tokens": 150
    }
  }
}
```

In-process vLLM records `prompt_tokens`, `completion_tokens`, and `total_tokens` from the returned
token IDs, plus `prompt_tokens_details.cached_tokens` when available. Completion tokens include
reasoning and all generated candidates. If prompt token IDs are unavailable, prompt and total
counts are omitted.

For Codex, `backend_metadata.usage` contains the CLI's individual usage reports in event order. Each list entry preserves the CLI's native fields without calculating totals.

Metadata is retained even if response parsing, schema validation, or reasoning extraction fails.
It is `null` when there is no response or the backend does not report usage; missing counts are
not estimated. Older prediction files remain readable without this field. These records contain
token counts only; monetary costs and aggregation across calls or documents are not computed.

### Evaluation

To evaluate the information extraction results against gold reference data, run:

```bash
uv run -m kibad_llm.evaluate \
dataset.predictions.file=path/to/predictions.jsonl
```

Per default, this uses `dataset=faktencheck` with `data/interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl` as reference data and calculates micro averaged precision, recall and F1-score for all fields in the Faktencheck database (i.e., `metric=f1_micro`, see [configs/metric/f1_micro.yaml](/configs/metric/f1_micro.yaml) for details). See [configs/metric](/configs/metric) for other available metrics.

To evaluate against a different dataset, set the `dataset` parameter. For instance, to evaluate organism trends for the forest habitat, use `dataset=organism_trends_forest`. See [configs/dataset](/configs/dataset) for available datasets, and [data/readme.md](/data/readme.md) for a description of the ground truth dataset files available.

See [configs/evaluate.yaml](/configs/evaluate.yaml) for further information and options.

Note: The `confusion_matrix` metric calculates the confusion matrix just for a single field, which needs to be specified (`metric.field=<field>`). To evaluate multiple fields at once, use multirun below.

Similar as for inference, relevant evaluation setups should be defined in their own `experiment/evaluate` config. For example, to run the evaluation with the F1 scores on the flattened Faktencheck predictions ([configs/experiment/evaluate/faktencheck_f1_micro_flat.yaml](/configs/experiment/evaluate/faktencheck_f1_micro_flat.yaml)), use:

```bash
uv run -m kibad_llm.evaluate \
dataset.predictions.file=path/to/predictions.jsonl \
experiment/evaluate=faktencheck_f1_micro_flat
```

See [configs/experiment/evaluate](/configs/experiment/evaluate) for available experiment configs.

### Multirun

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

See [configs/hydra/default.yaml](/configs/hydra/default.yaml) for further configuration options and details on the Hydra callback to create the combined output (`save_job_return`).

### A/B Testing with Multiple Seeds

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
