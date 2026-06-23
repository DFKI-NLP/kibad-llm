# 440_gpt_oss_120b_faktencheck_core

Evaluate `openai/gpt-oss-120b` with the chunking extractor on the Faktencheck core fields schema
(`faktencheck_core_fields_schema_with_chunking`), using the in-process vLLM config.
Goal: establish a performance baseline for a 120B-scale open-weights model and compare it against
smaller models already evaluated on this experiment.

## Config

Config file: `configs/extractor/llm/gpt_oss_120b_in_process.yaml`

### Non-default parameters

- `vllm_kwargs.max_model_len=65536`: overrides the vLLM default to cap the context window.
  `131072` requires ~5 GiB KV cache but only ~3.3 GiB is available on cluster GPUs, causing
  vLLM to refuse to start. `65536` was confirmed working on serv-3341 (2026-06-11).
  See [issue #440](https://github.com/DFKI-NLP/kibad-llm/issues/440) for test details.

## Prediction

```bash
./run_in_process.sh -pa "H100-SLT,H100-Trails,H100,H200,B200" -ng 1 \
  -u "-m kibad_llm.predict \
       name=440_gpt_oss_120b_faktencheck_core \
       experiment/predict=faktencheck_core_fields_schema_with_chunking \
       extractor/llm=gpt_oss_120b_in_process \
       pdf_directory=/ds/text/kiba-d/dev-set-100 \
       seed=42,1337,7331 \
       --multirun"
```

Result location: `logs/440_gpt_oss_120b_faktencheck_core/predict/multiruns/<timestamp>`

## Evaluation

### F1 scores

Run from within `data/prediction_results/`:

```bash
uv run -m kibad_llm.evaluate \
  name=440_gpt_oss_120b_faktencheck_core \
  experiment/evaluate=faktencheck_core_f1_micro_flat \
  prediction_logs=logs/440_gpt_oss_120b_faktencheck_core/predict/multiruns/<timestamp> \
  dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
  "metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group]" \
  --multirun
```

Result location: `logs/440_gpt_oss_120b_faktencheck_core/evaluate/multiruns/<timestamp>`

### Comparison with other models

### Errors

```bash
uv run -m kibad_llm.evaluate \
  name=440_gpt_oss_120b_faktencheck_core \
  experiment/evaluate=prediction_errors \
  hydra.callbacks.save_job_return.multirun_show_file_contents=null \
  prediction_logs=logs/440_gpt_oss_120b_faktencheck_core/predict/multiruns/<timestamp> \
  --multirun
```

Result location: `logs/440_gpt_oss_120b_faktencheck_core/evaluate/multiruns/<timestamp>`

## Outcome
