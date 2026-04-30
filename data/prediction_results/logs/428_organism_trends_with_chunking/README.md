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
startet at `screen -r kibad-llm-1`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 02:07:04 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=gpt_oss_20b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_056d68a0-669d-4904-8a5e-5fc8567a005d
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2868963 queued and waiting for resources
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
startet at `screen -r kibad-llm-2`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 02:16:50 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=gemma3_27b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_f1083c98-dd6e-4b32-a54e-62145e3742f4
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2868974 queued and waiting for resources
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

startet at `screen -r kibad-llm-3`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 02:17:41 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=qwen3_30b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_b5dfd426-0d2f-4e72-a212-9f9a101002ff
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2868975 queued and waiting for resources
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

startet at `screen -r kibad-llm-4`
```
=============================================
>>> USING PARTITION H100-SLT,H100-Trails,H100,A100-80GB
>>> MAX TIME 3-00:00:00
>>> SUBMITTED Thu Apr 30 02:18:34 PM CEST 2026
>>> UV_ARGS --cache-dir /netscratch/binder/cache/uv -m kibad_llm.predict name=428_organism_trends_with_chunking experiment/predict=organism_trends_with_chunking pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC extractor/llm=mistral_small_3_24b_in_process seed=42,1337,7331 --multirun
>>> JOB_NAME kiba-d_da16a534-5c76-4a4a-a527-833846c3e5ee
>>> GIT_REF (none; using current working tree)
=============================================
srun: jobinfo: version v1.0.0
srun: job 2868978 queued and waiting for resources
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