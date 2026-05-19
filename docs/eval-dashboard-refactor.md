# Eval Dashboard Refactor Notes

## Current architecture snapshot

### Canonical state

- Imported data lives only in:
  - `state.predictions`
  - `state.evaluations`
- UI state lives only in fields like:
  - prediction selection / sorting / truncation / defaults
  - evaluation tab state in `state.evalTabStates`
  - active tabs and plot preferences

### Derived selector layer

- Prediction-side derived structures are built through selectors such as:
  - `getPredictionViews()`
  - `getCurrentPredictionFields()`
  - `getCurrentPredictionGroups()`
- Evaluation-side derived structures are built through selectors such as:
  - `getEvaluationContext()`
  - `getSelectedEvaluationGroups()`
  - `getPlotGroups()`
- Prediction and evaluation fields are now represented as typed descriptors rather than prefix-parsed strings.

### Rendering flow

- `renderPredictions()` consumes selector-derived prediction views/groups.
- `renderEvaluations()` consumes selector-derived evaluation context/groups.
- `renderEvaluationPlots()` consumes selector-derived evaluation context/plot groups.
- Prediction render / grouping / plot paths now reuse shared derived `predictionFields` instead of repeatedly re-deriving them in hot loops.
- Post-load imperative work is limited to resetting load-dependent UI state in `resetDerivedUiStateAfterLoad()`.

### Why this is better

- Canonical data, derived view models, and UI state now have much clearer boundaries.
- Rendering code is less responsible for building persistent intermediate structures.
- The dashboard is in a much better position for later modularization.

## General

- Add docstrings to all new or adjusted methods.
- At the end of each cleanup/refactor phase, provide a concise commit message that clearly describes the changes and architecture impact.

## Completed refactor

### Goal

Replace the old string/prefix-based evaluation field model with a typed field-descriptor layer.

### Why this is needed

- The dashboard still needs a runtime-discovered set of scalar fields for:
  - table columns
  - grouping
  - sorting
  - missing-value/default handling
  - plot grouping
- The current implementation represents those fields as strings and recovers meaning through prefix checks such as:
  - `job_return_value.`
  - `eval.`
- That works, but it leaks source structure into UI logic and spreads field semantics across string parsing helpers.

### Better target model

Keep canonical nested evaluation data as-is, but derive typed field descriptors instead of prefix-encoded string columns.

Example shape:

```js
{
  id: "eval:jrv:duration",
  scope: "evaluation",
  source: "jobReturnValue",
  section: "job_return_value",
  path: ["duration"],
  label: "duration",
  getRawValue: (evaluation) => getValueAtPath(evaluation.jobReturnValue, ["duration"]),
}
```

Similarly for override fields:

```js
{
  id: "eval:override:metric.field",
  scope: "evaluation",
  source: "overrides",
  section: "overrides",
  key: "metric.field",
  label: "metric.field",
  getRawValue: (evaluation) => evaluation.overrides?.["metric.field"],
}
```

### Architectural intent

- Field identity should no longer be inferred from string prefixes.
- Sectioning, labeling, sorting, grouping, and default handling should rely on field metadata.
- Mixed prediction/evaluation plot grouping should work on field descriptors, not prefixed strings.

### Implemented migration

1. Added evaluation field descriptors derived from:
   - `evaluation.runDir`
   - `evaluation.overrides`
   - scalar leaves in `evaluation.jobReturnValue`
2. Switched evaluation rendering to consume descriptor arrays instead of string columns.
3. Switched evaluation grouping/sorting/default handling to descriptor ids.
4. Switched plot grouping to mixed descriptor lists instead of `eval.`-prefixed fields.
5. Removed `EVAL_METADATA_COLUMN_PREFIX` / `EVAL_FIELD_GROUP_PREFIX` from active code.
6. Later completed the matching prediction-side descriptor layer while preserving current prediction field ids in UI state.

### Benefits

- Clearer semantics
- Less string parsing and prefix matching
- Better modularization seams
- Easier future schema evolution

### Risks

- Larger refactor than the earlier selector passes
- UI state currently keyed by strings will need stable descriptor ids
- Group-id stability and selection persistence need careful validation during migration

## Cleanup step

This should be split into two parts.

- [x] Cleanup A completed
- [x] Field-descriptor refactor completed
- [x] Cleanup B completed

### Cleanup A — do before the field-descriptor refactor

These are very low-risk and reduce noise without causing churn in the upcoming field-model refactor.

#### A1. Remove dead helpers

- Candidates:
  - `getVaryingGroupByFields(...)`
  - `getPredictionGroupDisplayLabel(...)`
- Why:
  - both appear unused after the selector refactor
  - active code paths already use `getVaryingFields(...)` and `getGroupLabelForFields(...)`
- Risk: very low

#### A2. Remove trivial unused leftovers

- Candidates:
  - unused `evalJsonPane`
  - unused parameter in `getDefaultEvalTruncateColumns(evalColumns)`
- Why:
  - easy warning reduction without behavior change
- Risk: very low

#### A3. Finish tiny naming/doc cleanup leftovers

- Candidates:
  - rename `predictionEntry` parameter in `getPredictionMemberSortValue(...)` to `predictionView`
  - add a short docstring to `syncSelectedGroupIds(...)`
- Why:
  - small consistency cleanup after the selector refactor
- Risk: very low

### Cleanup B — do after the field-descriptor refactor

These are still good cleanups, but they touch code that the descriptor refactor is likely to reshape.

#### B1. Reuse one selection-summary helper for evaluations

- Current situation:
  - prediction rendering uses `getDisplayedSelectionState(...)`
  - evaluation rendering rebuilds the same `displayedGroupIds / selectedCount / allSelected / someSelected` logic inline
- Why:
  - obvious duplication
  - but evaluation rendering will likely change during the descriptor migration
- Risk: low

#### B2. Merge `createCell(...)` and `createEvalCell(...)`

- Current situation:
  - both helpers create a table cell and optionally apply `truncate-enabled`
  - the only real difference is which truncate-state set they read
- Why:
  - straightforward deduplication
  - but likely easier to do after the render layer settles again
- Risk: low

#### B3. Merge mixed-value display logic

- Current situation:
  - `getGroupValueDisplay(...)`
  - `getGroupValueDisplayFromEvaluations(...)`
  - both implement the same “single value vs `(mixed: N values)`” behavior
- Why:
  - can be reduced to one generic helper with small wrappers if needed
  - but likely easier after field access becomes descriptor-based
- Risk: low

## Optional symmetry follow-up completed

- Prediction-side field discovery, labeling, grouping defaults, truncation defaults, missing-value/default controls, header sectioning, and plot-field wrapping now use typed prediction field descriptors.
- Existing prediction UI state remains keyed by the same flattened prediction field ids, so grouping/sorting/default/truncation behavior stays compatible while the internal model becomes symmetric with the evaluation side.

### Post-symmetry follow-up work

- Fixed one prediction-table render regression introduced during the symmetry refactor: prediction header sections now consistently use the new `{ label, fields }` shape in `renderPredictions()` instead of the removed legacy `section.columns` shape.
- Added a small performance pass after the prediction descriptor migration:
  - precompute `predictionFields` once per render / grouping context
  - thread those fields through prediction grouping, sorting, defaults, rendering, evaluation grouping, and plot grouping
  - avoid repeated full prediction-field derivation from default-parameter fallbacks inside hot loops

## Suggested order

1. Optional later follow-up: modularize the dashboard now that both prediction and evaluation selector/field layers are explicit.
