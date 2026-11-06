# Task C evaluator: maintainer notes

**Private maintainer documentation. Do not include this file or repository tests in the
participant download.** Distribute only `evaluation/evaluate.py`, `evaluation/README.md`,
`evaluation/requirements-bertscore.txt`, and optionally `evaluation/metadata.yaml`.
Those files neither import nor identify the `kibad-llm` project. Do not distribute a
repository archive or the gold references with a scoring-program archive.

## Derivation from the existing implementation

The specification is Task C in `Advanced NLP shared tasks task descriptions.docx`.
The supplied `example-data/train.jsonl` contains 908 records keyed by `zotitem_ptr_id`.
It is read directly, without modifying the downloaded data. PDFs are not needed for
evaluation, and no data links were downloaded again.

Data naming caveat: driver objects in the supplied training references use `details`,
matching `DirectDriver.details` and `IndirectDriver.details` in
`src/kibad_llm/schema/types.py`, while the task document calls this text `description`.
The evaluator accepts either spelling on either side and reports the canonical task
names `direct_driver.description` and `indirect_driver.description`. If both keys occur
in one object, their normalized sets must agree; conflicts are rejected rather than
silently overwriting or combining values. The unchanged training file has 995 distinct
per-paper biodiversity-variable values, 464 direct-driver text values and 70 indirect-driver
text values. Ignoring the alias would incorrectly leave both driver text supports empty.

| Existing code/configuration                                                                  | Standalone implementation and relationship                                                                                                                                                                                                                                                                                                                                                                |
| -------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `src/kibad_llm/evaluate.py::evaluate`                                                        | The same per-paper prediction/reference comparison, followed by a final reduction. `evaluate.py::main` replaces Hydra/dataset instantiation with explicit JSONL arguments and a CodaBench adapter.                                                                                                                                                                                                        |
| `src/kibad_llm/utils/dictionary.py::flatten_to_value_lists`, with `remove_empty_values=True` | `field_values` traverses only the selected dotted path through objects and transparent lists. It omits null/blank leaves, preserves nonblank strings without stripping, and collapses duplicates into a set. Extra fields are ignored without traversal. The task requires string leaves; numbers, booleans and objects at scored leaves are rejected rather than accepted as generic project primitives. |
| `src/kibad_llm/metrics/base.py::MetricWithPrepareEntryAsSet._prepare_entry_as_set`           | The returned sets implement the same normalization used with `flatten_dicts=True`. Scalar strings and lists of strings produce identical sets. Nested subfield associations disappear, as in the existing flattened evaluation.                                                                                                                                                                           |
| `src/kibad_llm/metrics/base.py::MetricWithTpFpFnEntries._update`                             | Per-paper intersections/differences yield TP, FP and FN. Summing their lengths is equivalent to the project's sets of `(record_id, value)` when IDs are unique. Duplicate IDs are rejected at load time. One-sided empties are scored, matching `ignore_missing_entries=False`.                                                                                                                           |
| `src/kibad_llm/metrics/f1.py::F1MicroSingleFieldMetric.calculate_scores`                     | `categorical_scores` uses the same precision, recall, F1 and support formulas, including zero for undefined denominators. Explicit TP/FP/FN counts are also returned.                                                                                                                                                                                                                                     |
| `src/kibad_llm/metrics/f1.py::F1MicroMultipleFieldsMetric._compute`                          | Group `macro_f1` corresponds to project `AVG.f1`; group `micro` corresponds to `ALL`. The standalone report gives macro F1 explicitly and does not average support as the generic project `AVG` row does.                                                                                                                                                                                                 |
| `src/kibad_llm/dataset/utils.py::merge_references_into_predictions`                          | The default strict alignment policy is retained: reject missing references and missing predictions. JSONL order does not matter. There is no permissive mode that could silently omit papers from support.                                                                                                                                                                                                |
| `configs/experiment/evaluate/faktencheck_core_f1_micro_flat.yaml`                            | Retains the flattened comparison, but C1 uses exactly the five fields in the task document. The config's `taxa.german_name` and `taxa.scientific_name` move to C2b.                                                                                                                                                                                                                                       |
| `configs/experiment/evaluate/faktencheck_f1_micro_flat.yaml`                                 | Supplies the established exact-match behavior for the remaining categorical fields and taxa names. The task document limits field groups, adds `ecosystem_type.term`, and calls for BERTScore on three explicitly named text fields. Unrelated project fields are excluded.                                                                                                                               |

There are 16 distinct exact-match fields and three text fields across all tasks. The
allowlists are literal constants derived from the task's schema-group table; the evaluator
does not import Pydantic schemas, Hydra configuration, normalization services or project
code. Reference-only extras such as `taxa.collective_term` and
`ecosystem_type.description` do not affect scores. The evaluator does not validate
enum membership: an incorrect string is an FP and any missing gold label is an FN.

Each C2 selection includes C1. The `c2` aggregate contains the union of selected C2 fields;
`all` contains the union of C1 and selected C2 fields. This prevents `biodiversity_level`
and `taxa.species_group` from being double-counted when C2b is included. Each group retains
its own complete field list. All configured categorical fields enter macro F1, including
fields with zero support; such a field has F1 0, as in the project defaults.

## New BERTScore definition

The project has no BERTScore implementation. The document leaves model choice,
best-match direction, reduction and empty handling unspecified; the requester authorized
choosing and documenting these. The definition in the participant README is therefore
a new explicit task policy, not a claim of parity with an existing semantic metric.

`best_match_sum` builds pair scores only within a paper and field, finds each prediction's
best reference and each reference's best prediction, and adds both sets of maxima.
It uses the arithmetic mean over all directional value matches, pooled across papers.
This weights each predicted/reference value once rather than averaging per-paper means
or taking a harmonic mean of directional means. Matches can be reused; this is not
one-to-one assignment. Null/blank values and duplicates are removed before matching.
One-sided empty sets contribute zero and retain their cardinality in the denominator;
both-empty sets contribute nothing. No category-conditioned description matching is
performed because the document specifies independent sets per field. Both category and
description can therefore score well even if their associations are wrong.

The model is multilingual because labels/text are German and papers may be German or
English. The [model card](https://huggingface.co/google-bert/bert-base-multilingual-cased)
describes the cased multilingual checkpoint. Layer 9 follows the upstream
[BERTScore 0.3.13 model/layer mapping](https://github.com/Tiiiger/bert_score/blob/v0.3.13/bert_score/utils.py).
The model and tokenizer are obtained from an immutable Hugging Face commit, downloading
only safetensors and tokenizer/config files. `BertPairs` supplies the local snapshot
path and explicit layer count to `BERTScorer`, avoiding its unpinned model-name download.
IDF and baseline rescaling are disabled; the slow tokenizer, CPU, batch size, thread count,
random seed and deterministic algorithm setting are explicit. Standard upstream
tokenization/truncation applies (512 tokens including special tokens).

`requirements-bertscore.txt` pins the metric, model runtime, hub client and NumPy versions.
It is not a full platform-specific transitive lockfile: build and retain one scoring image
for the competition, record its digest, and preload the model cache in that image or mount
it read-only at runtime. CPU/library/hardware changes can cause small numerical differences.
The detailed report includes model policy and actual package versions when the model ran.
Categorical-only runs omit text metrics entirely; they never substitute exact matching.

## CodaBench deployment

The adapter follows CodaBench's documented `input/ref`, `input/res`, `output/scores.json`
contract; see the [official competition design](https://docs.codabench.org/dev/Organizers/Benchmark_Creation/Competition-Design/)
and [bundle structure](https://docs.codabench.org/v1.27/Organizers/Benchmark_Creation/Competition-Bundle-Structure/).
Reference archives must contain `references.jsonl` at their root, and submission archives
must contain exactly `predictions.jsonl`. Put the public evaluator files and `metadata.yaml`
directly at the scoring-program archive root. Package dependencies and the pinned model
in the scoring image; installation at scoring time is not performed by the script.
`python evaluate.py prepare-model` populates the cache selected by `HF_HOME`;
`HF_HUB_OFFLINE=1` prevents runtime network access after preloading.

Configure leaderboard columns against the flat keys in `scores.json`, rank descending by
`c1_score`, and select optional C2 columns as needed. The metadata defaults to all groups;
omit unrelated leaderboard columns or append `--task c2a`, `--task c2b`, etc. to the command
for a group-specific instance. A partial submission still scores C1 normally; omitted C2
fields have empty predictions and receive the corresponding penalties.
`detailed_scores.json` contains aggregate counts/settings without paper IDs or gold values;
stdout lists all leaderboard/per-field metrics. Validation errors exit nonzero and do not
produce a new score file. Use a fresh output directory for every submission.

The task document still lists baseline scores as `XX`. No thresholds were invented and
no baseline-validity gate is implemented. Compute/finalize the random and constant
baselines separately before enforcing the course's validity rule.

## Verification

Run the standalone contract tests and project parity tests with:

```sh
.venv/bin/python -m pytest tests/unit/shared_task/test_evaluation.py
```

The tests cover reference/prediction alignment, empty/missing fields, duplicate values,
exact strings, independent nested subfields, fixed macro denominators, unique-field
aggregates, best-match directionality/batching/empty penalties, CLI errors, CodaBench
layout and scores, and dependency-free execution outside the repository. The parity
tests compare TP/FP/FN, precision/recall/F1/support and macro/micro aggregates against
the existing project classes on the supplied training data, including perturbed
predictions. The training fixture is optional so a clean clone without local course
data can still run the remaining tests. Real-model smoke verification is separate
from the fast tests, which inject deterministic pair scores and require no network.
