# 397_faktencheck_core_v1_for_chunking

## inference

TODO @Hugo: add inference command here

## f1

### on all

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=faktencheck_core_f1_micro_flat \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[logs/380_faktencheck_core/predict,logs/397_faktencheck_core_v1_for_chunking/predict] \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```
out dir: [2026-03-30_13-44-22](evaluate/multiruns/2026-03-30_13-44-22)


### on previously working pdfs only

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=faktencheck_core_f1_micro_flat \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[logs/380_faktencheck_core/predict,logs/397_faktencheck_core_v1_for_chunking/predict] \
+dataset.predictions.skip_by_id=[2E9XWUUE,2EUNPHDZ,2P53UVJA,2RXMDX8I,3LGPK6BL,3WEEGFGW,46RX4AEN,4YXRYRJC,4Z67G9T5,5SIYLM9W,6D23L7B5,6G2THNDX,7DSY6RMR,84QQ9F5S,885FDL5Z] \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```
out dir: [2026-03-30_13-45-40](evaluate/multiruns/2026-03-30_13-45-40)

## prediction_errors

### on all

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=prediction_errors \
prediction_logs=[logs/380_faktencheck_core/predict,logs/397_faktencheck_core_v1_for_chunking/predict] \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```
out dir: [2026-03-30_14-07-05](evaluate/multiruns/2026-03-30_14-07-05)


### on previously working pdfs only

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=prediction_errors \
prediction_logs=[logs/380_faktencheck_core/predict,logs/397_faktencheck_core_v1_for_chunking/predict] \
+dataset.predictions.skip_by_id=[2E9XWUUE,2EUNPHDZ,2P53UVJA,2RXMDX8I,3LGPK6BL,3WEEGFGW,46RX4AEN,4YXRYRJC,4Z67G9T5,5SIYLM9W,6D23L7B5,6G2THNDX,7DSY6RMR,84QQ9F5S,885FDL5Z] \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

out dir: [2026-03-30_14-07-24](evaluate/multiruns/2026-03-30_14-07-24)