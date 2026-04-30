# 428_organism_trends_with_chunking

similar to [380_organism_trends](../380_organism_trends) + evaluation as in [422_organism_trends](../422_organism_trends), but with chunking as in [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking)

## Details

### Inference

- based on [380_organism_trends](../380_organism_trends)
- adapted according to [397_faktencheck_core_v1_for_chunking](../397_faktencheck_core_v1_for_chunking)
- no gpt5 for now

```bash
./run_in_process.sh \
-pa "H100-SLT,H100-Trails,H100,A100-80GB" \
-t "3-00:00:00" \
-u "-m kibad_llm.predict \
name=428_organism_trends_with_chunking \
experiment/predict=organism_trends_with_chunking \
pdf_directory=/ds/text/kiba-d/dev-set-Wald-WVC \
extractor/llm=gpt_oss_20b_in_process,gemma3_27b_in_process,qwen3_30b_in_process,mistral_small_3_24b_in_process \
seed=42,1337,7331 \
--multirun"
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