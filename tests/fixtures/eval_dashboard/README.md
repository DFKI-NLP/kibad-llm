# Eval dashboard curated fixtures

These fixtures support the early smoke and regression checks for the eval-dashboard refactor.

## Fixture policy

- Fixtures are curated snapshots, not live references into `data/prediction_results/logs/`.
- Prefer representative source experiments added later than `2026-01-16`.
- Keep fixtures intentionally small and reviewable while preserving valid dashboard input shapes.
- `run_v1` is synthetic because no natural `job_return_value.json` with `"version": 1` is currently available in the repository logs.

## Fixtures

The live dashboard currently supports four plot families:

- grouped/standard bars for `F1MicroMultipleFieldsMetric`
- error plots for `ErrorCollector`
- confusion-matrix plots for `ConfusionMatrix` / `ConfusionMatrixCollection`
- TP/FP/FN plots for `TpFpFnCollector` / `TpFpFnCollectorCollection`

The fixtures below provide explicit examples for each of those plot families.

### `bars`

- purpose: explicit grouped/standard bar-plot example for future dashboard tests
- source basis: `data/prediction_results/logs/422_organism_trends/evaluate/multiruns/2026-04-28_18-21-06/0`
- notes: version-0 style F1-micro snapshot that exercises the generic bar-plot path

### `errors`

- purpose: explicit error-plot example for future dashboard tests
- source basis: `data/prediction_results/logs/428_organism_trends_with_chunking/evaluate/multiruns/2026-05-04_13-01-11/8`
- notes: version-0 style error collector snapshot with both `total` and `details` tabs

### `run_v0`

- purpose: valid version-0 style evaluation fixture
- source basis: `data/prediction_results/logs/397_faktencheck_core_v1_for_chunking/evaluate/multiruns/2026-04-10_16-12-49/11`
- notes: curated down to a smaller but shape-compatible snapshot

### `run_v1`

- purpose: valid version-1 style evaluation fixture
- source basis: derived from `run_v0`
- notes: synthetic fixture created by adding a top-level `"version": 1` field while preserving the version-0-style payload shape

### `run_v2`

- purpose: valid version-2 style evaluation fixture
- source basis: `data/prediction_results/logs/477_organism_trends/evaluate/multiruns/2026-05-26_10-57-22/0`
- notes: curated version-2 confusion-matrix snapshot

### `confusion_matrix`

- purpose: explicit confusion-matrix example for future dashboard tests
- source basis: `data/prediction_results/logs/477_organism_trends/evaluate/multiruns/2026-05-26_10-57-22/0`
- notes: small version-2 confusion-matrix sample

### `tpfpfn`

- purpose: explicit TP/FP/FN example for future dashboard tests
- source basis: `data/prediction_results/logs/481_faktencheck_core/evaluate/multiruns/2026-05-26_14-21-18/0`
- notes: curated version-2 TP/FP/FN collection snapshot

### `malformed`

- purpose: intentionally invalid input example
- source basis: synthetic fixture derived from the `confusion_matrix` version-2 sample by truncating the JSON payload
- notes: contains malformed JSON so loader-side parsing should fail

### `missing_prediction_id`

- purpose: intentionally missing prediction-id example for Phase 7 normalization coverage
- source basis: synthetic fixture derived from the `confusion_matrix` version-2 sample by removing `prediction.job_return_value.output_file`
- notes: contains valid JSON and valid overrides, but normalization must fail when the dashboard tries to extract the missing prediction id

### `unsupported_version`

- purpose: intentionally unsupported `job_return_value.json` version example
- source basis: synthetic fixture derived from the `confusion_matrix` version-2 sample by changing the top-level `"version"` field to `99`
- notes: contains a valid object with `"version": 99`

### `conflicting_prediction_ids`

- purpose: intentionally conflicting prediction-id example
- source basis: synthetic paired fixtures derived from a valid version-2-style run and edited so both runs reuse the same prediction id while differing in prediction metadata
- notes: contains two valid run directories that share the same prediction id but differ in prediction payload content

