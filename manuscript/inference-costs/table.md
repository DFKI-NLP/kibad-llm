# Inference costs per document

Reproduce with `python scripts/manuscript_inference_costs.py` (no extra dependencies).

| Model               | Measure    |    CoreSchema | OrganismTrends |
| ------------------- | ---------- | ------------: | -------------: |
| GPT OSS 20B         | s/document |  76.84 ± 0.60 |   41.41 ± 0.39 |
| Gemma 3 27B         | s/document |  78.52 ± 3.30 |   65.80 ± 0.75 |
| Qwen 3 30B          | s/document | 109.11 ± 0.36 |   71.86 ± 0.36 |
| Mistral Small 3 24B | s/document | 103.10 ± 2.25 |  152.33 ± 2.38 |
| GPT-5               | €/document |           TBD |            TBD |

Values are mean ± sample standard deviation (ddof=1) across seeds 42, 1337 and 7331.
Each run's `time_extraction` is divided by the number of distinct `file_name` values
in its predictions JSONL, including documents with extraction errors or empty outputs.
Counts agree with all console logs: 500 for CoreSchema and 419 for OrganismTrends.
The 430 OrganismTrends documents stated elsewhere in the manuscript differ from
the 419 actually processed in these runs; the timing denominator is therefore 419.
This is extraction-stage wall-clock time, including chunk processing and aggregation,
excluding PDF conversion, extractor/model initialization and final file writing.
These are timings under the recorded execution conditions, not a controlled hardware benchmark.

Run locations are read from the prediction sections of the experiment READMEs:

- `525_faktencheck_core_bestconfig_testset` (CoreSchema)
- `549_organism_trends_bestconfig_testset` (OrganismTrends)

`runs.csv` preserves source paths, document counts and raw/normalized timings for all 24 runs.
`summary.csv` preserves unrounded means and sample standard deviations.

GPT-5 monetary costs remain TBD; no GPT-5 inference timings are included.
For the later cost analysis, the core README is `574_gpt5_faktencheck_core_testset`,
and the trends README is `574_gpt5_organism_trends_testset`; each specifies one seed.
The supplied experiment list repeats the trends experiment for GPT-5 core.
