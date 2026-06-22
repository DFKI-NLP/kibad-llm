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

```

Saved to ``

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

```

Saved to ``

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

```

Saved to ``

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

```

Saved to ``

### gpt_5

**IMPORTANT: Running this requires an openai token**  
This run does not need a gpu and is hence run with `-ng 0.

```sh
./run_in_process.sh -t "3-00:00:00" -ng 0 -pa "H100-SLT,H100-Trails,H100,H200,B200,A100-80GB,batch" \
-u "-m kibad_llm.predict \
name=525_faktencheck_core_bestconfig_testset \
experiment/predict=faktencheck_core_fields_schema_with_chunking \
pdf_directory=/ds/text/kiba-d/splits/test \
extractor/llm=gpt_5_in_process \
seed=42,1337,7331 \
--multirun"
```

```sh

```

Saved to ``

## Evaluation

Base for the command is https://github.com/DFKI-NLP/kibad-llm/tree/main/data/prediction_results/logs/519_faktencheck_core

```sh
uv run -m kibad_llm.evaluate \
name=525_faktencheck_core_bestconfig_testset \
experiment/evaluate=faktencheck_core_f1_micro_flat \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
metric.fields=[habitat,biodiversity_level,ecosystem_type.term,ecosystem_type.category,taxa.species_group] \
prediction_logs=[\
logs/525_faktencheck_core_bestconfig_testset/\
] \
--multirun
```

```sh
```

Saved to ``

