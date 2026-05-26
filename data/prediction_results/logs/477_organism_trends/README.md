# 477_organism_trends

This adds confusion matrizes for the predictions from [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking).

## Evaluation

### Conditional variable and trend
- base elements: Hauptgruppe_RoteListen, Lebensraum

```Bash
uv run -m kibad_llm.evaluate \
name=477_organism_trends \
experiment/evaluate=organism_trends_confusion_matrix_conditional_variable_and_trend \
prediction_logs=logs/380_organism_trends/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: `logs/477_organism_trends/evaluate/multiruns/2026-05-26_10-52-23`

### Conditional variable only
- base elements: Hauptgruppe_RoteListen, Lebensraum

```Bash
uv run -m kibad_llm.evaluate \
name=477_organism_trends \
experiment/evaluate=organism_trends_confusion_matrix_conditional_variable_only \
prediction_logs=logs/380_organism_trends/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: `logs/477_organism_trends/evaluate/multiruns/2026-05-26_10-57-22`

### Conditional trend only
- base elements: Hauptgruppe_RoteListen, Lebensraum, Variable

```Bash
uv run -m kibad_llm.evaluate \
name=477_organism_trends \
experiment/evaluate=organism_trends_confusion_matrix_conditional_trend_only \
prediction_logs=logs/380_organism_trends/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: `logs/477_organism_trends/evaluate/multiruns/2026-05-26_10-58-25`