## Please describe any files/folders you add to results here!

IMPORTANT: Any prediction and evaluation runs should be created with a good `name` argument! 
I.e., `name=[issue_or_pr_id]_[your_descriptive_name]`. 

1. Copy `logs/` for your runs from cluster into the local `logs/` (execute from this folder):
   ```
   scp -r <user>@<machine>:/netscratch/hennig/kiba-d/logs/<name> ./logs/
   ```
2. Copy `predictions/` for your runs from cluster to the local `predictions/` (execute from this folder):
   ```
   scp -r <user>@<machine>:/netscratch/hennig/kiba-d/predictions/<name> ./predictions/
   ```
3. Create `logs/<name>/readme.md` and describe the setup.
4. Add a line to the table below with a link to the new log folder, the date, the issue or PR link, and any notes.
5. See `159_core_schema_baseline_gpt5` for example folder structures for a single run and `159_core_schema_baseline_multirun` for example folder structures for a multi-run.
6. If you follow the above structure, you can plot the evaluation results using the notebook `plot_multirun_evaluation.ipynb`.

### Experiments

| Log Folder                                                                                  | Date       | Issue Link                                       | Notes                                                                                                                                                                 |
|:--------------------------------------------------------------------------------------------|:-----------|:-------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| [159_core_schema_baseline](logs/159_core_schema_baseline)                                   | 2026-01-09 | https://github.com/DFKI-NLP/kibad-llm/issues/159 | gpt_oss_20b and qwen3_30b with 3 runs per model setup and single GPT 5 run                                                                                            |
| [260_baseline_default_no_evi](logs/260_baseline_default_no_evi)                             | 2026-01-16 | https://github.com/DFKI-NLP/kibad-llm/issues/260 | gpt_oss_20b, gemma3_27b and gpt_5, single run, default prompt template                                                                                                |
| [261_baseline_faktencheck_core_variance](./logs/261_baseline_faktencheck_core_variance)     | 2026-01-15 | https://github.com/DFKI-NLP/kibad-llm/issues/261 | variance analysis for faktencheck (core fields with evidence; 3 llms; 3 seeds)                                                                                        |
| [276_baseline_faktencheck_core_v1_no_evi](logs/276_baseline_faktencheck_core_v1_no_evi)     | 2026-01-16 | https://github.com/DFKI-NLP/kibad-llm/issues/276 | gpt_oss_20b, gemma3_27b and gpt_5, single run, faktencheck_core_v1 prompt template                                                                                    |
| [277_baseline_faktencheck_core_v1_with_evi](logs/277_baseline_faktencheck_core_v1_with_evi) | 2026-01-16 | https://github.com/DFKI-NLP/kibad-llm/issues/277 | gpt_oss_20b, gemma3_27b and gpt_5, single run, faktencheck_core_v1_with_evidence prompt template                                                                      |
| [255_organism_trend_baseline_no_evi](logs/255_organism_trend_baseline_no_evi)               | 2026-01-30 | https://github.com/DFKI-NLP/kibad-llm/issues/255 | gpt_oss_20b, gemma3_27b, qwen3_30b, mistral_small_3_24b, and gpt_5, temperature variable, default prompt template                                                     |
| [308_fix_reasoning_content_splitting](logs/308_fix_reasoning_content_splitting)             | 2026-01-16 | https://github.com/DFKI-NLP/kibad-llm/issues/308 | gpt_oss_20b, gemma3_27, qwen3_30b, ministral, mistral, and nemotron; all in-process; temperature 0.0; faktencheck core                                                |
| [311_better_default_temperature_baseline](logs/311_better_default_temperature_baseline)     | 2026-01-26 | https://github.com/DFKI-NLP/kibad-llm/issues/311 | gpt_oss_20b, gemma3_27, qwen3_30b, mistral, and nemotron; all in-process; temperature 0.0; faktencheck core                                                           |
| [311_better_default_temperature](logs/311_better_default_temperature)                       | 2026-01-26 | https://github.com/DFKI-NLP/kibad-llm/issues/311 | gpt_oss_20b, gemma3_27, qwen3_30b, mistral, and nemotron; all in-process; temperature variable; faktencheck core                                                      |
| [327_faktencheck_core_with_persona](logs/327_faktencheck_core_with_persona)                 | 2026-01-28 | https://github.com/DFKI-NLP/kibad-llm/pull/327   | gpt_oss_20b, gemma3_27, qwen3_30b, mistral, and gpt_5; with adjusted template that mentions a persona; faktencheck core                                               |
| [226_dont_include_field_and_type_descriptions](logs/226_dont_include_field_and_type_descriptions)                  | 2026-02-01 | https://github.com/DFKI-NLP/kibad-llm/pull/226   | gpt_oss_20b, gemma3_27, qwen3_30b, mistral, and gpt_5; include/exclude field/type descriptions; faktencheck core                                                      |
| [88_faktencheck_core_gpt5_baseline](logs/88_faktencheck_core_gpt5_baseline)                  | 2026-01-30 | https://github.com/DFKI-NLP/kibad-llm/issues/88  | gpt 5; simple extractor (with reasoning, new eval format, 3 seeds); faktencheck core                                                                                  |
| [88_repeat_faktencheck_core](logs/88_repeat_faktencheck_core)                  | 2026-01-30 | https://github.com/DFKI-NLP/kibad-llm/issues/88  | gpt_oss_20b, gemma3_27, qwen3_30b, mistral; with ensemble (majority vote) over 3 queries per document (repeat extractor); faktencheck core                            |
| [257_organism_trends_v1_with_evi](logs/257_organism_trends_v1_with_evi)                     | 2026-02-02 | https://github.com/DFKI-NLP/kibad-llm/issues/257 | gpt_oss_20b, gemma3_27b, qwen3_30b, mistral_small_3_24b, and gpt_5; with adjusted template and evidence; organism trend                                               |
| [333_organism_trends_with_persona](logs/333_organism_trends_with_persona)                   | 2026-02-02 | https://github.com/DFKI-NLP/kibad-llm/issues/333 | gpt_oss_20b, gemma3_27b, qwen3_30b, mistral_small_3_24b, and gpt_5; with adjusted template that mentions a persona; organism trende                                   |
| [334_dont_include_field_and_type_descriptions](logs/334_dont_include_field_and_type_descriptions)                               | 2026-02-02 | https://github.com/DFKI-NLP/kibad-llm/issues/334 | gpt_oss_20b, gemma3_27b, qwen3_30b, mistral_small_3_24b; with and without field and type descriptions, with adjusted template that mentions a persona; organism trend |
| [335_organism_trends_ensemble](logs/335_organism_trends_ensemble)                      | 2026-02-02 | https://github.com/DFKI-NLP/kibad-llm/issues/335 | gpt_oss_20b, gemma3_27b, qwen3_30b, mistral_small_3_24b; majority voting ensemble, with adjusted template that mentions a persona; organism trend                     |
| [348_faktencheck_core_repeat](logs/348_faktencheck_core_repeat)                  | 2026-02-06 | https://github.com/DFKI-NLP/kibad-llm/issues/348 | gpt_oss_20b; with ensemble (majority vote) over 3 queries per document (repeat extractor) with bugfixes; faktencheck core                                             |
| [327_faktencheck_core_with_persona_docs_not_too_long](logs/327_faktencheck_core_with_persona_docs_not_too_long)                 | 2026-02-12 |    | same as faktencheck_core_with_persona, but evaluated only on docs that do not throw "document too long" errors                                                        |
| [371_faktencheck_core_fix_ecosystem_type](logs/371_faktencheck_core_fix_ecosystem_type)                 | 2026-01-28 | https://github.com/DFKI-NLP/kibad-llm/pull/371   | gpt_oss_20b, gemma3_27, qwen3_30b, mistral, and gpt_5; with adjusted schema for `ecosystem_type`; faktencheck core    
| [380_organism_trends](logs/380_organism_trends)                 | 2026-02-26 | https://github.com/DFKI-NLP/kibad-llm/pull/380 | same as [333_organism_trends_with_persona](logs/333_organism_trends_with_persona), but with fix for schema description generation: use space normalization to fix indentation |
