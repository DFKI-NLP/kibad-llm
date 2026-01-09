This folder contains the logs and predictions of the baseline experiments
conducted with the faktencheck_core_schema_v1, across the following LLMs:

- gpt_oss_20b
- qwen3_30b

See Issue https://github.com/DFKI-NLP/kibad-llm/issues/159  for more documentation.

All LLMs were tested with 3 runs and result averaging, their logs and predictions
are therefore multiruns.

When using the evaluation notebook (`plot_multirun_evaluation.ipynb`) with this data, use 
```
FILL_NA = {"overrides.extractor/llm": "gpt_oss_20b"}
``` 
since this is the default and was not explicitly set.