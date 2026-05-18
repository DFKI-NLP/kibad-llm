# Eval Dashboard Refactor Plan

## Implementation status

- [x] Canonical dashboard state uses `predictions` + `evaluations`
- [x] Prediction/evaluation terminology cleanup is in place
- [x] Refactor plan documented in this file
- [x] Phase 1: selector bridge introduced for prediction views/groups/selection
- [x] Phase 2: remove stored `state.predictionEntries`
- [x] Phase 3: remove stored `state.groups`
- [x] Phase 4: make evaluation grouping selector-driven
- [ ] Phase 5: simplify or remove `rebuildPredictionState()`

### Current architecture snapshot

- Canonical imported data lives in `state.predictions` and `state.evaluations`.
- Prediction-side grouping and selection are derived through selector helpers.
- Evaluation-side tabs, columns, groups, selected groups, and plot-group inputs are now derived through selector helpers.
- Remaining imperative cleanup is concentrated in `rebuildPredictionState()` and related load/reset paths.

## General

- Add docstrings to all new or adjusted methods.
- At the end of each phase, provide a concise commit message that clearly describes the changes and the new architecture.

## Core diagnosis

The current issue is not really `predictionEntries` itself. The issue is that `docs/eval-dashboard.html` still mixes three different layers:

1. **Canonical data**
   - `state.predictions`
   - `state.evaluations`
2. **Derived data / view models**
   - currently things like `predictionEntries`
   - current prediction/evaluation group structures
   - flattened prediction/evaluation access
3. **UI state**
   - grouping choices
   - sort state
   - defaults
   - expanded/selected groups
   - active tabs

That mixing causes two problems:

- responsibility drift: render functions are also partly data-build functions
- modularization gets harder, because there is no clean seam between “data shaping” and “DOM rendering”

So I think the right direction is:

> keep only canonical entities + UI state in state, and move the rest into pure derived selectors/view-model builders.

## Target architecture

### 1) Canonical state

This should remain the only real data store:

```js
state = {
  predictions: {
    [predictionId]: {
      jobReturnValue,
      overrides,
    },
  },

  evaluations: [
    {
      runDir,
      predictionId,
      jobReturnValue,
      overrides,
      data,
    },
  ],

  // UI state only
  predictionSort: [],
  selectedGroupIds: new Set(),
  expandedGroupIds: new Set(),
  groupByFields: [],
  predictionDefaultValues: {},
  evalTabStates: {},
  activeEvalTab: null,
  activeEvalJsonTab: "evaluation",
  ...
}
```

#### Important rule

Only keep things in state if they are:

- canonical imported data
- or true UI state

Everything else should be derived.

### 2) Derived selectors / view models

These should become pure functions, not persistent stored state.

Examples of target derived layers:

#### Prediction record layer

One per prediction id:

```js
{
  predictionId,
  predictionFlat,
  evaluations,
}
```

This is basically the current `predictionEntries`, but treated explicitly as:

- derived
- selector output
- not canonical mutable state

I would call these something like:

- `predictionViews`
- or `predictionRecords`

My preference: `predictionViews`

#### Prediction group layer

Built from prediction views + UI grouping settings:

```js
{
  groupId,
  predictions: [predictionView, ...],
  values,
}
```

This is the current `state.groups`, but it should also become derived, not stored.

#### Evaluation group layer

Built from:

- selected prediction groups or selected prediction ids
- selected experiment
- eval group-by config

Again: derived, not stored.

### 3) Rendering layer

`renderPredictions()` and `renderEvaluations()` should become consumers of selectors, not builders of core data structures.

That means:

- no more “rebuild state, then render”
- more “compute view model, then render”

That is much cleaner for later modularization.

## What should happen to `predictionEntries`

### Recommendation

Do not keep `state.predictionEntries` as stored mutable state.

Instead:

- replace it with a pure selector:
  - `getPredictionViews()`
  - or `buildPredictionViews()`

This selector returns the current shape:

```js
[
  {
    predictionId,
    predictionFlat,
    evaluations,
  },
]
```

Then later we can rename the shape itself more cleanly without worrying about global mutable state.

So I would say the future is:

- current `predictionEntries` responsibility survives
- but as a derived selector result, not as state

That is the important architectural fix.

## Refactor plan

### Phase 1 — make the layers explicit without changing behavior

**Goal:** introduce selector-based architecture while preserving current outputs.

**Work**

Add a dedicated selector section:

- `getPredictionViews()`
- `getPredictionColumns(predictionViews)`
- `getPredictionGroups(predictionViews, groupByFields, defaults)`
- `getSelectedPredictionGroups(...)`
- `getSelectedEvaluations(...)`

Make these selectors initially return the same shapes the render code already expects:

- prediction view objects compatible with current `predictionEntries`
- prediction groups compatible with current `groups`

Keep `state.predictionEntries` and `state.groups` temporarily during the transition.

**Why**

This gives us a compatibility bridge with low risk.

### Phase 2 — stop storing `predictionEntries`

**Goal:** make prediction rows fully derived.

**Work**

- Remove writes to `state.predictionEntries` from `rebuildPredictionState()`
- Replace reads of `state.predictionEntries` with `getPredictionViews()`
- Update functions like:
  - `getDefaultGroupByFields()`
  - prediction missing/default helpers
  - prediction sorting helpers
  - prediction summary rendering

**Result**

The Predictions table now consumes derived prediction views directly.

### Phase 3 — stop storing `state.groups`

**Goal:** make prediction grouping fully derived.

**Work**

- Replace `buildGroups()` mutating `state.groups` with pure:
  - `getPredictionGroups(...)`
- Update:
  - `renderPredictions()`
  - `gatherSelectedEvaluations()`
  - any group summary/selection helper
- Keep only selection state in state:
  - selected ids
  - expanded ids

**Result**

Grouping is now a pure function of:

- prediction views
- groupBy config
- defaults

### Phase 4 — make evaluation grouping fully selector-driven

**Goal:** apply the same discipline to evaluation-side grouping.

**Work**

- Keep canonical evaluation data in `state.evaluations`
- Derive:
  - active experiment evaluations
  - evaluation columns
  - evaluation groups
  - plot groups
- Ensure evaluation rendering and plot rendering only consume selector outputs

**Result**

Evaluation tabs/plots no longer depend on mixed mutable intermediate state.

### Phase 5 — simplify or remove `rebuildPredictionState()`

**Goal:** reduce imperative recomputation.

**Work**

After phases 2–4, `rebuildPredictionState()` should shrink dramatically.

Ideally it only does:

- reset UI state that logically depends on loaded data
- maybe recompute trivial defaults once if you still want eager initialization

Or it disappears entirely and becomes:

```js
resetDerivedUiStateAfterLoad()
```

This is a big clarity win.

## Concrete target module seams for later modularization

This refactor prepares exactly the seams you’ll want later:

### A. canonical-data module

- loading
- normalization
- import validation
- prediction id handling

### B. selectors module

- `getPredictionViews()`
- `getPredictionGroups()`
- `getSelectedEvaluations()`
- `getEvaluationColumns()`
- `getEvaluationGroups()`
- plot/confusion selectors

### C. prediction rendering module

- Predictions table rendering only

### D. evaluation rendering module

- Evaluations table + JSON pane

### E. plot/confusion rendering module

This is why the selector refactor matters now.

## Highest-risk transitions

### 1) Selection persistence

Right now selection is tied to group ids. If we recompute groups differently, selection could break.

**Plan**

Keep current group-id generation semantics initially. Do not change group-id format in the same pass.

### 2) Default-value behavior

Prediction/evaluation defaults influence grouping and display. If selectors compute effective values differently, grouping may shift subtly.

**Plan**

Move current logic as-is into selectors first. Do not redesign effective/default semantics during this refactor.

### 3) Evaluation plot grouping

This depends on prediction grouping + evaluation grouping + experiment slicing. It is easy to regress.

**Plan**

Refactor this only after prediction selectors and evaluation selectors are already stabilized.

## Validation strategy

I would explicitly validate after each phase.

### Invariants to check

For the same loaded dataset:

- number of canonical predictions unchanged
- number of canonical evaluations unchanged
- number of prediction views unchanged
- number of prediction groups unchanged
- group membership unchanged
- selected prediction groups still map to the same evaluations
- evaluation tab counts unchanged
- plot group membership unchanged

### Good practical smoke tests

- load real multirun data
- compare:
  - prediction count
  - group count
  - selected evaluations count
  - eval tabs and counts
  - confusion-tab counts
- run focused selector smoke tests in Node, like we already did

## Design decisions to settle before coding

These are the only ones I think we should decide first.

### 1) Name of the derived per-prediction selector output

**Options:**

- `predictionViews`
- `predictionRows`
- `predictionRecords`

**My recommendation:** `predictionViews`

**Why:**

- clearly derived
- not canonical
- broader than just DOM rows

### 2) Keep current group ids or redesign them?

**My recommendation:** keep current group-id semantics for now

**Reason:**

- avoids selection regressions
- lower-risk transition
- can be revisited later

### 3) Should derived selectors be cached/memoized?

**My recommendation:** no memoization initially

**Reason:**

- simpler
- easier to trust during refactor
- can add memoization later if performance matters

### 4) Do we keep `predictionColumns` in state?

I would prefer eventually deriving it too.

But for a staged refactor, it is okay to leave it briefly and remove it after prediction views are selector-driven.

So:

- short term: can stay
- medium term: should become derived

## My recommended plan in one sentence

Move from “stored derived structures plus rendering” to “canonical entities + pure selectors + UI state,” starting by replacing `state.predictionEntries` with a derived `predictionViews` selector, then doing the same for `state.groups`.

## What I would implement first

If we move ahead, I would do this exact order:

1. introduce `getPredictionViews()`
2. introduce `getPredictionGroups()`
3. switch prediction-side consumers to selectors
4. remove stored `state.predictionEntries`
5. remove stored `state.groups`
6. then do the same pattern on evaluation-side grouping

That gives the cleanest architecture with manageable risk.

If you want, next I can turn this into a phase-by-phase implementation checklist mapped to exact functions in `docs/eval-dashboard.html`, so we can execute the refactor in controlled steps.
