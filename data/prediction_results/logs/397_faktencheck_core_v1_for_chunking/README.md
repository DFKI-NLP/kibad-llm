# 397_faktencheck_core_v1_for_chunking

## inference

## inference with small chunks
this approach hopes to find strength in avoiding the needle-in-the-haystack problem.

the commands are based on #277.

all runs use [this commit](https://github.com/DFKI-NLP/kibad-llm/pull/397/changes/81d3de5422270e9a0394c3560def173b4373b2f2).

### gpt_oss_20b
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=gpt_oss_20b_in_process \
seed=42,1337,7331 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 03:46:23 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=gpt_oss_20b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_c601d96d-4b6e-43b1-a757-a6e09a124647
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-49-56`

This run has been saved to the same dir as gemma3_27b.

### gemma3_27b
**IMPORTANT: Running this requires a huggingface token**
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=gemma3_27b_in_process \
seed=42,1337,7331 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 03:47:11 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=gemma3_27b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_3fbc1379-cbfd-457b-89be-075cbdd74425
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-49-56`

This run has been saved to the same dir as gpt-oss.

### qwen3_30b
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=qwen3_30b_in_process \
seed=42,1337,7331 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 03:47:41 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=qwen3_30b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_d4a27f3a-153c-48da-9ccb-ac9aeed76b0a
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22`

### mistral_small_3_24b
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=mistral_small_3_24b_in_process \
seed=42,1337,7331 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 03:48:00 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=mistral_small_3_24b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_c895bb57-003b-4c08-8abb-cd061ab36af9
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-51-01`

This run had some errors and was terminated before the third seed could be fully executed. Hence, there is a second run:

```
./run_in_process.sh -t "3-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200" -r 81d3de5422270e9a0394c3560def173b4373b2f2 -u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=mistral_small_3_24b_in_process \
seed=42,1337,7331 \
--multirun"
```

```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Wed Apr  8 12:54:13 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=mistral_small_3_24b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_441a373b-2848-4913-9bbd-c518e5486260
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

### gpt_5
**IMPORTANT: Running this requires an openai token**  
This run does not need a gpu and is hence run with `-ng 0`.
```sh
./run_in_process.sh -t "3-00:00:00" -ng 0 -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=gpt_5 \
seed=42,1337,7331 \
--multirun"
```

```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr  2 04:39:58 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=gpt_5 seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_eef94652-f99e-4609-b938-9829381dbee6
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44`

This run took too long and was terminated prematurely. Only the first two seeds have been evaluated. Due to the exorbitant money and time consumption, this will not be reevaluated and instead used as is.

## evaluation using small chunks

```
# in this order:
# gpt-oss: done
# gemma-3: done - SAME DIR AS GPT-OSS
# qwen-3: done
# mistral-small-3: only the first two seeds done, the third was terminated due to time. also some storage full error.
# gpt-5: only the first two seeds done, the third was terminated due to time.
```

### f1 - on all documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=faktencheck_core_f1_micro_flat \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-49-56,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-51-01,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44\
] \
--multirun
```

Saved to [2026-04-08_13-32-47](evaluate/multiruns/2026-04-08_13-32-47)

### f1 - on previously working documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=faktencheck_core_f1_micro_flat \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-49-56,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-51-01,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44\
] \
+dataset.predictions.skip_by_id=[2E9XWUUE,2EUNPHDZ,2P53UVJA,2RXMDX8I,3LGPK6BL,3WEEGFGW,46RX4AEN,4YXRYRJC,4Z67G9T5,5SIYLM9W,6D23L7B5,6G2THNDX,7DSY6RMR,84QQ9F5S,885FDL5Z] \
--multirun
```

Saved to [2026-04-08_13-33-04](evaluate/multiruns/2026-04-08_13-33-04)

### errors - on all documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=prediction_errors \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-49-56,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-51-01,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44\
] \
--multirun
```

Saved to [2026-04-08_13-33-15](evaluate/multiruns/2026-04-08_13-33-15)

### errors - on previously working documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=prediction_errors \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-49-56,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-50-22,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_15-51-01,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-41-44\
] \
+dataset.predictions.skip_by_id=[2E9XWUUE,2EUNPHDZ,2P53UVJA,2RXMDX8I,3LGPK6BL,3WEEGFGW,46RX4AEN,4YXRYRJC,4Z67G9T5,5SIYLM9W,6D23L7B5,6G2THNDX,7DSY6RMR,84QQ9F5S,885FDL5Z] \
--multirun
```

Saved to [2026-04-08_13-33-28](evaluate/multiruns/2026-04-08_13-33-28)

# evaluation with large chunks
this evaluation aims to create similar conditions to the other extractors for better comparability.

the commands are based on #277.

all runs use [this commit](https://github.com/DFKI-NLP/kibad-llm/pull/397/changes/81d3de5422270e9a0394c3560def173b4373b2f2).
### gpt_oss_20b
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=gpt_oss_20b_in_process \
seed=42,1337,7331 \
extractor.max_char_buffer=175000 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 04:47:16 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=gpt_oss_20b_in_process seed=42,1337,7331 extractor.max_char_buffer=175000 --multirun
>>> JOB_NAME kiba-d_6c63c275-2b36-4b2f-bc4f-5a5ce7ff82f4
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-02`

### gemma3_27b
**IMPORTANT: Running this requires a huggingface token**
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=gemma3_27b_in_process \
seed=42,1337,7331 \
extractor.max_char_buffer=175000 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 04:47:56 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=gemma3_27b_in_process seed=42,1337,7331 extractor.max_char_buffer=175000 --multirun
>>> JOB_NAME kiba-d_f01b5887-bcf0-4475-bbab-b1542a1e39c0
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-15`

### qwen3_30b
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=qwen3_30b_in_process \
seed=42,1337,7331 \
extractor.max_char_buffer=175000 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 04:48:20 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=qwen3_30b_in_process seed=42,1337,7331 extractor.max_char_buffer=175000 --multirun
>>> JOB_NAME kiba-d_57defed2-37c5-4b53-ba43-232dd518697f
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-29`

### mistral_small_3_24b
```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=mistral_small_3_24b_in_process \
seed=42,1337,7331 \
extractor.max_char_buffer=175000 \
--multirun"
```
 
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Thu Apr  2 04:49:02 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=mistral_small_3_24b_in_process seed=42,1337,7331 extractor.max_char_buffer=175000 --multirun
>>> JOB_NAME kiba-d_f05ece31-ef79-4e3a-a7c1-d666b9b18915
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-56-31`

### gpt_5
**IMPORTANT: Running this requires an openai token**  
This run does not need a gpu and is hence run with `-ng 0`.
```sh
./run_in_process.sh -t "3-00:00:00" -ng 0 -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch" -sr \
-r 81d3de5422270e9a0394c3560def173b4373b2f2 \
-u "-m kibad_llm.predict \
name=397_faktencheck_core_v1_for_chunking \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-100 \
extractor/llm=gpt_5 \
seed=42,1337,7331 \
extractor.max_char_buffer=175000 \
--multirun"
```

```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr  2 04:49:24 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hmeinhof/cache/uv -m kibad_llm.predict name=397_faktencheck_core_v1_for_chunking experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-100 extractor/llm=gpt_5 seed=42,1337,7331 extractor.max_char_buffer=175000 --multirun
>>> JOB_NAME kiba-d_04fc4171-08b5-4ee5-856e-9010c1d0f45c
>>> GIT_REF 81d3de5422270e9a0394c3560def173b4373b2f2
=============================================
```

Saved to `logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-50-38`

## Evaluation using large chunks
```
# in this order:
# gpt-oss: done
# gemma-3: done
# qwen-3: done
# mistral-small-3: done
# gpt-5: done
```

### f1 - on all documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=faktencheck_core_f1_micro_flat \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-02,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-15,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-29,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-56-31,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-50-38\
] \
--multirun
```

Saved to [2026-04-08_13-36-22](evaluate/multiruns/2026-04-08_13-36-22)

### f1 - on previously working documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=faktencheck_core_f1_micro_flat \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
dataset.references.file=../interim/faktencheck-db/faktenscheck_core_corrected.jsonl \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-02,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-15,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-29,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-56-31,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-50-38\
] \
+dataset.predictions.skip_by_id=[2E9XWUUE,2EUNPHDZ,2P53UVJA,2RXMDX8I,3LGPK6BL,3WEEGFGW,46RX4AEN,4YXRYRJC,4Z67G9T5,5SIYLM9W,6D23L7B5,6G2THNDX,7DSY6RMR,84QQ9F5S,885FDL5Z] \
--multirun
```

Saved to [2026-04-08_13-36-36](evaluate/multiruns/2026-04-08_13-36-36)

### errors - on all documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=prediction_errors \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-02,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-15,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-29,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-56-31,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-50-38\
] \
--multirun
```

Saved to [2026-04-08_13-37-04](evaluate/multiruns/2026-04-08_13-37-04)

### errors - on previously working documents

```
uv run -m kibad_llm.evaluate \
name=397_faktencheck_core_v1_for_chunking \
experiment/evaluate=prediction_errors \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-02,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-15,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-54-29,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-56-31,\
logs/397_faktencheck_core_v1_for_chunking/predict/multiruns/2026-04-02_16-50-38\
] \
+dataset.predictions.skip_by_id=[2E9XWUUE,2EUNPHDZ,2P53UVJA,2RXMDX8I,3LGPK6BL,3WEEGFGW,46RX4AEN,4YXRYRJC,4Z67G9T5,5SIYLM9W,6D23L7B5,6G2THNDX,7DSY6RMR,84QQ9F5S,885FDL5Z] \
--multirun
```

Saved to [2026-04-08_13-37-19](evaluate/multiruns/2026-04-08_13-37-19)
