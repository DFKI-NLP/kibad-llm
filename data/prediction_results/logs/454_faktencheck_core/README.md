# 454_faktencheck_core

True positive, false positive, and false negative predictions on the [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking) data for the `biodiversity_level` field.

eval command:
```bash
uv run -m kibad_llm.evaluate \
name=454_faktencheck_core \
experiment/evaluate=faktencheck_tpfpfn \
metric.field=biodiversity_level \
prediction_logs=logs/397_faktencheck_core_v1_for_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

example result: [job_return_value.md](evaluate/multiruns/2026-05-15_22-43-01/0/job_return_value.md)