/**
 * Browser-free logic tests for the eval-dashboard state-store helpers.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  SORTABLE_CONTROL_COLUMNS,
  createInitialDashboardState,
  ensureEvalTabState,
  resetDerivedUiStateAfterLoad,
  syncEvaluationGroupUiState,
  syncPredictionGroupUiState,
  syncSelectedGroupIds,
} from "../../../../docs/eval-dashboard/assets/js/state/store.js";

/**
 * Ensure fresh dashboard state objects do not share mutable containers.
 */
test("store creates isolated dashboard state containers", () => {
  const first = createInitialDashboardState();
  const second = createInitialDashboardState();

  first.loadedFolders.add("run-a");
  first.selectedGroupIds.add("group-a");
  first.evalTabStates.expA = { knownColumns: ["a"] };

  assert.deepEqual([...SORTABLE_CONTROL_COLUMNS], ["expand", "select", "group_size"]);
  assert.equal(second.loadedFolders.size, 0);
  assert.equal(second.selectedGroupIds.size, 0);
  assert.deepEqual(second.evalTabStates, {});
});

/**
 * Ensure selection synchronization preserves valid ids and auto-selects newly introduced groups.
 */
test("store syncs selected group ids against current valid ids", () => {
  const selectionState = {
    selectedGroupIds: new Set(["stable", "stale"]),
    availableGroupIds: new Set(["stable", "old"]),
  };

  syncSelectedGroupIds(selectionState, ["stable", "new"]);

  assert.deepEqual([...selectionState.selectedGroupIds].sort(), ["new", "stable"]);
  assert.deepEqual([...selectionState.availableGroupIds].sort(), ["new", "stable"]);
});

/**
 * Ensure prediction-group UI state auto-selects all currently valid groups when the
 * persisted selection state is still uninitialized.
 */
test("store auto-selects all prediction groups when selection starts as null", () => {
  const state = createInitialDashboardState();
  state.selectedGroupIds = null;
  state.availableGroupIds = new Set(["old-group"]);
  state.expandedGroupIds = new Set(["stale-group", "group-b"]);

  syncPredictionGroupUiState(state, [{ groupId: "group-a" }, { groupId: "group-b" }]);

  assert.deepEqual([...state.selectedGroupIds].sort(), ["group-a", "group-b"]);
  assert.deepEqual([...state.availableGroupIds].sort(), ["group-a", "group-b"]);
  assert.deepEqual([...state.expandedGroupIds], ["group-b"]);
});

/**
 * Ensure evaluation-tab state initialization and normalization stay behavior-equivalent after extraction.
 */
test("store initializes and normalizes eval-tab state", () => {
  const state = createInitialDashboardState();
  const evaluations = [
    { overrides: { alpha: "x", beta: "same" } },
    { overrides: { alpha: "y", beta: "same" } },
  ];

  const tabState = ensureEvalTabState(state, "exp-a", ["alpha", "beta"], {
    evaluations,
    getDefaultEvalGroupByFields: (columns, rows) => (
      columns.includes("alpha") && rows.length > 0 ? ["alpha"] : []
    ),
  });

  tabState.sort = [
    { column: "alpha", direction: "asc" },
    { column: "missing", direction: "desc" },
  ];
  tabState.truncateEnabledColumns = new Set(["alpha", "missing", "eval_run_dir"]);
  tabState.groupByFields = ["alpha", "missing"];

  const normalizedTabState = ensureEvalTabState(state, "exp-a", ["alpha", "beta", "gamma"], {
    evaluations,
    getDefaultEvalGroupByFields: (columns) => (columns.includes("gamma") ? ["gamma"] : []),
  });

  assert.equal(normalizedTabState, tabState);
  assert.deepEqual(normalizedTabState.knownColumns.sort(), ["alpha", "beta", "gamma"]);
  assert.deepEqual(normalizedTabState.groupByFields.sort(), ["alpha", "gamma"]);
  assert.deepEqual(normalizedTabState.sort, [{ column: "alpha", direction: "asc" }]);
  assert.deepEqual([...normalizedTabState.truncateEnabledColumns].sort(), ["alpha", "eval_run_dir"]);
});

/**
 * Ensure malformed persisted eval-tab state is normalized back into the canonical shape.
 */
test("store repairs malformed persisted eval-tab state", () => {
  const state = createInitialDashboardState();
  state.evalTabStates["exp-a"] = {
    knownColumns: ["alpha"],
    groupByFields: "alpha",
    sort: { column: "alpha", direction: "desc" },
    truncateEnabledColumns: ["alpha"],
    defaultValues: "invalid",
    activeOptionsTab: "",
    availableGroupIds: ["group-a"],
    expandedGroupIds: { bad: true },
  };

  const normalizedTabState = ensureEvalTabState(state, "exp-a", ["alpha"], {
    evaluations: [{ overrides: { alpha: "x" } }],
  });

  assert.deepEqual(normalizedTabState.groupByFields, []);
  assert.deepEqual(normalizedTabState.sort, []);
  assert.ok(normalizedTabState.truncateEnabledColumns instanceof Set);
  assert.deepEqual([...normalizedTabState.truncateEnabledColumns], []);
  assert.deepEqual(normalizedTabState.defaultValues, {});
  assert.equal(normalizedTabState.activeOptionsTab, "truncate");
  assert.ok(normalizedTabState.availableGroupIds instanceof Set);
  assert.deepEqual([...normalizedTabState.availableGroupIds], []);
  assert.ok(normalizedTabState.expandedGroupIds instanceof Set);
  assert.deepEqual([...normalizedTabState.expandedGroupIds], []);
});

/**
 * Ensure evaluation-group UI state clears stale group and run selections after regrouping.
 */
test("store clears stale evaluation selections and run targets after regrouping", () => {
  const evalTabState = {
    selectedGroupIds: null,
    availableGroupIds: new Set(["old-group"]),
    expandedGroupIds: new Set(["stale-group", "group-b"]),
    selectedEvalGroupId: "stale-group",
    selectedEvalRunId: "run-stale",
  };

  syncEvaluationGroupUiState(
    evalTabState,
    [{ groupId: "group-a" }, { groupId: "group-b" }],
    [{ runId: "run-a", runDir: "runs/a" }, { runId: "run-b", runDir: "runs/b" }]
  );

  assert.deepEqual([...evalTabState.selectedGroupIds].sort(), ["group-a", "group-b"]);
  assert.deepEqual([...evalTabState.availableGroupIds].sort(), ["group-a", "group-b"]);
  assert.deepEqual([...evalTabState.expandedGroupIds], ["group-b"]);
  assert.equal(evalTabState.selectedEvalGroupId, null);
  assert.equal(evalTabState.selectedEvalRunId, null);
});

/**
 * Ensure post-load state reset keeps canonical data but clears derived UI state.
 */
test("store resets derived ui state after loading data", () => {
  const state = createInitialDashboardState();
  state.groupByFields = ["old-group"];
  state.predictionSort = [{ column: "old", direction: "desc" }];
  state.truncateEnabledColumns = new Set(["old"]);
  state.predictionDefaultValues = { old: "fallback" };
  state.selectedGroupIds = new Set(["stale"]);
  state.availableGroupIds = new Set(["stale"]);
  state.expandedGroupIds = new Set(["stale"]);
  state.activeEvalTab = "old-exp";
  state.evalTabStates = { "old-exp": { groupByFields: ["old"] } };
  state.activeEvalJsonTab = "prediction";
  state.activeEvalPlotTab = "plot-a";
  state.plotGroupBarFields = new Set(["metric.field"]);
  state.activePlotLegendItems = [{ label: "old" }];

  resetDerivedUiStateAfterLoad(state, {
    predictionViews: [{ predictionId: "pred-a" }],
    predictionColumns: ["prediction.overrides.model", "prediction.overrides.seed"],
    predictionGroups: [{ groupId: "group-a" }, { groupId: "group-b" }],
    getDefaultGroupByFields: (columns) => columns.filter((column) => column.endsWith("model")),
    getDefaultTruncateColumns: (columns) => new Set(columns.filter((column) => column.endsWith("seed"))),
  });

  assert.deepEqual(state.groupByFields, ["prediction.overrides.model"]);
  assert.deepEqual(state.predictionSort, []);
  assert.deepEqual([...state.truncateEnabledColumns], ["prediction.overrides.seed"]);
  assert.deepEqual(state.predictionDefaultValues, {});
  assert.equal(state.activeEvalTab, null);
  assert.deepEqual(state.evalTabStates, {});
  assert.equal(state.activeEvalJsonTab, "evaluation");
  assert.equal(state.activeEvalPlotTab, null);
  assert.deepEqual([...state.plotGroupBarFields], []);
  assert.deepEqual(state.activePlotLegendItems, []);
  assert.deepEqual([...state.selectedGroupIds].sort(), ["group-a", "group-b"]);
  assert.deepEqual([...state.availableGroupIds].sort(), ["group-a", "group-b"]);
  assert.deepEqual([...state.expandedGroupIds], []);
});
