# 380_organism_trends

## comparison with baseline

```python
NAME = "380_organism_trends"

SUBDIR = ["evaluate", "../333_organism_trends_with_persona/evaluate"]

FILE_NAME_PREFIX = "baseline_"

MAP_VALUES = {
    "prediction.job_return_value.branch": {
        "organism-trends-with-persona": "baseline",
        "build_schema_description/improve-newline-handling": "improve-newline-handling",
    }
}

METRICS = ["f1", "recall", "precision"]
# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm", "prediction.job_return_value.branch"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": ["prediction.job_return_value.branch"],
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

### errors
![baseline_comparison_errors.svg](baseline_comparison_errors.svg)

<details>
<summary>see detailed metrics</summary>

![baseline_comparison_errors_detail.svg](baseline_comparison_errors_detail.svg)

</details>
