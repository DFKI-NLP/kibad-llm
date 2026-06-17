# 514_faktencheck_core

Confusion matrices until now ... TODO: describe actual problem
This adds corrected confusion matrizes for the best setup predictions (see [519_faktencheck_core](../519_faktencheck_core)) from [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking).

## Evaluation
- on flattened data
- config file: [configs/experiment/evaluate/faktencheck_core_confusion_matrix_multiple_fields_flat.yaml](../../../../configs/experiment/evaluate/faktencheck_core_confusion_matrix_multiple_fields_flat.yaml)

```Bash
uv run -m kibad_llm.evaluate \
name=514_faktencheck_core \
experiment/evaluate=faktencheck_core_confusion_matrix_multiple_fields_flat \
prediction_logs=[logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_19-02-33,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_19-06-32,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_20-34-00] \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: `logs/514_faktencheck_core/evaluate/multiruns/2026-06-17_12-36-29`

See [figures/](figures/) for generated confusion matrices for gpt-oss-20b, qwen-3-30b and gpt5.
