## Please describe any files/folders you add to results here!

1. Create a folder for your experiment, naming it '[issue_or_pr_id]_[your_descriptive_name]'
2. Copy logs/ for your runs from cluster to this folder (`scp `)
   1. Strongly preferred is to copy prediction and evaluation logs into separate folders! 
3. Copy predictions/ for your runs from cluster to this folder
4. See `159_core_schema_baseline_gpt5` for an example folder structure for a single run
5. See `159_core_schema_baseline_multirun` for an example folder structure for a multi-run
5. If you follow the above structure, you can plot the evaluation results using the notebooks plot_evaluation.ipynb
   and plot_multirun_evaluation.ipynb

### Experiments

| Folder name                                                      | Date       | Issue Link                                        | Notes                                                              |
|:-----------------------------------------------------------------|:-----------|:--------------------------------------------------|:-------------------------------------------------------------------|
| [159_core_schema_baseline_gpt5](./159_core_schema_baseline_gpt5) | 2026-01-09 | https://github.com/DFKI-NLP/kibad-llm/issues/159  | Only the GPT 5 run, which was a single run setup                   | 
| [159_core_schema_baseline_multirun](./159_core_schema_baseline_multirun)                          | 2026-01-09 | https://github.com/DFKI-NLP/kibad-llm/issues/159  | gpt_oss_20b and qwen3_30b with 3 runs per model setup |
