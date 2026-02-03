# 333_organism_trends_with_persona

This folder contains the logs of the organism trend experiments with an improved prompt template (v1),
evidence retrieval, and a persona, across the following LLMs:

- gpt_oss_20b
- gemma3_27b
- qwen3_30b
- mistral_small_3_24b
- gpt_5

See https://github.com/DFKI-NLP/kibad-llm/issues/333 and https://github.com/DFKI-NLP/kibad-llm/pull/338 for more documentation.

## Notebook Parameters

### Just this experiment

```python
NAME = "333_organism_trends_with_persona"

# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": "prediction.overrides.extractor/llm",
    # add any more arguments passed to pd.DataFrame.plot
}
```

![metrics.svg](metrics.svg)
![errors.svg](errors.svg)
![errors_detail.svg](errors_detail.svg)

### comparison with baseline
```python
NAME = "333_organism_trends_with_persona"
METRICS_DIR_PATTERN = [
    "evaluate/**/2026-02-02_XXX/",
    "../255_organism_trend_baseline_no_evi/evaluate/**/2026-02-02_11-36-38/",
]
ERRORS_DIR_PATTERN = [
    "evaluate/**/2026-02-02_XXX/",
    "../255_organism_trend_baseline_no_evi/evaluate/**/2026-02-02_11-37-16/",
]

# used to group the data
INDEX_COLUMNS = ["prediction.overrides.extractor/llm"]
PLOT_KWARGS = {
    # can be either "metric" or one of the INDEX_COLUMNS (or multiple of them)
    "xgroup": "prediction.overrides.extractor/llm",
    # add any more arguments passed to pd.DataFrame.plot
    "create_subplot_for_each": "metric",
    "subplot_columns": 2,
}
FILL_NA = {}
```



![comparison_metrics.svg](comparison_metrics.svg)
![comparison_metrics_details.svg](comparison_metrics_details.svg)

![comparison_errors.svg](comparison_errors.svg)
![comparison_errors_detail.svg](comparison_errors_detail.svg)

## Inference
