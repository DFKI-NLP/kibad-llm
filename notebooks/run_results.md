## 2025-11-21_10-15-33 - openai/gpt-oss-20b, two_schemata
./run_with_llm.sh -v "openai/gpt-oss-20b" -pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=two_schemata
pdf_directory=/ds/text/kiba-d/dev-set-100/"

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-11-21_10-15-33/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-09 16:40:42,923][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.164 |    0.6   | 0.258 |        20 |
| habitat                |       0.605 |    0.543 | 0.573 |       138 |
| location.country       |       0.156 |    0.138 | 0.147 |       123 |
| location.federal_state |       0.516 |    0.647 | 0.574 |        51 |
| location.name          |       0.082 |    0.058 | 0.068 |       154 |
| natural_region         |       0.513 |    0.667 | 0.58  |        60 |
| taxa.german_name       |       0.143 |    0.113 | 0.126 |       231 |
| taxa.scientific_name   |       0.136 |    0.142 | 0.139 |       197 |
| taxa.species_group     |       0.473 |    0.33  | 0.389 |       106 |
| AVG                    |       0.31  |    0.36  | 0.317 |       120 |
| ALL                    |       0.27  |    0.255 | 0.262 |      1080 |
[2025-12-09 16:40:42,945][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_16-40-42/job_return_value.json
[2025-12-09 16:40:42,948][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_16-40-42/job_return_value.md


## 2025-12-10_12-11-20 - openai/gpt-oss-20b, faktencheck_most_important_schema
./run_with_llm.sh -v "openai/gpt-oss-20b" -vv "0.11.2" -pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 -u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d experiment/predict=faktencheck_most_important_schema pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor/llm=gpt_oss_20b"
[2025-12-10 13:13:42,240][__main__][INFO] - Writing results to /netscratch/hennig/kiba-d/predictions/default/2025-12-10_12-11-20/predictions.jsonl ...                                                                                      
Creating json from Arrow format: 100%|██████████| 1/1 [00:00<00:00, 56.59ba/s]                                        
[2025-12-10 13:13:42,273][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_12-11-20/job_return_value.json                    
[2025-12-10 13:13:42,277][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_12-11-20/job_return_value.md                      

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-10_12-11-20/predictions.jsonl paths.save_dir=/netscratch/hennig/kiba-d/ experiment/evaluate=faktencheck_f1_micro_flat metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]
2025-12-10 13:36:32,139][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.19  |    0.6   | 0.289 |        20 |
| habitat                |       0.602 |    0.514 | 0.555 |       138 |
| location.country       |       0.323 |    0.333 | 0.328 |       123 |
| location.federal_state |       0.688 |    0.863 | 0.765 |        51 |
| location.name          |       0.112 |    0.104 | 0.108 |       154 |
| natural_region         |       0.683 |    0.467 | 0.554 |        60 |
| taxa.german_name       |       0.114 |    0.203 | 0.146 |       231 |
| taxa.scientific_name   |       0.143 |    0.31  | 0.196 |       197 |
| taxa.species_group     |       0.49  |    0.462 | 0.476 |       106 |
| AVG                    |       0.372 |    0.429 | 0.38  |       120 |
| ALL                    |       0.247 |    0.342 | 0.286 |      1080 |
[2025-12-10 13:36:32,142][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_13-36-31/job_return_value.json
[2025-12-10 13:36:32,145][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_13-36-31/job_return_value.md



## 2025-12-10_13-50-58   Qwen/Qwen3-30B-A3B-Thinking-2507

./run_with_llm.sh -v "Qwen/Qwen3-30B-A3B-Thinking-2507 --max-model-len 131072 --reasoning-parser deepseek_r1" -vv "0.11.2"
-pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor/llm=qwen3_30b"

[2025-12-10 14:30:27,336][__main__][INFO] - Writing results to /netscratch/hennig/kiba-d/predictions/default/2025-12-10_13-50-58/predictions.jsonl ...
Creating json from Arrow format: 100%|██████████| 1/1 [00:00<00:00, 57.39ba/s]
[2025-12-10 14:30:27,635][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_13-50-58/job_return_value.json
[2025-12-10 14:30:27,651][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_13-50-58/job_return_value.md

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-10_13-50-58/predictions.jsonl paths.save_dir=/netscratch/hennig/kiba-d/ experiment/evaluate=faktencheck_f1_micro_flat metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-10 14:48:28,432][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.297 |    0.55  | 0.386 |        20 |
| habitat                |       0.72  |    0.486 | 0.58  |       138 |
| location.country       |       0.556 |    0.203 | 0.298 |       123 |
| location.federal_state |       0.625 |    0.784 | 0.696 |        51 |
| location.name          |       0.222 |    0.117 | 0.153 |       154 |
| natural_region         |       0.567 |    0.283 | 0.378 |        60 |
| taxa.german_name       |       0.158 |    0.143 | 0.15  |       231 |
| taxa.scientific_name   |       0.17  |    0.183 | 0.176 |       197 |
| taxa.species_group     |       0.519 |    0.509 | 0.514 |       106 |
| AVG                    |       0.426 |    0.362 | 0.37  |       120 |
| ALL                    |       0.344 |    0.279 | 0.308 |      1080 |
[2025-12-10 14:48:28,434][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_14-48-27/job_return_value.json
[2025-12-10 14:48:28,450][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_14-48-27/job_return_value.md

## 2025-12-10_15-29-36 - Nemotron-Nano
./run_with_llm.sh -v "nvidia/NVIDIA-Nemotron-Nano-12B-v2 --trust-remote-code"  -vv "0.11.2" -pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor/llm=nemotron_nano_12b"

[2025-12-10 17:05:20,314][__main__][INFO] - Writing results to /netscratch/hennig/kiba-d/predictions/default/2025-12-10_15-29-36/predictions.jsonl ...
Creating json from Arrow format: 100%|██████████| 1/1 [00:00<00:00, 35.64ba/s]
[2025-12-10 17:05:20,392][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_15-29-36/job_return_value.json
[2025-12-10 17:05:20,409][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_15-29-36/job_return_value.md

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-15-29-36/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-11 09:19:31,088][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.178 |    0.65  | 0.28  |        20 |
| habitat                |       0.473 |    0.254 | 0.33  |       138 |
| location.country       |       0.589 |    0.35  | 0.439 |       123 |
| location.federal_state |       0.382 |    0.667 | 0.486 |        51 |
| location.name          |       0.134 |    0.084 | 0.104 |       154 |
| natural_region         |       0.25  |    0.3   | 0.273 |        60 |
| taxa.german_name       |       0.159 |    0.156 | 0.158 |       231 |
| taxa.scientific_name   |       0.202 |    0.239 | 0.219 |       197 |
| taxa.species_group     |       0.374 |    0.321 | 0.345 |       106 |
| AVG                    |       0.305 |    0.335 | 0.292 |       120 |
| ALL                    |       0.266 |    0.253 | 0.259 |      1080 |
[2025-12-11 09:19:31,091][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-19-30/job_return_value.json
[2025-12-11 09:19:31,097][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-19-30/job_return_value.md

##   - Gemma3-27B
export HF_TOKEN=...
./run_with_llm.sh -v "google/gemma-3-27b-it --max-model-len 45536 --hf-token HF_TOKEN"  -vv "0.11.2" 
-pa "H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor/llm=gemma3_27b"

[2025-12-11 09:44:14,937][__main__][INFO] - Writing results to /netscratch/hennig/kiba-d/predictions/default/2025-12-11_09-28-48/predictions.jsonl ...
Creating json from Arrow format: 100%|██████████| 1/1 [00:00<00:00, 80.65ba/s]
[2025-12-11 09:44:15,007][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-28-48/job_return_value.json
[2025-12-11 09:44:15,012][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-28-48/job_return_value.md

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-11_09-28-48/predictions.jsonl
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-11 10:18:31,926][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.104 |    0.55  | 0.175 |        20 |
| habitat                |       0.508 |    0.442 | 0.473 |       138 |
| location.country       |       0.388 |    0.325 | 0.354 |       123 |
| location.federal_state |       0.366 |    0.725 | 0.487 |        51 |
| location.name          |       0.072 |    0.071 | 0.072 |       154 |
| natural_region         |       0     |    0     | 0     |        60 |
| taxa.german_name       |       0.082 |    0.143 | 0.104 |       231 |
| taxa.scientific_name   |       0.106 |    0.234 | 0.146 |       197 |
| taxa.species_group     |       0.352 |    0.415 | 0.381 |       106 |
| AVG                    |       0.22  |    0.323 | 0.243 |       120 |
| ALL                    |       0.182 |    0.262 | 0.215 |      1080 |
[2025-12-11 10:18:31,929][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_10-18-31/job_return_value.json
[2025-12-11 10:18:31,947][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_10-18-31/job_return_value.md



## 2025-12-10_15-18-03 - Mistral Small 3.2 24B

./run_with_llm.sh -v "mistralai/Mistral-Small-3.2-24B-Instruct-2506 --tokenizer_mode mistral 
--config_format mistral --load_format mistral"  -vv "0.11.2" -pa "H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor/llm=mistral_small_3_24b"

[2025-12-10 18:04:37,879][__main__][INFO] - Writing results to /netscratch/hennig/kiba-d/predictions/default/2025-12-10_15-18-03/predictions.jsonl ...
Creating json from Arrow format: 100%|██████████| 1/1 [00:00<00:00, 12.99ba/s]
[2025-12-10 18:04:38,014][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_15-18-03/job_return_value.json
[2025-12-10 18:04:38,032][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_15-18-03/job_return_value.md

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-10_15-18-03/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-11 09:23:34,934][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.098 |    0.6   | 0.168 |        20 |
| habitat                |       0.537 |    0.471 | 0.502 |       138 |
| location.country       |       0.458 |    0.439 | 0.448 |       123 |
| location.federal_state |       0.267 |    0.843 | 0.406 |        51 |
| location.name          |       0.088 |    0.117 | 0.101 |       154 |
| natural_region         |       0.396 |    0.35  | 0.372 |        60 |
| taxa.german_name       |       0.092 |    0.225 | 0.131 |       231 |
| taxa.scientific_name   |       0.07  |    0.269 | 0.111 |       197 |
| taxa.species_group     |       0.321 |    0.396 | 0.354 |       106 |
| AVG                    |       0.259 |    0.412 | 0.288 |       120 |
| ALL                    |       0.161 |    0.333 | 0.217 |      1080 |
[2025-12-11 09:23:34,937][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-23-34/job_return_value.json
[2025-12-11 09:23:34,941][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-23-34/job_return_value.md

## 2025-12-10_15-44-53 - Ministral 3 14B
./run_with_llm.sh -v "mistralai/Ministral-3-14B-Reasoning-2512 --tokenizer_mode mistral --config_format mistral 
--load_format mistral --max-model-len 131072 --reasoning-parser mistral"  -vv "0.11.2" -pa "H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor/llm=ministral_3_14b"

[2025-12-10 16:43:11,604][__main__][INFO] - Writing results to /netscratch/hennig/kiba-d/predictions/default/2025-12-10_15-44-53/predictions.jsonl ...
Creating json from Arrow format: 100%|██████████| 1/1 [00:00<00:00, 18.25ba/s]
[2025-12-10 16:43:11,703][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_15-44-53/job_return_value.json
[2025-12-10 16:43:11,755][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-10_15-44-53/job_return_value.md

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-10_15-44-53/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-11 09:30:17,343][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |   f1 |   support |
|:-----------------------|------------:|---------:|-----:|----------:|
| climate                |           0 |        0 |    0 |        20 |
| habitat                |           0 |        0 |    0 |       138 |
| location.country       |           0 |        0 |    0 |       123 |
| location.federal_state |           0 |        0 |    0 |        51 |
| location.name          |           0 |        0 |    0 |       154 |
| natural_region         |           0 |        0 |    0 |        60 |
| taxa.german_name       |           0 |        0 |    0 |       231 |
| taxa.scientific_name   |           0 |        0 |    0 |       197 |
| taxa.species_group     |           0 |        0 |    0 |       106 |
| AVG                    |           0 |        0 |    0 |       120 |
| ALL                    |           0 |        0 |    0 |      1080 |
[2025-12-11 09:30:17,346][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-30-17/job_return_value.json
[2025-12-11 09:30:17,356][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-11_09-30-17/job_return_value.md

========================================== OLD RUNS ======================


## 2025-12-09_10-47-22 - openai/gpt-oss-20b, faktencheck_most_important_schema_extended
./run_with_llm.sh -v "openai/gpt-oss-20b" -pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema_extended
pdf_directory=/ds/text/kiba-d/dev-set-100/"

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-09_10-51-56/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]


[2025-12-09 15:31:28,500][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.179 |    0.35  | 0.237 |        20 |
| habitat                |       0.602 |    0.362 | 0.452 |       138 |
| location.country       |       0.273 |    0.22  | 0.243 |       123 |
| location.federal_state |       0.567 |    0.667 | 0.613 |        51 |
| location.name          |       0.084 |    0.084 | 0.084 |       154 |
| natural_region         |       0.632 |    0.2   | 0.304 |        60 |
| taxa.german_name       |       0.199 |    0.186 | 0.192 |       231 |
| taxa.scientific_name   |       0.254 |    0.289 | 0.271 |       197 |
| taxa.species_group     |       0.458 |    0.311 | 0.371 |       106 |
| AVG                    |       0.361 |    0.297 | 0.308 |       120 |
| ALL                    |       0.286 |    0.256 | 0.27  |      1080 |
[2025-12-09 15:31:28,502][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_15-31-28/job_return_value.json
[2025-12-09 15:31:28,505][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_15-31-28/job_return_value.md


## 2025-12-09_15-41-00   - Qwen3-8B, faktencheck_most_important_schema. TODO rerun, LLM config not properly set for Qwen3
Note: Qwen3/Qwen3-8B  - max tokens 40960 in log!

./run_with_llm.sh -v "Qwen/Qwen3-8B" -pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor.llm.model='Qwen/Qwen3-8B'"

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-09_15-41-00/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-09 16:44:43,456][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.054 |    0.15  | 0.079 |        20 |
| habitat                |       0.468 |    0.21  | 0.29  |       138 |
| location.country       |       0.361 |    0.179 | 0.239 |       123 |
| location.federal_state |       0.183 |    0.667 | 0.287 |        51 |
| location.name          |       0.056 |    0.078 | 0.065 |       154 |
| natural_region         |       0.136 |    0.05  | 0.073 |        60 |
| taxa.german_name       |       0.1   |    0.139 | 0.116 |       231 |
| taxa.scientific_name   |       0.184 |    0.299 | 0.228 |       197 |
| taxa.species_group     |       0.237 |    0.217 | 0.227 |       106 |
| AVG                    |       0.198 |    0.221 | 0.178 |       120 |
| ALL                    |       0.162 |    0.201 | 0.179 |      1080 |
[2025-12-09 16:44:43,458][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_16-44-43/job_return_value.json
[2025-12-09 16:44:43,461][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_16-44-43/job_return_value.md

## 2025-12-09_15-23-27   - Qwen3-8B, faktencheck_most_important_schema_extended  TODO rerun, LLM config not properly set for Qwen3
Note: Qwen3/Qwen3-8B  - max tokens 40960 in log!

./run_with_llm.sh -v "Qwen/Qwen3-8B" -pa "RTXA6000-SLT,H100-SLT,H100-Trails" -t 1-00:00:00 
-u "-m kibad_llm.predict 
paths.save_dir=/netscratch/hennig/kiba-d 
experiment/predict=faktencheck_most_important_schema_extended 
pdf_directory=/ds/text/kiba-d/dev-set-100/ extractor.llm.model='Qwen/Qwen3-8B'"

uv run -m kibad_llm.evaluate dataset.predictions.file=/netscratch/hennig/kiba-d/predictions/default/2025-12-09_15-23-27/predictions.jsonl 
paths.save_dir=/netscratch/hennig/kiba-d/ 
experiment/evaluate=faktencheck_f1_micro_flat 
metric.fields=[habitat,natural_region,climate,taxa.german_name,taxa.scientific_name,taxa.species_group,location.name,location.country,location.federal_state]

[2025-12-09 17:01:41,492][kibad_llm.metric][INFO] - Evaluation results:
| field                  |   precision |   recall |    f1 |   support |
|:-----------------------|------------:|---------:|------:|----------:|
| climate                |       0.162 |    0.3   | 0.211 |        20 |
| habitat                |       0.438 |    0.152 | 0.226 |       138 |
| location.country       |       0.524 |    0.179 | 0.267 |       123 |
| location.federal_state |       0.299 |    0.51  | 0.377 |        51 |
| location.name          |       0.086 |    0.065 | 0.074 |       154 |
| natural_region         |       0.154 |    0.033 | 0.055 |        60 |
| taxa.german_name       |       0.142 |    0.108 | 0.123 |       231 |
| taxa.scientific_name   |       0.226 |    0.203 | 0.214 |       197 |
| taxa.species_group     |       0.239 |    0.104 | 0.145 |       106 |
| AVG                    |       0.252 |    0.184 | 0.188 |       120 |
| ALL                    |       0.22  |    0.151 | 0.179 |      1080 |
[2025-12-09 17:01:41,495][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_17-01-41/job_return_value.json
[2025-12-09 17:01:41,497][kibad_llm.hydra_callbacks.save_job_return_value.SaveJobReturnValueCallback][INFO] - Saving job_return in /netscratch/hennig/kiba-d/logs/runs/default/2025-12-09_17-01-41/job_return_value.md
