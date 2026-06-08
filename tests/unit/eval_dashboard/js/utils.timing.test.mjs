/**
 * Tests for eval-dashboard debug timing helpers.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  createTimingCollector,
  getTimingNow,
  isDebugTimingEnabled,
} from "../../../../docs/eval-dashboard/assets/js/utils/timing.js";

/**
 * Verify URL query parsing enables timing only for explicit truthy values.
 */
test("timing helper resolves debug query parameter values", () => {
  assert.equal(isDebugTimingEnabled({ locationLike: { search: "" } }), false);
  assert.equal(isDebugTimingEnabled({ locationLike: { search: "?debugTiming=0" } }), false);
  assert.equal(isDebugTimingEnabled({ locationLike: { search: "?debugTiming=false" } }), false);
  assert.equal(isDebugTimingEnabled({ locationLike: { search: "?debugTiming" } }), true);
  assert.equal(isDebugTimingEnabled({ locationLike: { search: "?debugTiming=1" } }), true);
  assert.equal(isDebugTimingEnabled({ locationLike: { search: "?debugTiming=true" } }), true);
});

/**
 * Verify timing collectors keep disabled mode side-effect free and log enabled records.
 */
test("timing collector records, flushes, and clears enabled timings", async () => {
  assert.equal(getTimingNow({ now: () => 12.5 }), 12.5);

  const disabled = createTimingCollector({ enabled: false });
  assert.equal(disabled.time("disabled", () => "result"), "result");
  assert.deepEqual(disabled.flush(), []);

  const times = [10, 14, 20, 25];
  const tables = [];
  const timing = createTimingCollector({
    enabled: true,
    label: "test timing",
    performanceLike: { now: () => times.shift() },
    consoleLike: { table: (rows) => tables.push(rows) },
  });

  assert.equal(timing.time("sync stage", () => "ok", { group: "a" }), "ok");
  assert.equal(await timing.timeAsync("async stage", async () => "async ok"), "async ok");

  const rows = timing.flush({ source: "fixture" });
  assert.equal(rows.length, 2);
  assert.deepEqual(rows.map((row) => row.stage), ["sync stage", "async stage"]);
  assert.deepEqual(rows.map((row) => row.duration_ms), [4, 5]);
  assert.equal(rows[0].source, "fixture");
  assert.equal(rows[0].group, "a");
  assert.deepEqual(tables[0], rows);
  assert.deepEqual(timing.flush(), []);
});
