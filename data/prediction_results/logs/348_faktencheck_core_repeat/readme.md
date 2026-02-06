# 348_faktencheck_core_repeat

See #348 for details.

## notebook parameters

### just this experiment

```python
NAME = "348_faktencheck_core_repeat"

FILL_NA = {"prediction.overrides.extractor.n": 3}

METRICS = ["f1", "recall", "precision"]
# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm", "prediction.overrides.extractor.n"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": ["prediction.overrides.extractor/llm", "prediction.overrides.extractor.n"],
    # add any more arguments passed to pd.DataFrame.plot
}
```

![metrics_f1.svg](metrics_f1.svg)
![metrics_recall.svg](metrics_recall.svg)
![metrics_precision.svg](metrics_precision.svg)
![errors.svg](errors.svg)
![errors_detail.svg](errors_detail.svg)

### comparison with baseline
baseline: [327_faktencheck_core_with_persona](../327_faktencheck_core_with_persona/)

```python
NAME = "348_faktencheck_core_repeat"

SUBDIR = ["evaluate", "../327_faktencheck_core_with_persona/evaluate"]

FILE_NAME_PREFIX = "baseline_"

FILL_NA = {"prediction.overrides.extractor.n": 3, "prediction.overrides.extractor": "simple"}

METRICS = ["f1", "recall", "precision"]
# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm", "prediction.overrides.extractor.n", "prediction.overrides.extractor"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": ["prediction.overrides.extractor.n", "prediction.overrides.extractor"],
    # add any more arguments passed to pd.DataFrame.plot
    "create_subplot_for_each": "metric",
    #"set_missing_values_to_zero": True,
    "subplot_columns": 2,
}
```
#### f1

![baseline_comparison_metrics_f1.svg](baseline_comparison_metrics_f1.svg)
![baseline_comparison_metrics_f1_detail.svg](baseline_comparison_metrics_f1_detail.svg)

#### recall

![baseline_comparison_metrics_recall.svg](baseline_comparison_metrics_recall.svg)
![baseline_comparison_metrics_recall_detail.svg](baseline_comparison_metrics_recall_detail.svg)

#### precision

![baseline_comparison_metrics_precision.svg](baseline_comparison_metrics_precision.svg)
![baseline_comparison_metrics_precision_detail.svg](baseline_comparison_metrics_precision_detail.svg)

#### errors

![baseline_comparison_errors.svg](baseline_comparison_errors.svg)
![baseline_comparison_errors_detail.svg](baseline_comparison_errors_detail.svg)


### comparison with previous repeat experiment
previous repeat experiment: [88_repeat_faktencheck_core](../88_repeat_faktencheck_core/)

```python
NAME = "348_faktencheck_core_repeat"

SUBDIR = [
    # take only n=3 runs from current experiment
    "evaluate/multiruns/2026-02-06_15-15-35",
    "evaluate/multiruns/2026-02-06_15-16-29", 
    "../88_repeat_faktencheck_core/evaluate",
]

FILE_NAME_PREFIX = "previous_comparison_"

METRICS = ["f1", "recall", "precision"]
# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm", "prediction.overrides.name"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": ["prediction.overrides.name"],
    # add any more arguments passed to pd.DataFrame.plot
    #"create_subplot_for_each": "metric",
    #"set_missing_values_to_zero": True,
    #"subplot_columns": 2,
}
```

![previous_comparison_metrics_f1.svg](previous_comparison_metrics_f1.svg)
![previous_comparison_metrics_precision.svg](previous_comparison_metrics_precision.svg)
![previous_comparison_metrics_recall.svg](previous_comparison_metrics_recall.svg)
![previous_comparison_errors.svg](previous_comparison_errors.svg)
![previous_comparison_errors_detail.svg](previous_comparison_errors_detail.svg)