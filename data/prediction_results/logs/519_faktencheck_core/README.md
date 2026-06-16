# 519_faktencheck_core

evaluation on only the best setup (with chunking, corrected gold data, full dev set) from [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking)

## f1

```
uv run -m kibad_llm.evaluate \
name=519_faktencheck_core \
experiment/evaluate=faktencheck_core_f1_micro_flat \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_19-02-33,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_19-06-32,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_20-34-00] \
--multirun
```

result location: `logs/519_faktencheck_core/evaluate/multiruns/2026-06-16_15-19-32`

## errors

```
uv run -m kibad_llm.evaluate \
name=519_faktencheck_core \
experiment/evaluate=prediction_errors \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_19-02-33,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_19-06-32,logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-08_20-34-00] \
--multirun
```

result location: `logs/519_faktencheck_core/evaluate/multiruns/2026-06-16_14-57-41`

TODO: add figures to the readme
