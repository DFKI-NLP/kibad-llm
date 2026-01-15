This folder contains the logs and predictions of the baseline experiments
conducted with the faktencheck_core_schema_v1, across the following LLMs:

- gpt_oss_20b
- qwen3_30b
- gemma3_27b
- ministral_3_14b
- mistral_small_3_24b
- nemotron_nano_12b
- gpt_5 (single run to save costs)

See Issue https://github.com/DFKI-NLP/kibad-llm/issues/159  for more documentation.

All LLMs were tested with 3 runs and result averaging (except `gpt_5`), their logs and predictions
are therefore multiruns.

When using the evaluation notebook (`plot_multirun_evaluation.ipynb`) with this data, use 
```python
NAME = "159_core_schema_baseline"
METRICS_DIR_PATTERN = ["evaluate/**/2026-01-08_16-46-51/", "evaluate/**/2026-01-08_16-44-31/"]
ERRORS_DIR_PATTERN = "evaluate/**/2026-01-09_12-07-41/"
# since this is the default and was not explicitly set
FILL_NA = {"overrides.extractor/llm": "gpt_oss_20b"}
```