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

result location: TODO

<details>
<summary>click to see results</summary>

TODO

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

result location: TODO

<details>
<summary>click to see results</summary>

TODO

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

result location: TODO

<details>
<summary>click to see results</summary>

TODO

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

result location: TODO

<details>
<summary>click to see results</summary>

TODO

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