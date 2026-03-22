# `kibad-llm` codebase description

## Purpose and scope

`kibad-llm` is a Hydra-configured Python project for LLM-based information extraction from PDFs plus downstream evaluation against reference datasets. The codebase combines:

- PDF-to-markdown conversion,
- configurable extractor orchestration,
- multiple LLM backends,
- schema-driven structured output,
- dataset loaders for predictions and reference data,
- evaluation metrics,
- data-integration scripts for preparing and inspecting source datasets,
- Hydra callbacks for persisting run and multirun results.

At a high level, the main runtime flows are:

1. **Prediction flow**: `PDF -> markdown text -> extractor -> JSONL predictions`
2. **Evaluation flow**: `predictions + references -> metric -> JSON/Markdown result`
3. **Data preparation flow**: PostgreSQL / Zotero / Nextcloud / analysis helpers -> intermediate data used by prediction or evaluation

The repository is structured around the package in `src/kibad_llm`, Hydra config groups in `configs/`, and a test suite in `tests/`.

---

## High-level architecture

### Main entry points

- `src/kibad_llm/predict.py` — batch PDF inference pipeline.
- `src/kibad_llm/evaluate.py` — batch evaluation pipeline.

### Supporting subsystems

- `kibad_llm.preprocessing` — PDF reading.
- `kibad_llm.extractors` — base extraction logic and composite extraction strategies.
- `kibad_llm.llms` — wrappers around OpenAI, OpenAI-like vLLM servers, and in-process vLLM.
- `kibad_llm.schema` — Pydantic schema definitions and JSON-schema utilities.
- `kibad_llm.dataset` — loading predictions and references from JSON/CSV/compressed files.
- `kibad_llm.metrics` / `kibad_llm.metric` — metric interfaces and concrete metrics.
- `kibad_llm.hydra_callbacks` — saving single-run and multirun return values.
- `kibad_llm.utils` — flattening, grouping, path handling, log helpers, and dataset map adapters.
- `kibad_llm.data_integration` — external-data preparation and inspection scripts.

### Configuration model

The project uses **Hydra** heavily:

- `configs/predict.yaml` composes prediction runs.
- `configs/evaluate.yaml` composes evaluation runs.
- config groups under `configs/extractor/`, `configs/dataset/`, `configs/metric/`, `configs/experiment/`, etc. define interchangeable building blocks.

This makes the project strongly configuration-driven: the Python entry points are intentionally generic and delegate most concrete behavior to instantiated config targets.

---

## Runtime flow

### Prediction pipeline

`src/kibad_llm/predict.py` implements the inference pipeline.

Core steps:

1. Determine Hydra run directory and Git metadata.
2. Build a Hugging Face `datasets.Dataset` from all `*.pdf` files in `cfg.pdf_directory`.
3. Instantiate the configured PDF reader from `cfg.pdf_reader`.
4. Convert each PDF to markdown text via `dataset.map(...)`.
5. Instantiate the configured extractor from `cfg.extractor`.
6. Run extraction over the text dataset with optional caching and multiprocessing.
7. Optionally remove the raw text from the saved predictions.
8. Write predictions to JSONL under `cfg.output_dir/<timestamp>/<output_file_name>`.
9. Return run metadata such as output path, timings, Git revision, and possibly `SLURM_JOB_ID`.

Notable implementation details:

- Uses `datasets.Dataset.map` for both PDF conversion and extraction.
- Uses `wrap_map_func()` to adapt simple callables to the `datasets` mapping interface.
- Separates PDF conversion time and extraction time in the returned metadata.
- Supports a `fast_dev_run` mode that only processes the first PDF.
- Uses relative and absolute output paths in the result dictionary.

### Evaluation pipeline

`src/kibad_llm/evaluate.py` implements the evaluation flow.

Core steps:

1. Instantiate the configured dataset from `cfg.dataset`.
2. Instantiate the configured metric from `cfg.metric`.
3. Iterate over all dataset records.
4. Call `metric.update(prediction=..., reference=..., record_id=...)`.
5. Compute results via `metric.compute()`.
6. Log formatted output.
7. If predictions came from a run log and therefore carry metadata, attach that metadata under `prediction` in the metric result.

Notable implementation details:

- Registers a Hydra resolver `get_directories_with_file` used for evaluation over multiple prediction logs.
- Accepts datasets that may carry metadata via `DictWithMetadata`.
- Treats the metric as a generic pluggable object implementing the `Metric` interface.

---

## Source tree (`src/kibad_llm`)

```text
src/kibad_llm/
├── __init__.py
├── config.py
├── evaluate.py
├── metric.py
├── predict.py
├── preprocessing.py
├── data_integration/
│   ├── __init__.py
│   ├── database_unique_summary.py
│   ├── db_converter.py
│   ├── extract_vocabulary_enums.py
│   ├── synch_nextcloud_with_cluster.py
│   └── zotero_download.py
├── dataset/
│   ├── __init__.py
│   ├── compression.py
│   ├── csv.py
│   ├── json.py
│   ├── prediction.py
│   └── utils.py
├── extractors/
│   ├── __init__.py
│   ├── aggregation_utils.py
│   ├── base.py
│   ├── conditional.py
│   ├── repeat.py
│   └── union.py
├── hydra_callbacks/
│   ├── __init__.py
│   └── save_job_return_value.py
├── llms/
│   ├── __init__.py
│   ├── base.py
│   ├── openai.py
│   ├── openai_like_vllm.py
│   └── vllm_in_process.py
├── metrics/
│   ├── __init__.py
│   ├── base.py
│   ├── collection.py
│   ├── confusion_matrix.py
│   ├── f1.py
│   └── statistics.py
├── schema/
│   ├── __init__.py
│   ├── types.py
│   └── utils.py
└── utils/
    ├── datasets.py
    ├── dictionary.py
    ├── job_return.py
    ├── log.py
    └── path.py
```

---

## Module-by-module description of all implemented Python modules

## Package root modules

### `src/kibad_llm/__init__.py`
Very small package initializer. It imports `kibad_llm.config` for side effects so that path constants, `.env` loading, and logging setup happen when the package is imported.

### `src/kibad_llm/config.py`
Central path/bootstrap module.

Responsibilities:

- Loads environment variables from `.env` via `python-dotenv`.
- Defines repository-relative path constants such as:
  - `PROJ_ROOT`
  - `DATA_DIR`, `RAW_DATA_DIR`, `INTERIM_DATA_DIR`, `PROCESSED_DATA_DIR`, `EXTERNAL_DATA_DIR`
  - `MODELS_DIR`
  - `REPORTS_DIR`, `FIGURES_DIR`
- Reconfigures `loguru` to write via `tqdm.write()` when `tqdm` is installed, preventing progress bars and logs from garbling each other.

This file is foundational because many modules import `PROJ_ROOT` or data-directory constants from here.

### `src/kibad_llm/predict.py`
Primary inference entry point.

Key functions:

- `_file_name_generator(file_names)` — emits dictionaries of the form `{"file_name": ...}` for building a `datasets.Dataset`.
- `get_git_info()` — captures commit hash, branch, and dirty-state using `gitpython`.
- `get_run_log_dir()` — safely extracts Hydra’s runtime output directory.
- `predict(cfg)` — orchestrates the complete PDF-to-prediction pipeline.
- `main(cfg)` — Hydra entry point.

Important design decisions:

- Uses sorted file names as the dataset basis, which stabilizes cache keys but also means adding/removing files changes the dataset fingerprint.
- Uses Hydra-instantiated callables for both `pdf_reader` and `extractor`.
- Explicitly deletes the extractor after use to potentially free GPU memory, especially relevant for in-process vLLM models.

### `src/kibad_llm/evaluate.py`
Primary evaluation entry point.

Key functions:

- `evaluate(cfg)` — loads a merged prediction/reference dataset, instantiates a metric, updates it per record, computes results, and appends prediction metadata if available.
- `main(cfg)` — Hydra entry point.

Notable feature:

- Registers a custom OmegaConf resolver to derive prediction-run directories from log roots for Hydra multirun evaluation.

### `src/kibad_llm/preprocessing.py`
Minimal PDF preprocessing module.

Key function:

- `read_pdf_as_markdown_via_pymupdf4llm(file_name, base_path)` — converts a PDF file to markdown text using `pymupdf4llm.to_markdown(...)`.

In practice, this function is used as the default `pdf_reader` target via Hydra.

### `src/kibad_llm/metric.py`
Defines the abstract metric interface used by evaluation.

Main class:

- `Metric`

Methods:

- `reset()` — clear internal state.
- `_update(...)` / `update(...)` — update state from one prediction/reference pair.
- `_compute(...)` / `compute(...)` — produce result dictionaries.
- `_format_result(...)` — default JSON formatting.
- `show_result(...)` — log formatted metric output.

This base class is intentionally lightweight and is extended by concrete metrics in `kibad_llm.metrics`.

---

## `data_integration` modules

### `src/kibad_llm/data_integration/__init__.py`
Empty package marker.

### `src/kibad_llm/data_integration/db_converter.py`
Converts the Faktencheck PostgreSQL database into JSONL.

Key concepts:

- Reads SQL query definitions from a YAML file.
- Executes a core query for the base record set.
- Executes additional vocabulary/linked queries per record.
- Emits one JSON object per database row.

Key functions:

- `query_core(cursor, query, query_vars)` — execute a SQL query and fetch all rows.
- `format_result(result, column_names)` — return either a scalar or a dict, depending on query width.
- `main(...)` — full conversion pipeline and CLI entry logic.

Important constant:

- `SINGLE_ENTITIES` — query names that should resolve to a single value rather than a list.

This is the main bridge from the relational database into evaluation-ready JSONL reference data.

### `src/kibad_llm/data_integration/zotero_download.py`
Downloads PDFs using Zotero exports and Semantic Scholar.

Main capabilities:

- Query Semantic Scholar by DOI.
- Query Semantic Scholar by title.
- Download PDFs directly from URLs stored in Zotero exports.
- Persist intermediate paper-ID lookups.

Key functions:

- `get_s2_data(ids)` — batch query to Semantic Scholar.
- `download_file(url, file_name, output_dir, ...)` — streamed PDF download.
- `get_s2_data_by_title(title)` — title-match API call.
- `get_paper_ids_by_title(df, paper_ids_file)` — cache title-based paper IDs.
- `get_papers_from_dois(df, verbose)` — resolve DOI-based open-access metadata.
- `main(file_path, output_dir, download_type)` — CLI workflow.

This module is an ingestion utility rather than part of the prediction runtime.

### `src/kibad_llm/data_integration/extract_vocabulary_enums.py`
Extracts enumeration values from the Faktencheck database for schema or analysis support.

Main capabilities:

- Parse vocabulary table names from SQL templates.
- Query vocabulary tables and selected direct columns.
- Limit output to fields with at most `top_n` unique values.

Key functions:

- `normalize_table_suffix(s)`
- `extract_vocabulary_table_name(query)`
- `query_vocabulary_values(cursor, table_suffix)`
- `query_direct_column_values(cursor, table, column)`
- `query_nested_column_values(cursor, query_template)`
- `extract_all_vocabulary_enums(...)`
- `main(...)`

Important constant:

- `DIRECT_COLUMNS` — non-vocabulary-table fields queried directly from base tables.

### `src/kibad_llm/data_integration/synch_nextcloud_with_cluster.py`
Synchronizes a public Nextcloud share with a local/cluster directory.

Main capabilities:

- List files from a public WebDAV Nextcloud share via `PROPFIND`.
- Compare share contents against local files.
- Download missing remote files.
- Upload missing local files.

Key functions:

- `list_nextcloud_files()`
- `list_local_files()`
- `download_file(filename)`
- `upload_file(filename)`
- `sync_nextcloud()`

This is operational infrastructure code for maintaining the PDF collection.

### `src/kibad_llm/data_integration/database_unique_summary.py`
Inspection utility for analyzing uniqueness and value distributions in JSONL exports.

Main capabilities:

- Flatten nested JSON-style structures.
- Detect columns that are single-label vs multi-label.
- Compute unique values per field.
- Display compact summaries for fields below a chosen cardinality threshold.

Key functions:

- `_get_list_cols(df)`
- `_sort_with_none(l, remove_none)`
- `get_unique_single_and_multi_values(df)`
- `show_unique_values_summary(input_file, top_n, fields, key_sep)`

Useful during schema design and reference-dataset understanding.

---

## `dataset` modules

### `src/kibad_llm/dataset/__init__.py`
Empty package marker.

### `src/kibad_llm/dataset/compression.py`
Generic text-file opener with transparent compression support.

Supported formats:

- plain text
- gzip (`.gz`)
- bzip2 (`.bz2`)
- xz (`.xz`)
- zip (`.zip`)
- tar and tar-compressed variants (`.tar`, `.tar.gz`, `.tar.bz2`, `.tar.xz`)
- zstandard (`.zst`)

Key functions:

- `_infer_compression(path)` — infer compression from filename suffix.
- `open_text(...)` — open a text file or archive member with the right decompressor.

This module underpins robust dataset loading from compressed reference or prediction files.

### `src/kibad_llm/dataset/csv.py`
CSV loader for organism trend reference data.

Key functions:

- `remove_nan_from_dict(d)` — drops `NaN` keys from dict records.
- `read_organism_trends(file, pdf_id_column, columns, remove_nan)` — groups CSV rows by PDF ID and returns nested records of the form `{"organism_trends": [...]}`.

This is the reference-data loader for the organism trends evaluation setup.

### `src/kibad_llm/dataset/json.py`
JSON / JSONL dataset loader with optional preprocessing.

Key function:

- `read_and_preprocess(file, id_key, encoding, process_id, preprocess, archive_member, **kwargs)`

Capabilities:

- Load a whole JSON object or a JSONL file.
- Use a field as the record ID and remove it from the value payload.
- Open compressed files using `dataset.compression.open_text`.
- Optionally preprocess each record after loading.

This is the general-purpose loader for reference JSONL data and predictions.

### `src/kibad_llm/dataset/prediction.py`
Prediction-loader helpers with run metadata support.

Main class:

- `DictWithMetadata` — a `dict` subclass that additionally carries a `metadata` property.

Key function:

- `load_with_metadata(log=None, file=None, skip_by_id=None, **load_kwargs)`

Behavior:

- If `log` is given, read:
  - `job_return_value.json`
  - `.hydra/overrides.yaml`
- Derive the actual prediction file path from the logged return value.
- Attach overrides and job-return metadata to the dataset.
- Optionally drop entries by ID.

This module is important because evaluation can preserve provenance from prediction runs.

### `src/kibad_llm/dataset/utils.py`
Helpers for combining dataset pieces.

Key function:

- `merge_references_into_predictions(predictions, references, allow_missing_references=False)`

Behavior:

- Creates a dataset keyed by record ID with values shaped like:
  - `{"prediction": ..., "reference": ...}`
- Can optionally allow missing references.
- Preserves prediction metadata when predictions are a `DictWithMetadata`.

This function is the glue used by dataset Hydra configs such as `configs/dataset/faktencheck.yaml`.

---

## `extractors` modules

### `src/kibad_llm/extractors/__init__.py`
Re-export module.

Exports:

- `extract_from_text`
- `extract_from_text_lenient`
- `ConditionalUnionExtractor`
- `RepeatingExtractor`
- `UnionExtractor`

### `src/kibad_llm/extractors/aggregation_utils.py`
Aggregation primitives for combining multiple extraction runs.

Key types:

- `InputType`, `OutputType`, `Aggregator`
- `AggregationError`

Key functions:

- `make_hashable_simple(value)` — convert nested lists/dicts into hashable representations.
- `collect_values_and_type_per_key(structured_outputs, skip_type_mismatches)` — gather values by field and enforce type consistency.
- `_majority_vote(values, exclude_none)`
- `_multi_entry_majority_vote(values)`
- `aggregate_majority_vote(...)`
- `_aggregate_unanimous(values)`
- `_multi_entry_union(values)`
- `aggregate_unanimous(...)`
- `aggregate_single_majority_vote_multi_union(...)`

This module defines the semantics for repeated or multi-schema extraction:

- **majority vote** for repeated noisy calls,
- **unanimity** for split-schema unions,
- **mixed strategy** for scalar/list combinations.

### `src/kibad_llm/extractors/base.py`
The core extraction engine and the largest single module in the package.

Major responsibilities:

1. Build chat prompts from templates and schema descriptions.
2. Call a configured LLM backend.
3. Parse response content into JSON.
4. Validate against JSON Schema when requested.
5. Optionally wrap outputs with metadata/evidence anchors.
6. Strip metadata back to clean structured outputs.
7. Return a rich `SingleExtractionResult` object.
8. Offer a lenient wrapper that catches all exceptions.

Important class:

- `SingleExtractionResult(FieldDict)`
  - stores `response_content`, `structured`, `structured_with_metadata`, `reasoning_content`, prompt messages, and error lists.

Important prompt-construction functions:

- `exception2error_msg(e)`
- `build_chat_message(...)`
- `build_chat_messages(...)`

Important metadata/evidence helpers:

- `_is_wrapper_dict(...)`
- `strip_metadata(...)`
- `_snippet_for_span(...)`
- `_strip_wrapping_quotes(...)`
- `_find_anchor_match_spans(...)`
- `augment_metadata_node_with_evidence(...)`
- `augment_metadata(...)`

Important postprocessing callbacks:

- `add_response_content_callback(...)`
- `add_reasoning_content_callback(...)`
- `add_structured_callback(...)`
- `augment_and_strip_metadata_from_structured_callback(...)`

Main execution functions:

- `extract_from_text(...)`
- `extract_from_text_lenient(text, text_id, **kwargs)`

This is the central abstraction of the entire project. Everything else in extraction either configures or composes this module.

### `src/kibad_llm/extractors/repeat.py`
Implements repeated extraction on the same text.

Main class:

- `RepeatingExtractor`

Behavior:

- Runs `extract_from_text_lenient(...)` `n` times.
- Aggregates `structured` outputs using the configured aggregator.
- Optionally returns per-run lists for selected fields (for example `errors_list` or `reasoning_content_list`).

Use case:

- Reduce stochastic LLM variation through majority voting.

### `src/kibad_llm/extractors/union.py`
Implements multi-setup extraction over one text.

Main class:

- `UnionExtractor`

Behavior:

- Iterates over a list/dict of override dictionaries.
- Runs the base extractor with those per-setup overrides.
- Aggregates the resulting `structured` outputs.
- Optionally returns lists of selected fields.

Use case:

- Split a complex schema into multiple extraction setups and merge results.

### `src/kibad_llm/extractors/conditional.py`
Implements a sequential union extractor where later extractions see previous prompt/response history.

Main class:

- `ConditionalUnionExtractor(UnionExtractor)`

Behavior:

- Similar to `UnionExtractor`, but:
  - requests formatted messages from each step,
  - appends those messages to a `history`,
  - passes the history into later steps,
  - suppresses the system message after the first step.

Use case:

- Multi-stage extraction where later schema queries depend on the earlier interaction context.

---

## `hydra_callbacks` modules

### `src/kibad_llm/hydra_callbacks/__init__.py`
Re-export module exposing `SaveJobReturnValueCallback`.

### `src/kibad_llm/hydra_callbacks/save_job_return_value.py`
Hydra callback for persisting single-run and multirun return values.

This module is central to experiment bookkeeping.

Helper functions:

- `to_py_obj(obj)` — convert NumPy arrays/scalars into Python-native types.
- `list_of_dicts_to_dict_of_lists_recursive(list_of_dicts)` — rearrange per-run results into aggregated columnar form.
- `remove_common_overrides(overrides_per_result)`
- `overrides_to_identifiers(overrides_per_result, sep, remove_common)`
- `identifier_to_dict(identifier, sep)`
- `handle_previous_overrides(job_return, key, replace_existing)`

Main class:

- `SaveJobReturnValueCallback`

Key capabilities:

- Save `job_return_value.json` and/or `job_return_value.md` for each run.
- Save multirun-level summary files under sweep directories.
- Optionally integrate multirun results into dict-of-lists form.
- Optionally aggregate numeric multirun results using `pandas.DataFrame.describe()`.
- Convert Hydra overrides into stable job IDs.
- Group markdown tables and compute mean/std for numeric columns.
- Handle embedded previous-result metadata such as evaluation results that include prediction provenance.

This callback makes Hydra output directly useful for experiment tracking and later analysis.

---

## `llms` modules

### `src/kibad_llm/llms/__init__.py`
Re-export module.

Exports:

- `OpenAI`
- `OpenAILikeVllm`
- `VllmInProcess`

### `src/kibad_llm/llms/base.py`
Defines the LLM abstraction used by extractors.

Important exception classes:

- `MissingRawChatResponseError`
- `RawMessageExtractionError`
- `MissingResponseContentError`
- `EmptyResponseMessageError`
- `ReasoningExtractionError`
- `EmptyReasoningError`

Important data class:

- `SimpleChatMessage` — thin role/content container.

Main abstract base class:

- `LLM`

Methods:

- `call_llm_chat_with_guided_decoding(...)` — abstract backend call.
- `get_raw_message_from_chat_response(...)`
- `get_reasoning_from_chat_response(...)`
- `get_response_content_from_chat_response(...)`

This abstraction allows the extraction layer to stay backend-agnostic.

### `src/kibad_llm/llms/openai.py`
OpenAI backend wrapper using the Responses API.

Key helper functions:

- `_schema_name_from(schema, default)` — derive a short schema name.
- `make_openai_strict_json_schema(schema)` — transform generic JSON Schema into a form acceptable for OpenAI strict structured outputs.

Main class:

- `OpenAI(LLM)`

Key features:

- Builds `text.format = {type: json_schema, strict: ...}` requests for OpenAI structured outputs.
- Optionally patches schemas into OpenAI-compatible strict mode.
- Returns reasoning summaries from `ThinkingBlock` content.
- Converts `BadRequestError` into `ValueError` for alignment with other backends.

The schema-patching logic is important because OpenAI’s strict structured output subset is narrower than general JSON Schema.

### `src/kibad_llm/llms/openai_like_vllm.py`
Wrapper for OpenAI-compatible externally hosted models, especially vLLM servers.

Main class:

- `OpenAILikeVllm(LLM)`

Key behavior:

- Injects guided-decoding schema under `extra_body["structured_outputs"] = {"json": schema}`.
- Uses `llama_index.llms.openai_like.OpenAILike` underneath.
- Extracts reasoning from either `reasoning` or legacy `reasoning_content` in the raw response message.

This is the default family for self-hosted vLLM-compatible endpoints.

### `src/kibad_llm/llms/vllm_in_process.py`
In-process vLLM backend.

Key functions:

- `cleanup()` — destroy distributed/model-parallel state and clear CUDA memory.
- `_chat_message_to_vllm_param(m)` — convert internal chat messages to vLLM request format.

Main class:

- `VllmInProcess(LLM)`

Key capabilities:

- Lazily or eagerly instantiate `vllm.LLM`.
- Use the model’s built-in chat template through `LLM.chat()`.
- Support guided decoding via `StructuredOutputsParams(json=...)`.
- Separate reasoning from final output using a configured reasoning parser.
- Explicitly destroy resources on cleanup.

This backend is useful when the model should run inside the same Python process rather than through an external API server.

---

## `metrics` modules

### `src/kibad_llm/metrics/__init__.py`
Re-export module.

Exports:

- `MetricCollection`
- `ConfusionMatrix`
- `F1MicroMultipleFieldsMetric`
- `F1MicroSingleFieldMetric`
- `ErrorCollector`

### `src/kibad_llm/metrics/base.py`
Shared helpers for metrics that normalize entries into sets.

Key helper:

- `_convert_dict_to_tuple(d, ignore_keys)` — convert dictionaries into comparable hashable tuples.

Main class:

- `MetricWithPrepareEntryAsSet(Metric)`

Key behavior:

- Optionally flatten nested dicts.
- Optionally extract a specific field.
- Normalize values into sets, handling scalars, lists, sets, and dicts.

This base class is used by the F1 and confusion-matrix metrics.

### `src/kibad_llm/metrics/collection.py`
Composite metric container.

Main class:

- `MetricCollection`

Behavior:

- Holds a mapping of named metrics.
- Propagates `reset`, `update`, and `compute` across them.
- Returns a dict keyed by submetric name.

### `src/kibad_llm/metrics/confusion_matrix.py`
Confusion matrix for single-label and multi-label set-style classification.

Main class:

- `ConfusionMatrix(MetricWithPrepareEntryAsSet)`

Key features:

- Computes counts of `(gold_label, predicted_label)`.
- Adds reserved labels for false positives and false negatives:
  - `UNASSIGNABLE`
  - `UNDETECTED`
- Can optionally log a markdown-formatted confusion matrix using pandas.

Methods of note:

- `calculate_counts(...)`
- `add_counts(...)`
- `_update(...)`
- `_compute(...)`

### `src/kibad_llm/metrics/f1.py`
Micro-F1 metrics for one or many fields.

Main classes:

- `F1MicroSingleFieldMetric`
- `F1MicroMultipleFieldsMetric`

`F1MicroSingleFieldMetric`:

- computes `tp`, `fp`, `fn`,
- derives `precision`, `recall`, `f1`, and `support`.

`F1MicroMultipleFieldsMetric`:

- creates one single-field metric per requested field,
- returns per-field metrics,
- computes:
  - `AVG` — macro-style mean over fields,
  - `ALL` — micro total over all field states,
- optionally formats output as a markdown table.

### `src/kibad_llm/metrics/statistics.py`
Error-frequency analysis metric.

Main class:

- `ErrorCollector`

Behavior:

- Looks for one of several supported error encodings in prediction records:
  - `error`
  - `error_list`
  - `errors`
  - `errors_list`
- Optionally logs each collected error.
- Returns counts such as `no_error`, `with_error`, and counts grouped by the error-type prefix before a separator.

This metric is aimed at debugging extraction robustness rather than comparing semantic field accuracy.

---

## `schema` modules

### `src/kibad_llm/schema/__init__.py`
Empty package marker.

### `src/kibad_llm/schema/types.py`
Large Pydantic schema library describing the extraction targets.

This is one of the most important domain modules in the repository. It defines:

- many `Enum` classes representing controlled vocabularies,
- shared base classes for schema models,
- compound feature models,
- multiple top-level extraction schemas for different tasks or schema granularities.

#### Base classes

- `BaseEcosystemStudyFeatures(BaseModel)` — common top-level model base with `extra="forbid"`.
- `CompoundFeature(BaseModel)` — base for nested/compound feature objects, also with `extra="forbid"`.

#### Main enum groups

The file contains many controlled vocabularies, including for example:

- habitat and geography:
  - `HabitatEnum`
  - `NaturalRegionEnum`
  - `LocationFederalStateEnum`
- ecosystem / service concepts:
  - `EcosystemTypeCategoryEnum`
  - `EcosystemTypeTermEnum`
  - `EcosystemServiceCategoryEnum`
  - `EcosystemServiceTermEnum`
- climate / land use / scale:
  - `ClimateEnum`
  - `LanduseEnum`
  - `SpatialExtentEnum`
  - `SpatialResolutionEnum`
  - `TemporalExtentUnit`
  - `TemporalResolutionEnum`
- methodology / study metadata:
  - `MethodEnum`
  - `StudyTypeEnum`
  - `BiodiversityLevelEnum`
  - `TransformationPotentialEnum`
- taxonomic and trend vocabularies:
  - `SpeciesGroupEnum`
  - `TrendCategoryEnum`
  - `HabitatForOrganismTrendEnum`
  - `BiodiversityVariableEnum`
- additional domain-specific groups such as conservation success, drivers, soil, and Red List groupings.

#### Compound models

Representative nested models include:

- `EcosystemType`
- `EcosystemTypeSimple`
- `Location`
- `Taxa`
- `Soil`
- `ConservationArea`
- `ManagementMeasure`
- `ImpulseMeasure`
- `DirectDriver`
- `IndirectDriver`
- `EcosystemService`
- `OrganismBiodiversityTrend`
- `OrganismBiodiversityTrendV1`

These encode structured subobjects rather than flat enum lists.

#### Top-level schema variants

The file defines multiple complete extraction targets, including:

- `EcosystemStudyFeaturesWithoutCompounds`
- `EcosystemStudyFeaturesSimple`
- `EcosystemStudyFeaturesCompoundsSimple`
- `EcosystemStudyFeaturesCompoundsOnly`
- `EcosystemStudyFeaturesAll`
- `EcosystemStudyOrganismTrends`
- `EcosystemStudyOrganismTrendsV1`
- `EcosystemStudyFeaturesCoreFields`

These top-level models are selected by Hydra config files under `configs/extractor/schema/` and compiled to JSON Schema via `.model_json_schema(...)`.

In effect, `schema/types.py` contains the project’s domain ontology for structured extraction.

### `src/kibad_llm/schema/utils.py`
JSON-schema processing utilities used mainly during prompt construction and evidence-aware extraction.

Main capabilities:

1. Turn JSON Schema into human-readable prompt instructions.
2. Resolve local `$ref` definitions.
3. Analyze enum choices and types across composed schemas.
4. Wrap terminal schema fields with metadata objects such as evidence anchors.

Important helpers for schema description:

- `_norm_desc(desc)`
- `_resolve_ref(schema, ref)`
- `_extract_choices_with_description(schema, node)`
- `_extract_type(schema, node)`
- `_pick_preferred_branch(node, root_schema)`
- `build_schema_description(...)`

Important metadata-wrapping constants:

- `METADATA_SCHEMA_WITH_EVIDENCE`
- `METADATA_SCHEMA_WITH_EVIDENCE_SHORTHAND`
- `WRAPPED_CONTENT_KEY = "content"`

Important metadata-wrapping helpers:

- `_is_objectish(node)`
- `_is_arrayish(node)`
- `_schema_should_be_wrapped(root, node, ...)`
- `_normalize_metadata_schema(metadata_schema)`
- `_is_metadata_wrapper(node, ...)`
- `_wrap_value_schema_with_metadata(value_schema, ...)`
- `wrap_terminals_with_metadata(schema, metadata_schema, ...)`

This module is crucial for the project’s advanced extraction mode where leaf values are returned together with textual evidence anchors.

---

## `utils` modules

### `src/kibad_llm/utils/datasets.py`
Tiny adapter module.

Key function:

- `wrap_map_func(func, result_key)` — wraps a plain callable so that it returns a dictionary suitable for `datasets.Dataset.map`.

### `src/kibad_llm/utils/dictionary.py`
Dictionary flattening/unflattening and dict-backed dataclass utilities.

Key functions:

- `flatten_dict_simple(d, sep)` — specialized flattening for shallow/nested extraction-style dicts.
- `_flatten_dict_gen(d, parent_key)`
- `flatten_dict(d, pad_keys)` — flatten to tuple keys, optionally padding levels with `NaN`.
- `flatten_dict_s(d, sep)` — flatten to string keys.
- `unflatten_dict(d, unpad_keys)` — reconstruct nested dicts.
- `get_and_map_keys(...)`
- `get(d, key, default)`

Important class:

- `FieldDict(dict[str, Any])`

`FieldDict` keeps dataclass fields and dictionary items synchronized, which is what enables `SingleExtractionResult` to behave both like a typed object and like a JSON-serializable dict.

### `src/kibad_llm/utils/job_return.py`
Helpers for loading and aggregating Hydra job-return artifacts.

Key functions:

- `overrides_to_dict(overrides, remove_plus_prefix)`
- `dict_to_overrides(d, remove_na)`
- `load(directory, subdir_pattern, ...)`
- `load_run(directory, filename, load_overrides)`
- `load_runs(directory, subdir, ...)`
- `_filter_nan_and_join(values, sep)`
- `multi_index_to_single(index, sep)`
- `mixed_group_by(data, by, numeric_agg_func, numeric_fill_na, force_list_col_regex, columns_name)`

This module complements the Hydra callback module and is mainly for later programmatic analysis of experiment outputs.

### `src/kibad_llm/utils/log.py`
Very small logging helper.

Key function:

- `warn_once(msg)` — `lru_cache`-backed warning logger that ensures repeated warnings only appear once.

Widely used in schema/extractor/LLM code where repetitive warnings would otherwise be noisy.

### `src/kibad_llm/utils/path.py`
Path and directory-discovery helpers.

Key functions:

- `strip_filename_extension(file_path)`
- `get_directories_with_file(paths, filename, leafs_only)`

The latter is especially important for Hydra evaluation multiruns because it resolves nested run directories containing `job_return_value.json`.

---

## Configuration tree (`configs/`)

```text
configs/
├── evaluate.yaml
├── predict.yaml
├── dataset/
│   ├── faktencheck.yaml
│   ├── organism_trends_forest.yaml
│   ├── predictions_only.yaml
│   ├── predictions/
│   │   └── extraction_result.yaml
│   └── references/
│       ├── faktencheck_db_converted.yaml
│       └── organism_trends_weighted_vote_count_wald_literatur.yaml
├── experiment/
│   ├── evaluate/
│   │   ├── faktencheck_confusion_matrix.yaml
│   │   ├── faktencheck_core_f1_micro_flat.yaml
│   │   ├── faktencheck_f1_micro.yaml
│   │   ├── faktencheck_f1_micro_flat.yaml
│   │   ├── organism_trends_confusion_matrix.yaml
│   │   ├── organism_trends_f1_micro.yaml
│   │   ├── organism_trends_f1_micro_flat.yaml
│   │   └── prediction_errors.yaml
│   └── predict/
│       ├── _with_evidence.yaml
│       ├── faktencheck_core_fields_schema.yaml
│       ├── faktencheck_core_fields_schema_with_evidence.yaml
│       ├── faktencheck_single_schema.yaml
│       ├── faktencheck_two_schemata.yaml
│       ├── organism_trends.yaml
│       └── organism_trends_with_evidence.yaml
├── extractor/
│   ├── conditional_union.yaml
│   ├── repeat.yaml
│   ├── simple.yaml
│   ├── union.yaml
│   ├── aggregator/
│   │   ├── majority_vote.yaml
│   │   ├── single_majority_vote_multi_union.yaml
│   │   └── unanimous.yaml
│   ├── llm/
│   │   ├── gemma3_27b.yaml
│   │   ├── gemma3_27b_in_process.yaml
│   │   ├── gpt_5.yaml
│   │   ├── gpt_oss_20b.yaml
│   │   ├── gpt_oss_20b_in_process.yaml
│   │   ├── ministral_3_14b.yaml
│   │   ├── ministral_3_14b_in_process.yaml
│   │   ├── mistral_small_3_24b.yaml
│   │   ├── mistral_small_3_24b_in_process.yaml
│   │   ├── nemotron_nano_12b.yaml
│   │   ├── nemotron_nano_12b_in_process.yaml
│   │   ├── qwen3_30b.yaml
│   │   └── qwen3_30b_in_process.yaml
│   ├── prompt_template/
│   │   ├── default.yaml
│   │   ├── faktencheck_core_v1.yaml
│   │   ├── faktencheck_core_v1_with_evidence.yaml
│   │   ├── faktencheck_core_v1_with_evidence_and_persona.yaml
│   │   ├── organism_trends_v1.yaml
│   │   ├── organism_trends_v1_with_evidence.yaml
│   │   ├── organism_trends_v1_with_evidence_and_persona.yaml
│   │   └── schema_in_user_message.yaml
│   ├── request_parameters/
│   │   └── default.yaml
│   └── schema/
│       ├── faktencheck_all.yaml
│       ├── faktencheck_compounds_only.yaml
│       ├── faktencheck_compounds_simple.yaml
│       ├── faktencheck_core.yaml
│       ├── faktencheck_simple.yaml
│       ├── faktencheck_without_compounds.yaml
│       ├── none.yaml
│       ├── organism_trends.yaml
│       └── organism_trends_v1.yaml
├── hydra/
│   └── default.yaml
├── metric/
│   ├── confusion_matrix.yaml
│   ├── f1_micro.yaml
│   ├── f1_micro_single_field.yaml
│   └── prediction_errors.yaml
├── paths/
│   ├── default.yaml
│   ├── evaluate.yaml
│   └── predict.yaml
└── pdf_reader/
    └── pymupdf4llm.yaml
```

---

## How the Hydra configs fit together

## Root configs

### `configs/predict.yaml`
Top-level prediction composition.

Defaults:

- `paths: predict`
- `hydra: default`
- `pdf_reader: pymupdf4llm`
- `extractor: simple`
- `experiment/predict: null`

Main fields:

- `name`
- `seed`
- `pdf_directory`
- `output_dir`
- `output_file_name`
- `fast_dev_run`
- `extraction_caching`
- `store_text_in_predictions`
- `pdf_reader_num_proc`
- `extractor_num_proc`

This config defines the complete inference application surface.

### `configs/evaluate.yaml`
Top-level evaluation composition.

Defaults:

- `paths: evaluate`
- `hydra: default`
- `dataset: faktencheck`
- `metric: f1_micro`
- `experiment/evaluate: null`

Main fields:

- `name`
- `prediction_logs`
- custom `hydra.mode`, sweeper params, and callback behavior

This config supports both single evaluation runs and multirun evaluation over multiple prediction logs.

## Dataset configs

### `configs/dataset/faktencheck.yaml`
Creates the default merged evaluation dataset by combining:

- predictions from `dataset/predictions/extraction_result.yaml`
- references from `dataset/references/faktencheck_db_converted.yaml`

Target:

- `kibad_llm.dataset.utils.merge_references_into_predictions`

### `configs/dataset/organism_trends_forest.yaml`
Same merge pattern, but uses the organism-trends reference CSV loader.

### `configs/dataset/predictions_only.yaml`
Builds a dataset with predictions only and empty/default references. Used especially for metrics like `prediction_errors`.

### `configs/dataset/predictions/extraction_result.yaml`
Prediction loader config.

Target:

- `kibad_llm.dataset.prediction.load_with_metadata`

Top-level keys include `log`, `file`, `id_key`, `process_id`, `preprocess`.

### `configs/dataset/references/faktencheck_db_converted.yaml`
Reference loader config using:

- `kibad_llm.dataset.json.read_and_preprocess`

### `configs/dataset/references/organism_trends_weighted_vote_count_wald_literatur.yaml`
Reference loader config using:

- `kibad_llm.dataset.csv.read_organism_trends`

## Extractor configs

### Workflow configs

- `configs/extractor/simple.yaml`
  - target: `kibad_llm.extractors.extract_from_text_lenient`
  - partial callable
  - default single-call extraction

- `configs/extractor/repeat.yaml`
  - target: `kibad_llm.extractors.RepeatingExtractor`
  - repeated extraction with configurable repetition count and aggregation

- `configs/extractor/union.yaml`
  - target: `kibad_llm.extractors.UnionExtractor`
  - multi-setup extraction with per-setup overrides

- `configs/extractor/conditional_union.yaml`
  - target: `kibad_llm.extractors.ConditionalUnionExtractor`
  - sequential union with history propagation

### Aggregator configs

- `majority_vote.yaml` -> `aggregate_majority_vote`
- `unanimous.yaml` -> `aggregate_unanimous`
- `single_majority_vote_multi_union.yaml` -> `aggregate_single_majority_vote_multi_union`

These are configured as partial callables so the extractor classes can receive them directly.

### LLM configs

Two broad families exist:

1. **Externally hosted OpenAI-like endpoints**
   - targets such as `kibad_llm.llms.OpenAILikeVllm`
   - examples: `gpt_oss_20b.yaml`, `gemma3_27b.yaml`, `qwen3_30b.yaml`

2. **In-process vLLM instances**
   - target `kibad_llm.llms.VllmInProcess`
   - examples: `*_in_process.yaml`

There is also:

- `gpt_5.yaml` -> `kibad_llm.llms.OpenAI`

The configs specify model identifiers, API base URLs, auth keys, sampling settings, context window, retries, and backend-specific parameters.

### Prompt-template configs

All prompt templates provide some combination of:

- `system_message`
- `user_message`
- `schema_description_placeholder`
- `document_placeholder`

Variants encode task differences such as:

- Faktencheck vs organism trends
- evidence-aware prompts
- persona-enhanced prompts
- schema placement in user vs system message

### Schema configs

These call `.model_json_schema(by_alias=...)` on Pydantic models from `schema/types.py`.

Examples:

- `faktencheck_simple.yaml` -> `EcosystemStudyFeaturesSimple`
- `faktencheck_core.yaml` -> `EcosystemStudyFeaturesCoreFields`
- `organism_trends.yaml` -> `EcosystemStudyOrganismTrends`
- `none.yaml` -> no schema

## Experiment configs

Experiment configs package stable, named setups for reproducibility.

### Prediction experiments

Examples:

- `faktencheck_single_schema.yaml` — single-schema Faktencheck extraction.
- `faktencheck_two_schemata.yaml` — union extractor with two schema branches.
- `faktencheck_core_fields_schema.yaml` — core-field schema.
- `faktencheck_core_fields_schema_with_evidence.yaml` — core-field extraction with evidence-aware behavior.
- `organism_trends.yaml` / `organism_trends_with_evidence.yaml` — organism trend tasks.
- `_with_evidence.yaml` — helper config injecting extractor evidence settings.

### Evaluation experiments

Examples:

- `faktencheck_f1_micro.yaml`
- `faktencheck_f1_micro_flat.yaml`
- `faktencheck_core_f1_micro_flat.yaml`
- `faktencheck_confusion_matrix.yaml`
- `organism_trends_f1_micro.yaml`
- `organism_trends_f1_micro_flat.yaml`
- `organism_trends_confusion_matrix.yaml`
- `prediction_errors.yaml`

These mainly override the dataset and/or metric groups.

## Metric configs

- `f1_micro.yaml` -> `F1MicroMultipleFieldsMetric`
- `f1_micro_single_field.yaml` -> `F1MicroSingleFieldMetric`
- `confusion_matrix.yaml` -> `ConfusionMatrix`
- `prediction_errors.yaml` -> `ErrorCollector`

## Hydra and path configs

### `configs/hydra/default.yaml`
Configures:

- color logging,
- `SaveJobReturnValueCallback`,
- run directory pattern,
- multirun sweep directory pattern,
- multirun markdown/JSON behavior.

### `configs/paths/default.yaml`
Defines reusable path interpolations such as:

- `root_dir`
- `data_dir`
- `timestamp`
- `run_subdir`
- `output_dir`
- `save_dir`
- `log_dir`
- `work_dir`
- `prediction_save_dir`

### `configs/paths/predict.yaml` and `configs/paths/evaluate.yaml`
Small overrides of the default path layout for task-specific logging.

## PDF reader config

### `configs/pdf_reader/pymupdf4llm.yaml`
Default PDF reader target:

- `kibad_llm.preprocessing.read_pdf_as_markdown_via_pymupdf4llm`

---

## Tests

The test suite lives in `tests/` and mixes unit tests with integration tests.

## Test structure

```text
tests/
├── __init__.py
├── conftest.py
├── fixtures/
│   └── test_dont_write.py
├── integration/
│   ├── test_evaluation.py
│   ├── test_extractors.py
│   └── test_predict.py
└── unit/
    ├── __init__.py
    ├── test_db_converter.py
    ├── test_preprocessing.py
    ├── dataset/
    │   ├── test_csv.py
    │   └── test_prediction.py
    ├── extractors/
    │   ├── __init__.py
    │   ├── test_aggregation_utils.py
    │   └── test_base.py
    ├── hydra_callbacks/
    │   └── test_save_job_return_value.py
    ├── llms/
    │   └── test_openai.py
    ├── metrics/
    │   ├── __init__.py
    │   ├── test_base.py
    │   ├── test_confusion_matrix.py
    │   └── test_f1.py
    └── schema/
        ├── __init__.py
        ├── test_types.py
        └── test_utils.py
```

## Test infrastructure

### `tests/conftest.py`
Provides common fixtures and Hydra composition helpers.

Key elements:

- `WRITE_FIXTURE_DATA = False` safety switch
- `test_dont_write_fixture_data()` guard test
- `cfg_global(...)` helper for composing Hydra configs with test-specific overrides
- `cfg_predict(...)` fixture for per-test prediction configs

A notable feature is that tests override `cfg.paths.root_dir` with `PROJ_ROOT` and clear Hydra global state after use.

## Integration tests

### `tests/integration/test_predict.py`
End-to-end prediction tests.

Covers:

- prediction over fixture PDFs,
- `fast_dev_run`,
- specific error-path cases such as very long PDFs and missing response content.

It checks prediction structure and selected error properties rather than deterministic extraction content.

### `tests/integration/test_extractors.py`
Parameterized integration tests over all extractor configs found in `configs/extractor/`.

Covers:

- Hydra instantiation of extractor configs,
- special setup for union-style extractors,
- execution on fixture markdown,
- top-level result structure,
- expected error-list semantics.

### `tests/integration/test_evaluation.py`
End-to-end evaluation tests over all metric configs.

Covers:

- dynamic metric selection,
- expected outputs for `f1_micro_single_field`, `confusion_matrix`, `f1_micro`, and `prediction_errors`,
- complete `evaluate(cfg)` execution.

## Unit tests

### `tests/unit/test_db_converter.py`
Tests formatting behavior of `db_converter.format_result`.

### `tests/unit/test_preprocessing.py`
Tests PDF-to-markdown reading through the preprocessing layer.

### `tests/unit/dataset/test_csv.py`
Tests CSV-based organism-trend loading.

### `tests/unit/dataset/test_prediction.py`
Tests prediction loading with metadata.

### `tests/unit/extractors/test_aggregation_utils.py`
Extensive coverage of all aggregation behaviors:

- hashability conversion,
- majority vote,
- list-majority logic,
- unanimity,
- mixed aggregation,
- error conditions and type mismatches.

### `tests/unit/extractors/test_base.py`
Focused tests for metadata stripping logic in `extractors.base`.

### `tests/unit/hydra_callbacks/test_save_job_return_value.py`
Substantial tests for callback behavior:

- initialization,
- single-run saves,
- multirun aggregation,
- identifier generation,
- override handling.

### `tests/unit/llms/test_openai.py`
Tests OpenAI strict-schema conversion logic in detail.

### `tests/unit/metrics/test_base.py`
Tests normalization to sets in `MetricWithPrepareEntryAsSet`.

### `tests/unit/metrics/test_confusion_matrix.py`
Tests confusion-matrix counting, reset logic, reserved-label guards, and markdown logging.

### `tests/unit/metrics/test_f1.py`
Tests single-field and multi-field micro-F1 calculations plus formatting behavior.

### `tests/unit/schema/test_types.py`
Parameterized validation tests over all schema models and compound models.

### `tests/unit/schema/test_utils.py`
Broad tests for:

- schema-description generation,
- terminal wrapping with metadata,
- idempotence,
- handling of refs, arrays, unions, and custom content keys.

### `tests/fixtures/test_dont_write.py`
Additional safety test ensuring fixture-writing mode is not accidentally enabled.

Overall, the test suite is strongest around schema handling, aggregation logic, metrics, and Hydra callback behavior.

---

## `pyproject.toml`

`pyproject.toml` is the central packaging, dependency, and tool configuration file.

## Package metadata

- build backend: `hatchling`
- project name: `kibad-llm`
- version: `0.1.0`
- Python requirement: `>=3.10.0`
- readme: `README.md`

The human-facing metadata is still placeholder-like in places:

- description: `Add your description here`
- authors: `Your name (or your organization/company/team)`

So operationally the file is mature, but the package metadata is not fully polished yet.

## Runtime dependencies

The dependencies reveal the project’s core technology stack:

- data handling: `pandas`, `datasets`
- database: `psycopg2-binary`
- config/parsing: `pyyaml`, `python-dotenv`
- HTTP/downloads: `requests`, `retry`
- PDF parsing: `pymupdf4llm`, `pdfplumber`
- LLM integration: `llama-index-llms-openai-like`, `llama-index-llms-openai`, `vllm`
- schema validation: `jsonschema`
- CLI / logging / infra: `typer`, `loguru`, `tqdm`, `gitpython`, `hydra-core`, `hydra-colorlog`
- docs / analysis: `mkdocs`, `jupyter`, `matplotlib`, `tabulate`

The package also includes many typing stub packages, indicating an emphasis on type checking.

## Development dependency group

`[dependency-groups].cicd` contains:

- `pytest`
- `pytest-xdist`
- `pytest-cov`
- `typeguard`
- `pre-commit`
- `mypy`

This matches the CI and code-quality workflow described in the README.

## Tool configuration

The file also centralizes config for:

- `pytest`
- `coverage`
- `black`
- `isort`
- `flake8`
- `codespell`
- `bandit`
- `mdformat`
- `nbqa`
- `mypy`

Notable details:

- `pytest` uses `typeguard-packages = "kibad_llm"`.
- coverage is restricted to the package source.
- `black` line length is `99`.
- `flake8` excludes large/generated directories such as `data`, `logs`, `models`, `notebooks`.
- `codespell` skips large swaths of generated or schema-heavy content.
- `mypy` checks both `src` and `tests`, with overrides for third-party packages lacking full typing.

In short, `pyproject.toml` is both the build manifest and the repository’s main static-quality control center.

---

## `.pre-commit-config.yaml`

The pre-commit setup is comprehensive and aligned with the `pyproject.toml` tool settings.

## Global behavior

- excludes `data/` and `tests/fixtures/` from hook processing.

## Hook groups

### Housekeeping hooks (`pre-commit-hooks`)
Includes checks such as:

- trailing whitespace
- end-of-file fixer
- YAML/TOML validation
- debug statement detection
- private key detection
- shebang checks
- case-conflict checks
- large-file checks

### Formatting and modernization

- `black`
- `isort`
- `pyupgrade --py310-plus`

### Static analysis and security

- `flake8` with `flake8-pyproject`
- `bandit` with TOML support
- `mypy` via a local hook executed as `uv run mypy --config=pyproject.toml`

### Documentation / spelling

- `mdformat` with GitHub-flavored markdown, table support, frontmatter, and pyproject integration
- `codespell`

### Notebook hygiene

- `nbstripout`
- `nbqa-black`
- `nbqa-isort`
- `nbqa-flake8`

This setup indicates that the project treats code, markdown, and notebooks as first-class maintainable artifacts.

---

## Relationship between code, configs, and tests

A useful way to read the project is:

1. **Schemas in `schema/types.py`** define what can be extracted.
2. **Schema utilities in `schema/utils.py`** turn those schemas into prompt guidance and metadata-aware variants.
3. **LLM wrappers in `llms/`** define how prompts are executed against different backends.
4. **Extractor logic in `extractors/base.py`** translates text and schema into structured predictions.
5. **Extractor workflow configs in `configs/extractor/`** decide whether extraction is single-shot, repeated, unioned, or conditional.
6. **`predict.py`** applies that extractor at dataset scale.
7. **Dataset loaders in `dataset/` plus dataset configs in `configs/dataset/`** merge predictions with references.
8. **Metrics in `metrics/` plus metric configs in `configs/metric/`** compute task-specific evaluation outputs.
9. **`evaluate.py`** runs the evaluation loop.
10. **Hydra callback logic** writes out reproducible experiment artifacts.
11. **Tests** verify the individual layers and several end-to-end paths.

This layered structure is one of the strengths of the repository: most complexity is isolated into reusable modules, while Hydra handles composition.

---

## Strengths and notable design choices

### Strengths

- Clear separation of runtime pipeline, LLM backend, schema definition, and evaluation.
- Heavy use of Hydra for reproducible experiment composition.
- Thoughtful multirun result handling via a custom Hydra callback.
- Strong schema utility layer, especially for evidence-aware extraction.
- Good unit-test coverage for the most failure-prone logic:
  - aggregation,
  - schema wrapping,
  - metrics,
  - callback output generation.

### Notable design choices

- Prediction uses Hugging Face `datasets` rather than ad hoc loops, enabling caching and multiprocessing.
- Evaluation metrics treat many fields as set-valued classification targets.
- Schema-driven extraction is central; prompt templates are schema-aware rather than free-form.
- Metadata/evidence wrapping is implemented in a generic JSON-schema transformation layer rather than being hardcoded per schema.

### Practical caveats visible from the codebase

- Some packaging metadata is still generic placeholder text.
- The README’s “Project Organization” section appears to be inherited from a template and is no longer an exact description of the real code structure.
- The package is config-rich; understanding actual behavior requires reading both Python and Hydra config composition.

---

## Recommended reading order for a new contributor

1. `README.md`
2. `pyproject.toml`
3. `configs/predict.yaml` and `configs/evaluate.yaml`
4. `src/kibad_llm/predict.py`
5. `src/kibad_llm/evaluate.py`
6. `src/kibad_llm/extractors/base.py`
7. `src/kibad_llm/llms/base.py` and the concrete LLM backends
8. `src/kibad_llm/schema/types.py` and `src/kibad_llm/schema/utils.py`
9. `src/kibad_llm/dataset/*`
10. `src/kibad_llm/metrics/*`
11. `src/kibad_llm/hydra_callbacks/save_job_return_value.py`
12. `tests/`, especially integration tests and schema/aggregation tests

---

## Summary

`kibad-llm` is a research/engineering codebase for structured biodiversity- and ecosystem-related information extraction from PDFs using LLMs. Its core identity is not just “LLM inference,” but **schema-driven extraction with Hydra-composed experiment management and evaluation**.

The repository’s most important technical pillars are:

- `predict.py` and `evaluate.py` as the two application entry points,
- `extractors/base.py` as the core extraction engine,
- `schema/types.py` as the domain model,
- `schema/utils.py` as the schema-to-prompt and evidence-wrapping layer,
- `llms/` as the backend abstraction,
- `metrics/` as the evaluation layer,
- `hydra_callbacks/save_job_return_value.py` as the experiment artifact system,
- `configs/` as the composition layer tying everything together.

For anyone extending the project, the critical skill is understanding the interaction between **Hydra config composition**, **schema definitions**, and **extractor behavior**.

