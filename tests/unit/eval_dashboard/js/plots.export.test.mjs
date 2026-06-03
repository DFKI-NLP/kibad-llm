/**
 * Tests for eval-dashboard plot export helper seams.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  buildVisibleFigureFiles,
  buildPlotTabZipFilename,
  computeCrc32,
  concatUint8Arrays,
  createZipBlob,
  downloadVisibleFigures,
  getActivePlotTabZipFilename,
  getSvgExportViewBox,
  getUniqueFigureFilename,
  getVisiblePlotFigureCards,
  hideTooltip,
  measureCanvasText,
  positionTooltip,
  resolveOpaqueExportBackgroundColor,
  saveBlob,
  serializeLegendSvg,
  serializeSvgForDownload,
  showTooltip,
  triggerBlobDownload,
  writeTextToClipboard,
} from "../../../../docs/eval-dashboard/assets/js/plots/export.js";
import { createDocumentStub, serializeFakeSvg } from "./plots.dom-test-helpers.mjs";

/**
 * Verify figure and archive filenames preserve the dashboard's sanitizer contract.
 */
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

/**
 * Verify SVG export fallback geometry and opaque-background selection.
 */
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

/**
 * Verify custom CRC32, byte concatenation, and uncompressed ZIP archive assembly.
 */
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

/**
 * Verify tooltip helpers position, show, and hide the shared plot tooltip.
 */
test("export helpers position and toggle plot tooltips", () => {
  const tooltipElement = { offsetWidth: 60, offsetHeight: 20, style: {}, textContent: "" };
  showTooltip({
    tooltipElement,
    windowLike: { innerWidth: 200 },
    event: { clientX: 150, clientY: 10 },
    lines: ["a", "b"],
  });
  assert.equal(tooltipElement.textContent, "a\nb");
  assert.equal(tooltipElement.style.display, "block");
  assert.equal(tooltipElement.style.left, "76px");
  assert.equal(tooltipElement.style.top, "24px");

  positionTooltip({
    tooltipElement,
    windowLike: { innerWidth: 400 },
    event: { clientX: 20, clientY: 100 },
  });
  assert.equal(tooltipElement.style.left, "34px");
  assert.equal(tooltipElement.style.top, "66px");
  hideTooltip({ tooltipElement });
  assert.equal(tooltipElement.style.display, "none");
});

/**
 * Verify clipboard helper prefers the async clipboard API when present.
 */
test("export helpers write clipboard text through navigator clipboard", async () => {
  let written = "";
  await writeTextToClipboard({
    text: "payload",
    navigatorLike: { clipboard: { writeText: async (text) => { written = text; } } },
    documentLike: createDocumentStub(),
  });
  assert.equal(written, "payload");
});

/**
 * Verify clipboard helper falls back to a temporary textarea and reports copy failures.
 */
test("export helpers use textarea clipboard fallback", async () => {
  const documentLike = createDocumentStub();
  let command = "";
  documentLike.execCommand = (nextCommand) => {
    command = nextCommand;
    return true;
  };

  await writeTextToClipboard({ text: "fallback", navigatorLike: {}, documentLike });
  assert.equal(command, "copy");
  assert.equal(documentLike.body.children.length, 0);

  documentLike.execCommand = () => false;
  await assert.rejects(
    writeTextToClipboard({ text: "fallback", navigatorLike: {}, documentLike }),
    /Clipboard copy command/
  );
});

/**
 * Verify SVG serialization adds namespaces, computed styles, and optional opaque backgrounds.
 */
test("export helpers serialize figure and legend SVGs", () => {
  const documentLike = createDocumentStub();
  const svg = documentLike.createElementNS("", "svg");
  svg.setAttribute("width", "100");
  svg.setAttribute("height", "50");
  const serializer = { serializeToString: serializeFakeSvg };
  const computedStyle = { color: "#111111", fontFamily: "Inter", backgroundColor: "transparent" };

  const figure = serializeSvgForDownload({
    documentLike,
    serializer,
    sourceSvg: svg,
    computedStyle,
    exportOptions: { opaqueBackground: true, backgroundColor: "#ffffff" },
  });
  assert.match(figure, /^<\?xml/);
  assert.match(figure, /xmlns="http:\/\/www\.w3\.org\/2000\/svg"/);
  assert.match(figure, /fill="#ffffff"/);

  const legend = serializeLegendSvg({
    documentLike,
    serializer,
    legendItems: [{ label: "Series", color: "#ff0000" }],
    computedStyle,
    measureText: () => 40,
    exportOptions: { opaqueBackground: false },
  });
  assert.match(legend, /Series/);
  assert.match(legend, /#ff0000/);
  assert.equal(
    serializeLegendSvg({ documentLike, serializer, legendItems: [], computedStyle }),
    ""
  );
});

/**
 * Verify browser download fallback creates, clicks, removes, and revokes a temporary link.
 */
test("export helpers trigger blob downloads through object URLs", () => {
  const documentLike = createDocumentStub();
  let revoked = "";
  let timeoutDelay = 0;
  triggerBlobDownload({
    documentLike,
    urlLike: {
      createObjectURL: () => "blob:url",
      revokeObjectURL: (url) => {
        revoked = url;
      },
    },
    setTimeoutLike: (callback, delay) => {
      timeoutDelay = delay;
      callback();
    },
    filename: "figures.zip",
    blob: new Blob(["x"]),
  });

  assert.equal(documentLike.body.children.length, 0);
  assert.equal(timeoutDelay, 1000);
  assert.equal(revoked, "blob:url");
});

/**
 * Verify save helper handles save-picker success, user aborts, and download fallback.
 */
test("export helpers save blobs with picker or fallback", async () => {
  const writes = [];
  assert.equal(
    await saveBlob({
      windowLike: {
        showSaveFilePicker: async () => ({
          createWritable: async () => ({
            write: async (blob) => writes.push(blob),
            close: async () => writes.push("closed"),
          }),
        }),
      },
      blob: "zip",
      suggestedName: "figures.zip",
      types: [],
      triggerDownload: () => assert.fail("fallback should not run"),
    }),
    true
  );
  assert.deepEqual(writes, ["zip", "closed"]);

  assert.equal(
    await saveBlob({
      windowLike: { showSaveFilePicker: async () => { throw Object.assign(new Error("abort"), { name: "AbortError" }); } },
      blob: "zip",
      suggestedName: "figures.zip",
      types: [],
      triggerDownload: () => assert.fail("aborted save should not fallback"),
    }),
    false
  );

  let fallback = null;
  const warnings = [];
  assert.equal(
    await saveBlob({
      windowLike: { showSaveFilePicker: async () => { throw new Error("denied"); } },
      blob: "zip",
      suggestedName: "figures.zip",
      types: [],
      triggerDownload: (blob, filename) => {
        fallback = [blob, filename];
      },
      consoleLike: { warn: (...args) => warnings.push(args) },
    }),
    true
  );
  assert.deepEqual(fallback, ["zip", "figures.zip"]);
  assert.equal(warnings.length, 1);
});

/**
 * Verify visible figure collection and active-tab archive names are derived from DOM state.
 */
test("export helpers collect visible figure cards and active tab filenames", () => {
  const documentLike = createDocumentStub();
  const content = documentLike.createElement("div");
  const withSvg = documentLike.createElement("section");
  withSvg.className = "plot-card";
  withSvg.appendChild(documentLike.createElementNS("", "svg"));
  const withoutSvg = documentLike.createElement("section");
  withoutSvg.className = "plot-card";
  content.appendChild(withSvg);
  content.appendChild(withoutSvg);
  assert.deepEqual(getVisiblePlotFigureCards(content), [withSvg]);

  const tabs = documentLike.createElement("div");
  const active = documentLike.createElement("button");
  active.className = "tab-button active";
  active.setAttribute("title", "score.mean");
  tabs.appendChild(active);
  assert.equal(
    getActivePlotTabZipFilename({ activeEvalTab: "exp/a", evalPlotTabs: tabs }),
    "exp - a-score.mean.zip"
  );
});

/**
 * Verify visible figure file assembly and ZIP download orchestration.
 */
test("export helpers build visible figure files and download archives", async () => {
  const documentLike = createDocumentStub();
  const card = documentLike.createElement("section");
  card.className = "plot-card";
  const title = documentLike.createElement("p");
  title.className = "plot-title";
  title.textContent = "Score / Mean";
  card.appendChild(title);
  card.appendChild(documentLike.createElementNS("", "svg"));

  const files = buildVisibleFigureFiles({
    figureCards: [card],
    activePlotLegendItems: [{ key: "a", label: "A", color: "#111" }, { key: "b", label: "B", color: "#222" }],
    exportOptions: {},
    serializeLegend: () => "legend",
    serializeSvg: () => "svg",
  });
  assert.deepEqual(files.map((file) => file.filename), ["legend.svg", "Score - Mean.svg"]);

  let saved = null;
  const downloaded = await downloadVisibleFigures({
    figureCards: [card],
    activePlotLegendItems: [],
    exportOptions: {},
    serializeLegend: () => "",
    serializeSvg: () => "svg",
    createZip: (zipFiles) => ({ zipFiles }),
    saveZip: async (blob, filename, types) => {
      saved = { blob, filename, types };
      return true;
    },
    getZipFilename: () => "figures.zip",
  });
  assert.equal(downloaded, true);
  assert.equal(saved.filename, "figures.zip");
  assert.deepEqual(saved.blob.zipFiles, [{ name: "Score - Mean.svg", content: "svg" }]);

  assert.equal(
    await downloadVisibleFigures({
      figureCards: [],
      activePlotLegendItems: [],
      exportOptions: {},
      serializeLegend: () => "",
      serializeSvg: () => "",
      createZip: () => null,
      saveZip: async () => true,
      getZipFilename: () => "figures.zip",
    }),
    false
  );
});

/**
 * Verify canvas text measurement uses context metrics and fallback estimates.
 */
test("export helpers measure canvas text with fallback", () => {
  const documentLike = createDocumentStub();
  assert.equal(measureCanvasText({ documentLike, text: "abcd", font: "12px Inter" }), 32);
  assert.equal(
    measureCanvasText({
      documentLike: { createElement: () => ({ getContext: () => null }) },
      text: "abcd",
      font: "12px Inter",
    }),
    30
  );
});
