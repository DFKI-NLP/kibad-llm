# 454_faktencheck_core

This run collects true-positive, false-positive, and false-negative predictions for the
`biodiversity_level` field on
[397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking) predictions.

It uses `experiment/evaluate=faktencheck_tpfpfn`, which evaluates predictions with
`TpFpFnCollector` and keeps the matched, spurious, and missed entries instead of only reporting
aggregate scores. The stored output is grouped by record id so individual documents can be
inspected easily.

## Reproduce

```bash
uv run -m kibad_llm.evaluate \
name=454_faktencheck_core \
experiment/evaluate=faktencheck_tpfpfn \
metric.field=biodiversity_level \
prediction_logs=logs/397_faktencheck_core_v1_for_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

## Result files

- The multirun output is stored under `evaluate/multiruns/2026-05-15_22-43-01/`.
- Each `job_return_value.md` file contains the tp/fp/fn entries for one run.
- Example result (Qwen 3 30B):
  [evaluate/multiruns/2026-05-15_22-43-01/0/job_return_value.md](evaluate/multiruns/2026-05-15_22-43-01/0/job_return_value.md)
