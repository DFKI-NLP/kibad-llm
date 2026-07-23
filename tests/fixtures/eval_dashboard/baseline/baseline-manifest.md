# Eval dashboard baseline manifest

## Purpose

This baseline captures the current behavior of the monolithic eval dashboard implementation before CSS/JS modularization.

The baseline was recorded during the Phase 0/1 migration window on 2026-05-27.
It is intended to preserve behavior while the dashboard runtime entrypoint remains at `docs/eval-dashboard/index.html` and the implementation is split into modules.

## Current implementation shape

- runtime page: `docs/eval-dashboard/index.html`
- compatibility path: none; the temporary `docs/eval-dashboard.html` shim has been retired
- implementation style: single static HTML page with large inline CSS and inline JavaScript
- CSS extraction status: not started
- JavaScript extraction status: not started

## Baseline feature expectations

The dashboard should continue to support these feature families during refactoring:

- loading local evaluation folders/files
- loading runs from a GitHub URL
- prediction grouping and group expansion
- experiment/evaluation tabs
- JSON side pane synchronization
- grouped bar plots
- error plots
- confusion matrix plots
- TP/FP/FN plots
- figure download/export state
- light/dark styling

## Recommended source experiments for fixture curation

Prefer curated snapshots derived from representative runs documented in `data/results/readme.md`, especially runs added later than `2026-01-16`.

Recommended candidates:

- `311_better_default_temperature`
- `327_faktencheck_core_with_persona`
- `333_organism_trends_with_persona`
- `380_faktencheck_core`
- `380_organism_trends`
- `397_faktencheck_core_v1_for_chunking`
- `422_organism_trends`
- `428_organism_trends_with_chunking`
- `454_faktencheck_core`
- `477_faktencheck_core`
- `477_organism_trends`
- `481_faktencheck_core`

If an older run is added as an edge-case fixture, document why it is still needed.

## Phase 0/1 validation notes

Manual validation target for this baseline:

1. build the docs site
2. open the dashboard
3. verify the feature families above still behave as expected
4. confirm the runtime entry path works

## Baseline artifact contents

- `baseline-manifest.md`: human-readable rationale and expectations
- `baseline-summary.json`: machine-checkable summary of the baseline
- `optional-screenshots/`: optional visual references if later needed

## Phase 3 guardrail

Phase 3 is intentionally limited to CSS extraction.
While `docs/eval-dashboard/index.html` is switched from inline CSS to `assets/css/index.css`, the lone inline `<script>` block is expected to remain behavior-equivalent until Phase 4 moves it to an external JS file.

To make that constraint reviewable, `baseline-summary.json` includes a normalized inline-script fingerprint that Phase 3 tests compare against.
