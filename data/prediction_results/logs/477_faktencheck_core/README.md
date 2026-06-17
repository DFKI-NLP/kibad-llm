# 477_faktencheck_core

This adds confusion matrizes for the predictions from [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking).

## Evaluation
- on flattened data
- config file: [configs/experiment/evaluate/faktencheck_core_confusion_matrix_multiple_fields_flat.yaml](../../../../configs/experiment/evaluate/faktencheck_core_confusion_matrix_multiple_fields_flat.yaml)

```Bash
uv run -m kibad_llm.evaluate \
name=477_faktencheck_core \
experiment/evaluate=faktencheck_core_confusion_matrix_multiple_fields_flat \
prediction_logs=logs/397_faktencheck_core_v1_for_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```
