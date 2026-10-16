# Hardware evidence for the manuscript

The available records establish resource requests and inference configuration, but **do not identify the GPU model, GPU memory capacity, or compute node actually assigned to any of the eight model/test-set jobs**. Search performed on 2026-10-06, in the requested order: prediction logs, experiment READMEs, repository files, then GitHub issues/PRs and discussions.

## Established configuration

- All 24 seed-run configs use in-process vLLM (`kibad_llm.llms.VllmInProcess`), `tensor_parallel_size: 1`, and `gpu_memory_utilization: 0.95`. The last value is a configured fraction, not measured memory usage or GPU capacity.
- The documented commands call `run_in_process.sh` without overriding its default of one GPU. The script requests one node, one task, six CPUs per task, one GPU per task and `--mem=128G` of host memory. These are scheduler requests, not measured resource usage or the physical specifications of the entire node.
- This script was verified at both exact source commits recorded in the run metadata: [CoreSchema commit](https://github.com/DFKI-NLP/kibad-llm/blob/11e74f3bab8ceed36682b9148d2169a24c9ed34a/run_in_process.sh) and [OrganismTrends commit](https://github.com/DFKI-NLP/kibad-llm/blob/50d38a1b00c4ded08378832e625a7f73bde099de/run_in_process.sh). Both versions have identical content (Git blob `aed13bc3f6aa077b16c3d2907b28489fa80d931c`). All 24 runs report `is_dirty: false`.
- All commands allow the partition list `H100-SLT,H100-Trails,H100,H200,B200,A100-80GB`. This is an eligibility list; its order does not establish which partition or GPU was used. The script's default `RTXA6000-SLT` is overridden and does not describe these jobs.
- Within each model/test-set combination, all three seeds share the same recorded Slurm job ID. Eight job allocations therefore cover the 24 seed runs.

Local sources are the [CoreSchema README](../../data/kibad-llm-results/logs/525_faktencheck_core_bestconfig_testset/README.md), [OrganismTrends README](../../data/kibad-llm-results/logs/549_organism_trends_bestconfig_testset/README.md), each seed directory's `.hydra/config.yaml` and `job_return_value.json`, and [run_in_process.sh](../../run_in_process.sh). The exact seed-directory paths are recorded in [runs.csv](runs.csv).

## Allocation lookup for a colleague or cluster administrator

Please recover the actual GPU model (including variant), GPU memory capacity, compute node and CPU model for these jobs. Confirm whether the same hardware was used across model/test-set combinations before treating the timing table as a comparison on identical hardware.

| Model               | CoreSchema Slurm job | OrganismTrends Slurm job |
| ------------------- | -------------------- | ------------------------ |
| GPT OSS 20B         | 3112047              | 3157298                  |
| Gemma 3 27B         | 3117415              | 3157300                  |
| Qwen 3 30B          | 3117417              | 3157301                  |
| Mistral Small 3 24B | 3117418              | 3157302                  |

CoreSchema jobs ran on 23–25 June 2026; OrganismTrends jobs ran on 9–12 July 2026 (timestamps in the stored console logs). A colleague with access to the submitting user's Slurm accounting records may be able to recover the assigned partition, node and GPU type. If accounting lists only an untyped GPU count, the administrator will also need the corresponding node inventory or original job stdout/stderr. These records were not present in the searched repository files. No cluster-accounting query has been run here.

## GitHub checks

The descriptions, issue comments, review comments and reviews of [PR #525](https://github.com/DFKI-NLP/kibad-llm/pull/525) and [PR #549](https://github.com/DFKI-NLP/kibad-llm/pull/549), and the comments of [publication issue #521](https://github.com/DFKI-NLP/kibad-llm/issues/521), did not identify the assigned GPUs for these jobs. Repository-wide issue/PR searches for GPU, hardware and sacct also yielded no allocation record for these runs. The [submission comment in #525](https://github.com/DFKI-NLP/kibad-llm/pull/525#issuecomment-4751911581) repeats the same list of eligible partitions. Mentions of specific GPU models in older development experiments do not establish the hardware of these test-set runs.

## Manuscript changes

Appendix C now has a “Hardware setup” subsection after the hyperparameter settings, with the established resource requests and configuration, a CPU-model placeholder, and Table C.1 containing GPU-model/VRAM placeholders for each model and test set. Section 3.3 references this subsection and states that the assigned GPU models remain to be confirmed. Inference-time values are unchanged.
