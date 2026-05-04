# 428_organism_trends_with_chunking

similar to [380_organism_trends](../380_organism_trends) + evaluation as in [422_organism_trends](../422_organism_trends), but with chunking as in [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking)

## Details

### Inference

- based on [380_organism_trends](../380_organism_trends)
- adapted according to [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking)
- no gpt5 for now

#### gpt_oss_20b_in_process

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-t "3-00:00:00" \
-u "-m kibad_llm.predict \
name=428_organism_trends_with_chunking \
experiment/predict=organism_trends_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC \
extractor/llm=gpt_oss_20b_in_process \
seed=42,1337,7331 \
--multirun"
```
started at `screen -r kibad-llm-1`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 03:10:22 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=gpt_oss_20b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_8bfad5fe-9ca8-4560-a6dd-567920e31ce8
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2869103 queued and waiting for resources
```

result location: `/netscratch/binder/projects/kibad-llm/logs/428_organism_trends_with_chunking/predict/multiruns/2026-04-30_15-10-47`

<details>
<summary>click to see results</summary>

|           | branch                                               | commit_hash                              | is_dirty   | output_file                                                                                                    | output_file_absolute                                                                                                                                 | overrides.experiment/predict   | overrides.extractor/llm   | overrides.name                    | overrides.pdf_directory          |   overrides.seed |   slurm_job_id |   time_end |   time_extraction |   time_pdf_conversion |   time_start |
|:----------|:-----------------------------------------------------|:-----------------------------------------|:-----------|:---------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------|:--------------------------|:----------------------------------|:---------------------------------|-----------------:|---------------:|-----------:|------------------:|----------------------:|-------------:|
| seed=1337 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-10-47/2026-04-30_20-05-04_813422/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-10-47/2026-04-30_20-05-04_813422/predictions.jsonl | organism_trends_with_chunking  | gpt_oss_20b_in_process    | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             1337 |        2869103 | 1777589542 |           17174.7 |            0.00486733 |   1777572304 |
| seed=42   | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-10-47/2026-04-30_15-10-48_127341/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-10-47/2026-04-30_15-10-48_127341/predictions.jsonl | organism_trends_with_chunking  | gpt_oss_20b_in_process    | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |               42 |        2869103 | 1777572304 |           17485.9 |            0.00393253 |   1777554648 |
| seed=7331 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-10-47/2026-05-01_00-52-23_188169/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-10-47/2026-05-01_00-52-23_188169/predictions.jsonl | organism_trends_with_chunking  | gpt_oss_20b_in_process    | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             7331 |        2869103 | 1777606469 |           16873.3 |            0.00294652 |   1777589543 |

</details>


#### gemma3_27b_in_process

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-t "3-00:00:00" \
-u "-m kibad_llm.predict \
name=428_organism_trends_with_chunking \
experiment/predict=organism_trends_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC \
extractor/llm=gemma3_27b_in_process \
seed=42,1337,7331 \
--multirun"
```
started at `screen -r kibad-llm-2`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 03:10:44 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=gemma3_27b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_b9d8bae5-fe54-4b6a-8cfc-1421d2870aac
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2869104 queued and waiting for resources
```

result location: `/netscratch/binder/projects/kibad-llm/logs/428_organism_trends_with_chunking/predict/multiruns/2026-04-30_15-50-26`

<details>
<summary>click to see results</summary>

|           | branch                                               | commit_hash                              | is_dirty   | output_file                                                                                                    | output_file_absolute                                                                                                                                 | overrides.experiment/predict   | overrides.extractor/llm   | overrides.name                    | overrides.pdf_directory          |   overrides.seed |   slurm_job_id |   time_end |   time_extraction |   time_pdf_conversion |   time_start |
|:----------|:-----------------------------------------------------|:-----------------------------------------|:-----------|:---------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------|:--------------------------|:----------------------------------|:---------------------------------|-----------------:|---------------:|-----------:|------------------:|----------------------:|-------------:|
| seed=1337 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-50-26/2026-05-01_00-00-24_225439/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-50-26/2026-05-01_00-00-24_225439/predictions.jsonl | organism_trends_with_chunking  | gemma3_27b_in_process     | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             1337 |        2869104 | 1777615377 |           28875.9 |            0.00437259 |   1777586424 |
| seed=42   | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-50-26/2026-04-30_15-50-27_426199/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-50-26/2026-04-30_15-50-27_426199/predictions.jsonl | organism_trends_with_chunking  | gemma3_27b_in_process     | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |               42 |        2869104 | 1777586424 |           29239.7 |            0.0160239  |   1777557027 |
| seed=7331 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-50-26/2026-05-01_08-02-58_241590/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-50-26/2026-05-01_08-02-58_241590/predictions.jsonl | organism_trends_with_chunking  | gemma3_27b_in_process     | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             7331 |        2869104 | 1777643631 |           28157.4 |            0.0132321  |   1777615378 |

</details>


#### qwen3_30b_in_process

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-t "3-00:00:00" \
-u "-m kibad_llm.predict \
name=428_organism_trends_with_chunking \
experiment/predict=organism_trends_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC \
extractor/llm=qwen3_30b_in_process \
seed=42,1337,7331 \
--multirun"
```

started at `screen -r kibad-llm-3`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 03:11:11 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=qwen3_30b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_3109ef2e-d7f8-4c37-a6dc-166241b47f10
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2869105 queued and waiting for resources
```

result location: `/netscratch/binder/projects/kibad-llm/logs/428_organism_trends_with_chunking/predict/multiruns/2026-04-30_15-51-30`

<details>
<summary>click to see results</summary>

|           | branch                                               | commit_hash                              | is_dirty   | output_file                                                                                                    | output_file_absolute                                                                                                                                 | overrides.experiment/predict   | overrides.extractor/llm   | overrides.name                    | overrides.pdf_directory          |   overrides.seed |   slurm_job_id |   time_end |   time_extraction |   time_pdf_conversion |   time_start |
|:----------|:-----------------------------------------------------|:-----------------------------------------|:-----------|:---------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------|:--------------------------|:----------------------------------|:---------------------------------|-----------------:|---------------:|-----------:|------------------:|----------------------:|-------------:|
| seed=1337 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-51-30/2026-04-30_22-43-48_815233/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-51-30/2026-04-30_22-43-48_815233/predictions.jsonl | organism_trends_with_chunking  | qwen3_30b_in_process      | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             1337 |        2869105 | 1777605681 |           23790.8 |            0.00418444 |   1777581828 |
| seed=42   | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-51-30/2026-04-30_15-51-30_470332/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-51-30/2026-04-30_15-51-30_470332/predictions.jsonl | organism_trends_with_chunking  | qwen3_30b_in_process      | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |               42 |        2869105 | 1777581828 |           24619.4 |            0.00318383 |   1777557090 |
| seed=7331 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-51-30/2026-05-01_05-21-21_301951/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-51-30/2026-05-01_05-21-21_301951/predictions.jsonl | organism_trends_with_chunking  | qwen3_30b_in_process      | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             7331 |        2869105 | 1777629993 |           24252.4 |            0.00281874 |   1777605681 |

</details>


#### mistral_small_3_24b_in_process

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-t "3-00:00:00" \
-u "-m kibad_llm.predict \
name=428_organism_trends_with_chunking \
experiment/predict=organism_trends_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC \
extractor/llm=mistral_small_3_24b_in_process \
seed=42,1337,7331 \
--multirun"
```

started at `screen -r kibad-llm-4`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 03:11:32 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=mistral_small_3_24b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_e589d490-7c11-4149-af7b-4e8583013b98
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2869107 queued and waiting for resources
```

result location: `/netscratch/binder/projects/kibad-llm/logs/428_organism_trends_with_chunking/predict/multiruns/2026-04-30_15-59-49`

<details>
<summary>click to see results</summary>

|           | branch                                               | commit_hash                              | is_dirty   | output_file                                                                                                    | output_file_absolute                                                                                                                                 | overrides.experiment/predict   | overrides.extractor/llm        | overrides.name                    | overrides.pdf_directory          |   overrides.seed |   slurm_job_id |   time_end |   time_extraction |   time_pdf_conversion |   time_start |
|:----------|:-----------------------------------------------------|:-----------------------------------------|:-----------|:---------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------|:-------------------------------|:-------------------------------|:----------------------------------|:---------------------------------|-----------------:|---------------:|-----------:|------------------:|----------------------:|-------------:|
| seed=1337 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-59-49/2026-05-01_08-26-53_886051/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-59-49/2026-05-01_08-26-53_886051/predictions.jsonl | organism_trends_with_chunking  | mistral_small_3_24b_in_process | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             1337 |        2869107 | 1777676206 |           59304.2 |            0.0109318  |   1777616813 |
| seed=42   | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-59-49/2026-04-30_15-59-50_254622/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-59-49/2026-04-30_15-59-50_254622/predictions.jsonl | organism_trends_with_chunking  | mistral_small_3_24b_in_process | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |               42 |        2869107 | 1777616813 |           59030.4 |            0.00872045 |   1777557590 |
| seed=7331 | prediction_results/add-organism_trends_with_chunking | 096090bf929c361a9164f099a077d2621612fdca | False      | predictions/428_organism_trends_with_chunking/2026-04-30_15-59-49/2026-05-02_00-56-46_893538/predictions.jsonl | /netscratch/binder/projects/kibad-llm/predictions/428_organism_trends_with_chunking/2026-04-30_15-59-49/2026-05-02_00-56-46_893538/predictions.jsonl | organism_trends_with_chunking  | mistral_small_3_24b_in_process | 428_organism_trends_with_chunking | /ds/text/kiba-d/dev-set-Wald-WVC |             7331 |        2869107 | 1777735470 |           59188.7 |            0.00470726 |   1777676206 |

</details>

### Evaluation
 - based on [380_organism_trends](../380_organism_trends) + [422_organism_trends](../422_organism_trends)

#### metrics
 - all without `Untergruppe_RoteListen`

##### flattened
```Bash
uv run -m kibad_llm.evaluate \
name=428_organism_trends_with_chunking \
experiment/evaluate=organism_trends_f1_micro_flat \
prediction_logs=logs/428_organism_trends_with_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: TODO

<details>
<summary>click to see results</summary>

TODO

</details>

##### full compounds

```Bash
uv run -m kibad_llm.evaluate \
name=428_organism_trends_with_chunking \
experiment/evaluate=organism_trends_f1_micro \
prediction_logs=logs/428_organism_trends_with_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: TODO

<details>
<summary>click to see results</summary>

TODO

</details>

##### base elements

```Bash
uv run -m kibad_llm.evaluate \
name=428_organism_trends_with_chunking \
experiment/evaluate=organism_trends_f1_micro_base_entries \
prediction_logs=logs/428_organism_trends_with_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: TODO

<details>
<summary>click to see results</summary>

TODO

</details>

##### `Antwortvariable` conditioned on base elements

```Bash
uv run -m kibad_llm.evaluate \
name=428_organism_trends_with_chunking \
experiment/evaluate=organism_trends_f1_micro_conditional_variable_only \
prediction_logs=logs/428_organism_trends_with_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: TODO

<details>
<summary>click to see results</summary>

TODO

</details>

##### `Antwortvariable` & `Trend` conditioned on base elements

```Bash
uv run -m kibad_llm.evaluate \
name=428_organism_trends_with_chunking \
experiment/evaluate=organism_trends_f1_micro_conditional_variable_and_trend \
prediction_logs=logs/428_organism_trends_with_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: TODO

<details>
<summary>click to see results</summary>

TODO

</details>

#### errors

```Bash
uv run -m kibad_llm.evaluate \
name=428_organism_trends_with_chunking \
experiment/evaluate=prediction_errors \
prediction_logs=logs/428_organism_trends_with_chunking/predict \
hydra.callbacks.save_job_return.multirun_show_file_contents=null \
--multirun
```

result location: TODO

<details>
<summary>click to see results</summary>

TODO

</details>