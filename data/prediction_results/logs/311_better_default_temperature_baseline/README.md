# 311_better_default_temperature

evaluate setting temperature, top_p, top_k and repetition penalty to recommended values per model
see https://github.com/DFKI-NLP/kibad-llm/issues/311 / https://github.com/DFKI-NLP/kibad-llm/pull/322 for details
 - models: gpt_oss_20b, gemma3_27b, qwen3_30b, mistral_small_3_24b, and nemotron_nano_12b_v2 (all in-process)
 - `temperature=0.0`
 - faktencheck core schema + detect evidence
 - with `return_reasoning=true`



## Evaluation Notebook Parameters
```python
NAME = "311_better_default_temperature_baseline"
METRICS_DIR_PATTERN = "evaluate/**/2026-01-26_03-05-47/"
ERRORS_DIR_PATTERN = "evaluate/**/2026-01-26_03-07-48/"
# used to group the data
INDEX_COLUMNS = ["overrides.extractor/llm"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": "overrides.extractor/llm",
    # add any more arguments passed to pd.DataFrame.plot
}
```

![metrics.svg](metrics.svg)
![errors.svg](errors.svg)
![errors_detail.svg](errors_detail.svg)

details below

## Inference

```
./run_in_process.sh -pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-u "-m kibad_llm.predict \
name=311_better_default_temperature_baseline \
experiment/predict=faktencheck_core_fields_schema_with_evidence \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor.return_reasoning=true \
extractor/llm=gpt_oss_20b_in_process,gemma3_27b_in_process,qwen3_30b_in_process,nemotron_nano_12b_in_process,mistral_small_3_24b_in_process \
seed=42,1337,7331 \
--multirun"
```

[2026-01-24 02:19:22,800][HYDRA] Contents of /netscratch/binder/projects/kibad-llm/logs/311_better_default_temperature_baseline/predict/multiruns/2026-01-23_15-36-01/job_return_value.md:

<details>
<summary>click to see content</summary>

|                                                        | branch   | commit_hash                              | is_dirty   | output_file                                                                                                             | output_file_absolute                                                                                                                                          | overrides.experiment/predict                 | overrides.extractor.return_reasoning   | overrides.extractor/llm        | overrides.name                          | overrides.pdf_directory     |   overrides.seed |   time_extraction |   time_pdf_conversion |
|:-------------------------------------------------------|:---------|:-----------------------------------------|:-----------|:------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------|:---------------------------------------|:-------------------------------|:----------------------------------------|:----------------------------|-----------------:|------------------:|----------------------:|
| extractor/llm=gemma3_27b_in_process#seed=1337          | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_18-39-10_953067/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_18-39-10_953067/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | gemma3_27b_in_process          | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             1337 |           1171.69 |            0.00279479 |
| extractor/llm=gemma3_27b_in_process#seed=42            | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_18-17-37_871565/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_18-17-37_871565/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | gemma3_27b_in_process          | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |               42 |           1177.43 |            0.002606   |
| extractor/llm=gemma3_27b_in_process#seed=7331          | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_19-00-04_947040/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_19-00-04_947040/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | gemma3_27b_in_process          | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             7331 |           1174.12 |            0.00285013 |
| extractor/llm=gpt_oss_20b_in_process#seed=1337         | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_16-31-24_198356/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_16-31-24_198356/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | gpt_oss_20b_in_process         | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             1337 |           3127    |            0.00351188 |
| extractor/llm=gpt_oss_20b_in_process#seed=42           | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_15-36-03_747336/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_15-36-03_747336/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | gpt_oss_20b_in_process         | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |               42 |           3147.93 |            0.00348547 |
| extractor/llm=gpt_oss_20b_in_process#seed=7331         | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_17-24-26_293566/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_17-24-26_293566/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | gpt_oss_20b_in_process         | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             7331 |           3136.27 |            0.00282958 |
| extractor/llm=mistral_small_3_24b_in_process#seed=1337 | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-24_00-08-29_427127/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-24_00-08-29_427127/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | mistral_small_3_24b_in_process | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             1337 |           3816.76 |            0.00651497 |
| extractor/llm=mistral_small_3_24b_in_process#seed=42   | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_23-03-02_317682/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_23-03-02_317682/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | mistral_small_3_24b_in_process | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |               42 |           3813.69 |            0.00368887 |
| extractor/llm=mistral_small_3_24b_in_process#seed=7331 | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-24_01-13-57_888376/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-24_01-13-57_888376/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | mistral_small_3_24b_in_process | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             7331 |           3817.52 |            0.0025578  |
| extractor/llm=nemotron_nano_12b_in_process#seed=1337   | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_22-27-17_288378/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_22-27-17_288378/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | nemotron_nano_12b_in_process   | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             1337 |           1030.05 |            0.00301912 |
| extractor/llm=nemotron_nano_12b_in_process#seed=42     | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_22-09-16_585406/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_22-09-16_585406/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | nemotron_nano_12b_in_process   | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |               42 |           1030.35 |            0.00283951 |
| extractor/llm=nemotron_nano_12b_in_process#seed=7331   | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_22-45-09_183196/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_22-45-09_183196/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | nemotron_nano_12b_in_process   | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             7331 |           1029.75 |            0.00364807 |
| extractor/llm=qwen3_30b_in_process#seed=1337           | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_20-17-13_589198/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_20-17-13_589198/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | qwen3_30b_in_process           | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             1337 |           3251.25 |            0.00270458 |
| extractor/llm=qwen3_30b_in_process#seed=42             | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_19-21-01_133940/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_19-21-01_133940/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | qwen3_30b_in_process           | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |               42 |           3258.61 |            0.00311493 |
| extractor/llm=qwen3_30b_in_process#seed=7331           | main     | 96efc8cbaf31910ffab43b74a2a0b89184634a01 | False      | predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_21-12-33_308488/predictions.jsonl.gz | /netscratch/binder/projects/kibad-llm/predictions/311_better_default_temperature_baseline/2026-01-23_15-36-01/2026-01-23_21-12-33_308488/predictions.jsonl.gz | faktencheck_core_fields_schema_with_evidence | True                                   | qwen3_30b_in_process           | 311_better_default_temperature_baseline | /ds/text/kiba-d/dev-set-100 |             7331 |           3337.45 |            0.00319516 |

</details>

## evaluate

### f1

```
uv run -m kibad_llm.evaluate \
name=311_better_default_temperature_baseline  \
experiment/evaluate=faktencheck_core_f1_micro_flat \
prediction_logs=logs/311_better_default_temperature_baseline/predict/multiruns/2026-01-23_15-36-01 \
+hydra.callbacks.save_job_return.multirun_markdown_group_by=overrides.extractor/llm \
--multirun
```

[2026-01-26 03:06:00,720][HYDRA] Saving job_return in /netscratch/binder/projects/kibad-llm/logs/311_better_default_temperature_baseline/evaluate/multiruns/2026-01-26_03-05-47/job_return_value.json
[2026-01-26 03:06:00,753][HYDRA] Saving job_return in /netscratch/binder/projects/kibad-llm/logs/311_better_default_temperature_baseline/evaluate/multiruns/2026-01-26_03-05-47/job_return_value.md
/netscratch/binder/cache/uv-venvs/kibad-llm/lib/python3.12/site-packages/hydra/_internal/callbacks.py:28: UserWarning: Callback SaveJobReturnValueCallback.on_multirun_end raised ValueError: len(index) != len(labels)
  warnings.warn(

**MARKDOWN CREATION FAILED (but json should be fine, so the eval notebook should also work)**
EDIT: the notebook works fine with the eval data


### errors
```
uv run -m kibad_llm.evaluate \
name=311_better_default_temperature_baseline \
experiment/evaluate=prediction_errors \
prediction_logs=logs/311_better_default_temperature_baseline/predict/multiruns/2026-01-23_15-36-01 \
+hydra.callbacks.save_job_return.multirun_markdown_group_by=overrides.extractor/llm \
--multirun
```

[2026-01-26 03:07:59,247][HYDRA] Saving job_return in /netscratch/binder/projects/kibad-llm/logs/311_better_default_temperature_baseline/evaluate/multiruns/2026-01-26_03-07-48/job_return_value.json
[2026-01-26 03:07:59,258][HYDRA] Saving job_return in /netscratch/binder/projects/kibad-llm/logs/311_better_default_temperature_baseline/evaluate/multiruns/2026-01-26_03-07-48/job_return_value.md
/netscratch/binder/cache/uv-venvs/kibad-llm/lib/python3.12/site-packages/hydra/_internal/callbacks.py:28: UserWarning: Callback SaveJobReturnValueCallback.on_multirun_end raised ValueError: len(index) != len(labels)
  warnings.warn(

**MARKDOWN CREATION FAILED (but json should be fine, so the eval notebook should also work)**
EDIT: the notebook works fine with the eval data