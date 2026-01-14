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

| Log Folder                                                                  | Date       | Issue Link                                        | Notes                                                              |
|:------------------------------------------------------------------------------|:-----------|:--------------------------------------------------|:-------------------------------------------------------------------|
| [159_core_schema_baseline_gpt5](./logs/159_core_schema_baseline_gpt5)         | 2026-01-09 | https://github.com/DFKI-NLP/kibad-llm/issues/159  | Only the GPT 5 run, which was a single run setup                   | 
| [159_core_schema_baseline_multirun](./logs/159_core_schema_baseline_multirun) | 2026-01-09 | https://github.com/DFKI-NLP/kibad-llm/issues/159  | gpt_oss_20b and qwen3_30b with 3 runs per model setup |
