# 525_faktencheck_core_bestconfig_testset

Evaluation of the best setup (with chunking) from [519_faktencheck_core](../519_faktencheck_core), but on the
true test set (/ds/text/kiba-d/splits/test). 

## Prediction

Base for the commands is https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/logs/397_faktencheck_core_v1_for_chunking 

### gpt_oss_20b

```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB"  \
-u "-m kibad_llm.predict \
name=525_faktencheck_core_bestconfig_testset \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/splits/test \
extractor/llm=gpt_oss_20b_in_process \
seed=42,1337,7331 \
--multirun"
```

```sh
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Mon Jun 22 01:22:26 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hennig/cache/uv -m kibad_llm.predict name=525_faktencheck_core_bestconfig_testset experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/splits/test extractor/llm=gpt_oss_20b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_ddaff36f-7799-4709-a477-9faccf1c7566
>>> GIT_REF (none; using current working tree)
=============================================
```

Saved to `logs/525_faktencheck_core_bestconfig_testset/predict/multiruns/2026-06-23_00-38-05/`

### gemma3_27b

**IMPORTANT: Running this requires a huggingface token**

```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB"  \
-u "-m kibad_llm.predict \
name=525_faktencheck_core_bestconfig_testset \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/splits/test \
extractor/llm=gemma3_27b_in_process \
seed=42,1337,7331 \
--multirun"
```

```sh
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Tue Jun 23 08:48:10 AM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hennig/cache/uv -m kibad_llm.predict name=525_faktencheck_core_bestconfig_testset experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/splits/test extractor/llm=gemma3_27b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_256e87a8-2fb8-4dbe-b753-7613ff8afbe2
>>> GIT_REF (none; using current working tree)
=============================================
```

Saved to `logs/525_faktencheck_core_bestconfig_testset/predict/multiruns/2026-06-23_10-23-46/`

### qwen3_30b

```sh
./run_in_process.sh -t "2-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB"  \
-u "-m kibad_llm.predict \
name=525_faktencheck_core_bestconfig_testset \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/splits/test \
extractor/llm=qwen3_30b_in_process \
seed=42,1337,7331 \
--multirun"
```

```sh
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 2-00:00:00
>>> SUBMITTED Tue Jun 23 08:48:56 AM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hennig/cache/uv -m kibad_llm.predict name=525_faktencheck_core_bestconfig_testset experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/splits/test extractor/llm=qwen3_30b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_007b3ab8-a95d-4845-8dad-74fcad788840
>>> GIT_REF (none; using current working tree)
=============================================
```

Saved to `logs/525_faktencheck_core_bestconfig_testset/predict/multiruns/2026-06-23_10-24-03/`

### mistral_small_3_24b

```sh
./run_in_process.sh -t "3-00:00:00" -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB"  \
-u "-m kibad_llm.predict \
name=525_faktencheck_core_bestconfig_testset \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/splits/test \
extractor/llm=mistral_small_3_24b_in_process \
seed=42,1337,7331 \
--multirun"
```

```sh
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Tue Jun 23 08:49:23 AM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hennig/cache/uv -m kibad_llm.predict name=525_faktencheck_core_bestconfig_testset experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/splits/test extractor/llm=mistral_small_3_24b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_9f5c1acb-8734-413d-98c9-ea3f764d37d8
>>> GIT_REF (none; using current working tree)
=============================================
```

Saved to `logs/525_faktencheck_core_bestconfig_testset/predict/multiruns/2026-06-23_10-25-16/`

### gpt_5

**IMPORTANT: Running this requires an openai token**  
This run does not need a gpu and is hence run with `-ng 0.

```sh
./run_in_process.sh -t "3-00:00:00" -ng 0 -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch" \
-u "-m kibad_llm.predict \
name=525_faktencheck_core_bestconfig_testset \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/splits/test \
extractor/llm=gpt_5 \
seed=42 \
--multirun"
```

```sh
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Tue Jun 23 01:24:16 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/hennig/cache/uv -m kibad_llm.predict name=525_faktencheck_core_bestconfig_testset experiment/predict=faktencheck_core_fields_schema_with_chunking pdf_directory=/ds/text/kiba-d/splits/test extractor/llm=gpt_5 seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_f6567664-5b6a-4808-91e2-90e133299fb5
>>> GIT_REF (none; using current working tree)
=============================================
```

**Note:** Stopped after first seed due to costs (USD  $195) and time constraints (pass through 500 docs took 59 hrs)

Saved to `logs/525_faktencheck_core_bestconfig_testset/predict/multiruns/2026-06-23_13-25-01/`

## Evaluation

### F1, P, R
Base for the command is https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/logs/519_faktencheck_core

```sh
uv run -m kibad_llm.evaluate \
name=525_faktencheck_core_bestconfig_testset \
experiment/evaluate=faktencheck_core_f1_micro_flat \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[\
logs/525_faktencheck_core_bestconfig_testset/predict \
] \
--multirun
```

Saved to `logs/525_faktencheck_core_bestconfig_testset/evaluate/multiruns/2026-06-29_14-39-29`

### Errors

```sh
uv run -m kibad_llm.evaluate \
name=525_faktencheck_core_bestconfig_testset \
experiment/evaluate=prediction_errors \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
prediction_logs=[\
logs/525_faktencheck_core_bestconfig_testset/predict \
] \
--multirun
```

Saved to `logs/525_faktencheck_core_bestconfig_testset/evaluate/multiruns/2026-06-30_15-39-52`

## Outcome

### F1, P, R
The results in this folder can serve as a basis for the [Journal experiments](https://github.com/DFKI-NLP/kibad-llm/issues/521),
namely for the Faktencheck core schema plots:

- ![Figure/Table 1 "main pipeline results": F1 scores for the best configuration (prompt+chunking+...)](figures/faktencheck_core_f1_micro_flat-ALL/f1.svg) 
- ![Figure/Table 2: "detail results - precision and recall" - same plots as above, but with precision scores instead of F1](figures/faktencheck_core_f1_micro_flat-ALL/precision.svg)
- ![Figure/Table 2: "detail results - precision and recall" - same plots as above, but with recall scores instead of F1](figures/faktencheck_core_f1_micro_flat-ALL/recall.svg)
- ![Figure/Table 3: "detail results - schema elements" for all models and the best configuration - Biodiversity Level](figures/faktencheck_core_f1_micro_flat-biodiversity_level/f1.svg)
- ![Figure/Table 3: "detail results - schema elements" for all models and the best configuration - Ecosystem type category](figures/faktencheck_core_f1_micro_flat-ecosystem_type.category/f1.svg)
- ![Figure/Table 3: "detail results - schema elements" for all models and the best configuration - Ecosystem type term](figures/faktencheck_core_f1_micro_flat-ecosystem_type.term/f1.svg)
- ![Figure/Table 3: "detail results - schema elements" for all models and the best configuration - Habitat](figures/faktencheck_core_f1_micro_flat-habitat/f1.svg)
- ![Figure/Table 3: "detail results - schema elements" for all models and the best configuration - Taxa species group](figures/faktencheck_core_f1_micro_flat-taxa.species_group/f1.svg)

Micro-averaged F1 scores on the test set range from 0.43 (Mistral, Gemma) to 0.50 (GPT OSS, Qwen), with GPT5 performing slightly
worse than the top two models at F1=0.47. This is most likely due to the large amount of MissingResponseContent errors (449 chunks
out of 2723, 16.5%), which might have lowered recall considerably. Compared to the dev set with the correct reference
data, F1 scores are significantly lower. GPT5 achieved 0.71 on the dev set, the other models approx from 0.56 - 0.63 (See 
https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/logs/519_faktencheck_core) 
Compared to the dev set with the original, uncorrected reference data (see 
https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/logs/542_faktencheck_core), which range
from 0.34 (Mistral, Gemma) to 0.42 (GPT OSS, Qwen), the results are slightly better. 

Precision is quite low at 0.39 for GPT OSS and Qwen, and 0.28 for Mistral, recall is high at 0.8 for Mistral and GPT5,
and around 0.71 for the other models.
Regarding individual fields, biodiversity level was identified with an F1 between 0.41 and 0.45, ecosystem_type.category
between 0.43 and 0.5, ecosytem_type.term at 0.23-0.33, habitat at 0.65-0.71 and taxa.species_group at 0.41-0.53.


### Errors
- ![No errors, vs Run 519](figures/prediction_errors-total/no_error.svg)
- ![Total errors, vs Run 519](figures/prediction_errors-total/with_error.svg)
- ![JSONDecode errors, vs Run 519](figures/prediction_errors-details/JSONDecodeError.svg)
- ![MissingResponseContent errors, vs Run 519](figures/prediction_errors-details/MissingResponseContentError.svg)

GPT5 has a significant amount of MissingResponseContent errors, 449 out of 2723 chunks failed with this error. Thse
are 16.5% of the total chunks.