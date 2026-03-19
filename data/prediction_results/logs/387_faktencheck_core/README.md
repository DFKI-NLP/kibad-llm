# 387_faktencheck_core

## comparison vs. corrected reference data

- This uses the predictions from [380_faktencheck_core](../380_faktencheck_core) and compares them to the original reference data ([faktencheck-db-converted_2025-11-05.jsonl](../../../interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl)) as well as the corrected reference data ([faktenscheck_core_corrected_reference_null.jsonl](../../../interim/faktencheck-db/faktenscheck_core_corrected_reference_null.jsonl)).
- We evaluate only the fields that were corrected in the reference data, i.e., `habitat`, `biodiversity_level`, `ecosystem_type.term`, and `taxa.species_group` (*not* `ecosystem_type.category`, `taxa.german_name`, `taxa.scientific_name` from the Faktencheck core schema).

### eval command:

```
uv run -m kibad_llm.evaluate \
name=387_faktencheck_core  \
experiment/evaluate=faktencheck_core_f1_micro_flat \
dataset.references.file=../interim/faktencheck-db/faktencheck-db-converted_2025-11-05.jsonl,../interim/faktencheck-db/faktenscheck_core_corrected_reference_null.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,taxa.species_group] \
prediction_logs=logs/380_faktencheck_core/predict \
+hydra.callbacks.save_job_return.multirun_markdown_group_by=[prediction.overrides.extractor/llm,overrides.dataset.references.file] \
--multirun
```

### notebook parameters
```python
NAME = "387_faktencheck_core"

SUBDIR = ["evaluate"]

FILE_NAME_PREFIX = "baseline_"

METRICS = ["f1", "recall", "precision"]
# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm", "overrides.dataset.references.file"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": ["overrides.dataset.references.file"],
    # add any more arguments passed to pd.DataFrame.plot
    "create_subplot_for_each": "metric",
    #"set_missing_values_to_zero": True,
    "subplot_columns": 2,
}
```


### f1
![baseline_comparison_metrics_f1.svg](baseline_comparison_metrics_f1.svg)

<details>
<summary>see detailed metrics</summary>

![baseline_comparison_metrics_f1_detail.svg](baseline_comparison_metrics_f1_detail.svg)

</details>

### recall
![baseline_comparison_metrics_recall.svg](baseline_comparison_metrics_recall.svg)

<details>
<summary>see detailed metrics</summary>

![baseline_comparison_metrics_recall_detail.svg](baseline_comparison_metrics_recall_detail.svg)

</details>

### precision
![baseline_comparison_metrics_precision.svg](baseline_comparison_metrics_precision.svg)

<details>
<summary>see detailed metrics</summary>

![baseline_comparison_metrics_precision_detail.svg](baseline_comparison_metrics_precision_detail.svg)

</details>