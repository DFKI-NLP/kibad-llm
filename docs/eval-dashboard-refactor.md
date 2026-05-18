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
  - `getCurrentPredictionColumns()`
  - `getCurrentPredictionGroups()`
- Evaluation-side derived structures are built through selectors such as:
  - `getEvaluationContext()`
  - `getSelectedEvaluationGroups()`
  - `getPlotGroups()`

### Rendering flow

- `renderPredictions()` consumes selector-derived prediction views/groups.
- `renderEvaluations()` consumes selector-derived evaluation context/groups.
- `renderEvaluationPlots()` consumes selector-derived evaluation context/plot groups.
- Post-load imperative work is limited to resetting load-dependent UI state in `resetDerivedUiStateAfterLoad()`.

### Why this is better

- Canonical data, derived view models, and UI state now have much clearer boundaries.
- Rendering code is less responsible for building persistent intermediate structures.
- The dashboard is in a much better position for later modularization.

## General

- Add docstrings to all new or adjusted methods.
- At the end of each cleanup/refactor phase, provide a concise commit message that clearly describes the changes and architecture impact.

## Next easy cleanup steps

### 1. Remove dead helpers

- Candidates:
  - `getVaryingGroupByFields(...)`
  - `getPredictionGroupDisplayLabel(...)`
- Why:
  - both appear unused after the selector refactor
  - active code paths already use `getVaryingFields(...)` and `getGroupLabelForFields(...)`
- Risk: very low

### 2. Reuse one selection-summary helper for evaluations

- Current situation:
  - prediction rendering uses `getDisplayedSelectionState(...)`
  - evaluation rendering rebuilds the same `displayedGroupIds / selectedCount / allSelected / someSelected` logic inline
- Why:
  - obvious duplication
  - low-risk extraction or generalization
- Risk: low

### 3. Merge `createCell(...)` and `createEvalCell(...)`

- Current situation:
  - both helpers create a table cell and optionally apply `truncate-enabled`
  - the only real difference is which truncate-state set they read
- Why:
  - straightforward deduplication
- Risk: low

### 4. Merge mixed-value display logic

- Current situation:
  - `getGroupValueDisplay(...)`
  - `getGroupValueDisplayFromEvaluations(...)`
  - both implement the same “single value vs `(mixed: N values)`” behavior
- Why:
  - can be reduced to one generic helper with small wrappers if needed
- Risk: low

### 5. Finish tiny naming/doc cleanup leftovers

- Candidates:
  - rename `predictionEntry` parameter in `getPredictionMemberSortValue(...)` to `predictionView`
  - add a short docstring to `syncSelectedGroupIds(...)`
- Why:
  - small consistency cleanup after the selector refactor
- Risk: very low

### 6. Remove trivial unused leftovers

- Candidates:
  - unused `evalJsonPane`
  - unused parameter in `getDefaultEvalTruncateColumns(evalColumns)`
- Why:
  - easy warning reduction without behavior change
- Risk: very low

## Suggested order

1. Remove dead helpers
2. Remove trivial unused leftovers
3. Unify selection-summary logic
4. Unify cell creation
5. Unify mixed-value display
6. Finish tiny naming/doc cleanup
