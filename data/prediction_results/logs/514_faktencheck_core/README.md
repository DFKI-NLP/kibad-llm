# 514_faktencheck_core

Confusion matrices until now ... TODO: describe actual problem
This adds corrected confusion matrizes for the predictions from [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking).

## Evaluation
- on flattened data
- config file: [configs/experiment/evaluate/faktencheck_core_confusion_matrix_multiple_fields_flat.yaml](../../../../configs/experiment/evaluate/faktencheck_core_confusion_matrix_multiple_fields_flat.yaml)

```Bash
uv run -m kibad_llm.evaluate \
name=514_faktencheck_core \
experiment/evaluate=faktencheck_core_confusion_matrix_multiple_fields_flat \
prediction_logs=logs/397_faktencheck_core_v1_for_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: `logs/514_faktencheck_core/evaluate/multiruns/2026-06-09_15-00-34`

See [figures/](figures/) for generated confusion matrices for gpt-oss-20b and qwen-3-30b.
