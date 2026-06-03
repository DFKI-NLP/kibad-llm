import test from "node:test";
import assert from "node:assert/strict";

import {
  buildPlotTabZipFilename,
  computeCrc32,
  concatUint8Arrays,
  createZipBlob,
  getSvgExportViewBox,
  getUniqueFigureFilename,
  resolveOpaqueExportBackgroundColor,
} from "../../../../docs/eval-dashboard/assets/js/plots/export.js";

test("export helpers derive stable figure and archive filenames", () => {
  const usedNames = new Set();
  assert.equal(getUniqueFigureFilename("Accuracy / macro F1", usedNames), "Accuracy - macro F1.svg");
  assert.equal(getUniqueFigureFilename("Accuracy / macro F1", usedNames), "Accuracy - macro F1 (2).svg");
  assert.equal(
    buildPlotTabZipFilename({ activeEvalTab: "experiment/a", activePlotTabLabel: "score.mean" }),
    "experiment - a-score.mean.zip"
  );
  assert.equal(buildPlotTabZipFilename({ activeEvalTab: "", activePlotTabLabel: "" }), "figures.zip");
});

test("export helpers parse SVG viewBox values and choose opaque backgrounds", () => {
  assert.deepEqual(
    getSvgExportViewBox({ getAttribute: () => "1 2 300 400" }, "10", "20"),
    { minX: 1, minY: 2, width: 300, height: 400 }
  );
  assert.deepEqual(
    getSvgExportViewBox({ getAttribute: () => "bad" }, "10", "20"),
    { minX: 0, minY: 0, width: 10, height: 20 }
  );
  assert.equal(
    resolveOpaqueExportBackgroundColor(["transparent", "rgb(1, 2, 3)"], (value) => ({ backgroundColor: value })),
    "rgb(1, 2, 3)"
  );
  assert.equal(
    resolveOpaqueExportBackgroundColor(["transparent"], (value) => ({ backgroundColor: value })),
    "#ffffff"
  );
});

test("export helpers compute crc32 and create uncompressed zip blobs", async () => {
  assert.equal(computeCrc32(new TextEncoder().encode("hello")), 0x3610a686);
  assert.deepEqual(
    Array.from(concatUint8Arrays([new Uint8Array([1, 2]), new Uint8Array([3])])),
    [1, 2, 3]
  );

  const blob = createZipBlob(
    [{ name: "a.txt", content: "hello" }],
    { date: new Date("2026-06-03T12:34:56Z") }
  );
  assert.equal(blob.type, "application/zip");
  const bytes = new Uint8Array(await blob.arrayBuffer());
  assert.deepEqual(Array.from(bytes.slice(0, 4)), [0x50, 0x4b, 0x03, 0x04]);
  assert.deepEqual(Array.from(bytes.slice(-22, -18)), [0x50, 0x4b, 0x05, 0x06]);
});
