/**
 * Figure export, SVG serialization, and ZIP helpers for the eval dashboard.
 */

import {
  getFigureTitlePrefix,
  sanitizeFigureFilename,
} from "../utils/text.js";

export function getUniqueFigureFilename(title, usedNames) {
  const baseName = sanitizeFigureFilename(getFigureTitlePrefix(title));
  let candidate = baseName;
  let suffix = 2;
  while (usedNames.has(candidate.toLowerCase())) {
    candidate = `${baseName} (${suffix})`;
    suffix += 1;
  }
  usedNames.add(candidate.toLowerCase());
  return `${candidate}.svg`;
}

export function buildPlotTabZipFilename({ activeEvalTab, activePlotTabLabel }) {
  const evalTabLabel = typeof activeEvalTab === "string" ? activeEvalTab.trim() : "";
  const filenameParts = [evalTabLabel, getFigureTitlePrefix(String(activePlotTabLabel || "figures").trim())]
    .filter((part) => part.length > 0)
    .map((part) => sanitizeFigureFilename(part));
  return `${filenameParts.join("-") || "figures"}.zip`;
}

export function getSvgExportViewBox(svg, width, height) {
  const viewBox = svg.getAttribute("viewBox");
  if (!viewBox) {
    return { minX: 0, minY: 0, width: Number(width), height: Number(height) };
  }
  const parts = viewBox
    .trim()
    .split(/\s+/)
    .map((part) => Number(part));
  if (parts.length !== 4 || parts.some((part) => !Number.isFinite(part))) {
    return { minX: 0, minY: 0, width: Number(width), height: Number(height) };
  }
  return { minX: parts[0], minY: parts[1], width: parts[2], height: parts[3] };
}

export function resolveOpaqueExportBackgroundColor(elements, getStyle = globalThis.getComputedStyle) {
  for (const element of elements || []) {
    if (!element) {
      continue;
    }
    const backgroundColor = getStyle(element).backgroundColor;
    if (
      backgroundColor &&
      backgroundColor !== "transparent" &&
      backgroundColor !== "rgba(0, 0, 0, 0)"
    ) {
      return backgroundColor;
    }
  }
  return "#ffffff";
}

export function positionTooltip({ tooltipElement, windowLike = globalThis.window, event, pad = 14 }) {
  let x = event.clientX + pad;
  let y = event.clientY - pad - tooltipElement.offsetHeight;
  if (x + tooltipElement.offsetWidth > windowLike.innerWidth - pad) {
    x = event.clientX - tooltipElement.offsetWidth - pad;
  }
  if (y < pad) {
    y = event.clientY + pad;
  }
  tooltipElement.style.left = `${x}px`;
  tooltipElement.style.top = `${y}px`;
}

export function showTooltip({
  tooltipElement,
  windowLike = globalThis.window,
  event,
  lines,
}) {
  tooltipElement.textContent = lines.join("\n");
  tooltipElement.style.display = "block";
  positionTooltip({ tooltipElement, windowLike, event });
}

export function hideTooltip({ tooltipElement }) {
  tooltipElement.style.display = "none";
}

export async function writeTextToClipboard({
  documentLike = globalThis.document,
  navigatorLike = globalThis.navigator,
  text,
}) {
  if (navigatorLike.clipboard?.writeText) {
    await navigatorLike.clipboard.writeText(text);
    return;
  }

  const textarea = documentLike.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "readonly");
  textarea.style.position = "fixed";
  textarea.style.top = "-9999px";
  textarea.style.left = "-9999px";
  documentLike.body.appendChild(textarea);
  textarea.focus();
  textarea.select();
  const copied = documentLike.execCommand("copy");
  documentLike.body.removeChild(textarea);
  if (!copied) {
    throw new Error("Clipboard copy command was not successful.");
  }
}

export function getActivePlotTabZipFilename({
  activeEvalTab,
  evalPlotTabs,
}) {
  const activeButton = evalPlotTabs.querySelector(".tab-button.active");
  const plotTabLabel = activeButton?.getAttribute("title") || activeButton?.textContent || "figures";
  return buildPlotTabZipFilename({
    activeEvalTab,
    activePlotTabLabel: plotTabLabel,
  });
}

export function measureCanvasText({ documentLike = globalThis.document, text, font }) {
  const canvas = documentLike.createElement("canvas");
  const context = canvas.getContext("2d");
  if (!context) {
    return text.length * 7.5;
  }
  context.font = font;
  return context.measureText(text).width;
}

export function triggerBlobDownload({
  documentLike = globalThis.document,
  urlLike = globalThis.URL,
  setTimeoutLike = globalThis.setTimeout,
  filename,
  blob,
}) {
  const url = urlLike.createObjectURL(blob);
  const link = documentLike.createElement("a");
  link.href = url;
  link.download = filename;
  link.rel = "noopener";
  documentLike.body.appendChild(link);
  link.click();
  link.remove();
  setTimeoutLike(() => urlLike.revokeObjectURL(url), 1000);
}

export async function saveBlob({
  windowLike = globalThis.window,
  blob,
  suggestedName,
  types,
  triggerDownload,
  consoleLike = globalThis.console,
}) {
  if (typeof windowLike.showSaveFilePicker === "function") {
    try {
      const handle = await windowLike.showSaveFilePicker({ suggestedName, types });
      const writable = await handle.createWritable();
      await writable.write(blob);
      await writable.close();
      return true;
    } catch (error) {
      if (error && error.name === "AbortError") {
        return false;
      }
      consoleLike?.warn?.("Save picker failed, falling back to browser download.", error);
    }
  }

  triggerDownload(blob, suggestedName);
  return true;
}

export function getVisiblePlotFigureCards(evalPlotContent) {
  return Array.from(evalPlotContent.querySelectorAll(".plot-card")).filter((card) => card.querySelector("svg"));
}

export function buildVisibleFigureFiles({
  figureCards,
  activePlotLegendItems,
  exportOptions,
  serializeLegend,
  serializeSvg,
}) {
  const includeLegend = activePlotLegendItems.length > 1;
  const usedNames = new Set(includeLegend ? ["legend"] : []);
  const files = [];
  if (includeLegend) {
    files.push({
      filename: "legend.svg",
      content: serializeLegend(activePlotLegendItems, exportOptions),
    });
  }

  figureCards.forEach((card, index) => {
    const svg = card.querySelector("svg");
    if (!svg) {
      return;
    }
    const title = card.querySelector(".plot-title")?.textContent?.trim() || `figure ${index + 1}`;
    files.push({
      filename: getUniqueFigureFilename(title, usedNames),
      content: serializeSvg(svg, exportOptions),
    });
  });

  return files;
}

export async function downloadVisibleFigures({
  figureCards,
  activePlotLegendItems,
  exportOptions,
  serializeLegend,
  serializeSvg,
  createZip,
  saveZip,
  getZipFilename,
}) {
  if (!figureCards.length) {
    return false;
  }

  const files = buildVisibleFigureFiles({
    figureCards,
    activePlotLegendItems,
    exportOptions,
    serializeLegend,
    serializeSvg,
  });
  if (!files.length) {
    return false;
  }

  const zipBlob = createZip(files.map((file) => ({ name: file.filename, content: file.content })));
  return saveZip(zipBlob, getZipFilename(), [
    { description: "ZIP archive", accept: { "application/zip": [".zip"] } },
  ]);
}

export function prependExportBackgroundRect({
  documentLike = globalThis.document,
  svg,
  width,
  height,
  color = "#ffffff",
}) {
  const box = getSvgExportViewBox(svg, width, height);
  const background = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
  background.setAttribute("x", String(box.minX));
  background.setAttribute("y", String(box.minY));
  background.setAttribute("width", String(box.width));
  background.setAttribute("height", String(box.height));
  background.setAttribute("fill", color);
  svg.insertBefore(background, svg.firstChild);
}

export function serializeLegendSvg({
  documentLike = globalThis.document,
  serializer = new XMLSerializer(),
  legendItems,
  computedStyle,
  measureText,
  exportOptions = {},
}) {
  if (!legendItems.length) {
    return "";
  }

  const fontSize = 12;
  const rowHeight = 22;
  const padding = 10;
  const swatchSize = 12;
  const textX = padding + swatchSize + 8;
  const fontFamily = computedStyle.fontFamily || "Inter, Arial, sans-serif";
  const textColor = computedStyle.color || "#cbd5e1";
  const textWidths = legendItems.map((item) =>
    measureText ? measureText(item.label, `${fontSize}px ${fontFamily}`) : item.label.length * (fontSize * 0.62)
  );
  const width = Math.ceil(Math.max(120, textX + Math.max(...textWidths, 0) + padding));
  const height = padding * 2 + legendItems.length * rowHeight;

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  svg.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

  if (exportOptions.opaqueBackground) {
    prependExportBackgroundRect({
      documentLike,
      svg,
      width,
      height,
      color: exportOptions.backgroundColor || "#ffffff",
    });
  }

  legendItems.forEach((item, index) => {
    const centerY = padding + index * rowHeight + rowHeight / 2;

    const swatch = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
    swatch.setAttribute("x", String(padding));
    swatch.setAttribute("y", String(centerY - swatchSize / 2));
    swatch.setAttribute("width", String(swatchSize));
    swatch.setAttribute("height", String(swatchSize));
    swatch.setAttribute("rx", "2");
    swatch.setAttribute("fill", item.color);
    svg.appendChild(swatch);

    const text = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    text.setAttribute("x", String(textX));
    text.setAttribute("y", String(centerY + fontSize / 3));
    text.setAttribute("fill", textColor);
    text.setAttribute("font-size", String(fontSize));
    text.setAttribute("font-family", fontFamily);
    text.textContent = item.label;
    svg.appendChild(text);
  });

  return `<?xml version="1.0" encoding="UTF-8"?>\n${serializer.serializeToString(svg)}`;
}

export function serializeSvgForDownload({
  documentLike = globalThis.document,
  serializer = new XMLSerializer(),
  sourceSvg,
  computedStyle,
  exportOptions = {},
}) {
  const clone = sourceSvg.cloneNode(true);
  const width = sourceSvg.getAttribute("width") || String(Math.ceil(sourceSvg.getBoundingClientRect().width));
  const height = sourceSvg.getAttribute("height") || String(Math.ceil(sourceSvg.getBoundingClientRect().height));

  clone.setAttribute("xmlns", "http://www.w3.org/2000/svg");
  clone.setAttribute("xmlns:xlink", "http://www.w3.org/1999/xlink");
  clone.setAttribute("width", width);
  clone.setAttribute("height", height);
  if (!clone.hasAttribute("viewBox")) {
    clone.setAttribute("viewBox", `0 0 ${width} ${height}`);
  }
  if (exportOptions.opaqueBackground) {
    prependExportBackgroundRect({
      documentLike,
      svg: clone,
      width,
      height,
      color: exportOptions.backgroundColor || "#ffffff",
    });
  }
  clone.style.color = computedStyle.color;
  clone.style.fontFamily = computedStyle.fontFamily;
  clone.style.backgroundColor = computedStyle.backgroundColor;

  return `<?xml version="1.0" encoding="UTF-8"?>\n${serializer.serializeToString(clone)}`;
}

export function getZipDosDateTime(date = new Date()) {
  const year = Math.max(1980, date.getFullYear());
  return {
    time: ((date.getHours() & 0x1f) << 11) | ((date.getMinutes() & 0x3f) << 5) | ((Math.floor(date.getSeconds() / 2)) & 0x1f),
    date: (((year - 1980) & 0x7f) << 9) | (((date.getMonth() + 1) & 0x0f) << 5) | (date.getDate() & 0x1f),
  };
}

const crc32Table = (() => {
  const table = new Uint32Array(256);
  for (let i = 0; i < 256; i += 1) {
    let value = i;
    for (let bit = 0; bit < 8; bit += 1) {
      value = (value & 1) ? (0xedb88320 ^ (value >>> 1)) : (value >>> 1);
    }
    table[i] = value >>> 0;
  }
  return table;
})();

export function computeCrc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc = crc32Table[(crc ^ byte) & 0xff] ^ (crc >>> 8);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

export function concatUint8Arrays(chunks) {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const result = new Uint8Array(totalLength);
  let offset = 0;
  for (const chunk of chunks) {
    result.set(chunk, offset);
    offset += chunk.length;
  }
  return result;
}

export function createZipBlob(files, { date = new Date(), BlobCtor = globalThis.Blob } = {}) {
  const encoder = new TextEncoder();
  const fileDate = getZipDosDateTime(date);
  const localChunks = [];
  const centralChunks = [];
  let offset = 0;

  for (const file of files) {
    const nameBytes = encoder.encode(file.name);
    const dataBytes = encoder.encode(file.content);
    const crc32 = computeCrc32(dataBytes);

    const localHeader = new Uint8Array(30 + nameBytes.length);
    const localView = new DataView(localHeader.buffer);
    localView.setUint32(0, 0x04034b50, true);
    localView.setUint16(4, 20, true);
    localView.setUint16(6, 0x0800, true);
    localView.setUint16(8, 0, true);
    localView.setUint16(10, fileDate.time, true);
    localView.setUint16(12, fileDate.date, true);
    localView.setUint32(14, crc32, true);
    localView.setUint32(18, dataBytes.length, true);
    localView.setUint32(22, dataBytes.length, true);
    localView.setUint16(26, nameBytes.length, true);
    localView.setUint16(28, 0, true);
    localHeader.set(nameBytes, 30);
    localChunks.push(localHeader, dataBytes);

    const centralHeader = new Uint8Array(46 + nameBytes.length);
    const centralView = new DataView(centralHeader.buffer);
    centralView.setUint32(0, 0x02014b50, true);
    centralView.setUint16(4, 20, true);
    centralView.setUint16(6, 20, true);
    centralView.setUint16(8, 0x0800, true);
    centralView.setUint16(10, 0, true);
    centralView.setUint16(12, fileDate.time, true);
    centralView.setUint16(14, fileDate.date, true);
    centralView.setUint32(16, crc32, true);
    centralView.setUint32(20, dataBytes.length, true);
    centralView.setUint32(24, dataBytes.length, true);
    centralView.setUint16(28, nameBytes.length, true);
    centralView.setUint16(30, 0, true);
    centralView.setUint16(32, 0, true);
    centralView.setUint16(34, 0, true);
    centralView.setUint16(36, 0, true);
    centralView.setUint32(38, 0, true);
    centralView.setUint32(42, offset, true);
    centralHeader.set(nameBytes, 46);
    centralChunks.push(centralHeader);

    offset += localHeader.length + dataBytes.length;
  }

  const centralDirectory = concatUint8Arrays(centralChunks);
  const endRecord = new Uint8Array(22);
  const endView = new DataView(endRecord.buffer);
  endView.setUint32(0, 0x06054b50, true);
  endView.setUint16(4, 0, true);
  endView.setUint16(6, 0, true);
  endView.setUint16(8, files.length, true);
  endView.setUint16(10, files.length, true);
  endView.setUint32(12, centralDirectory.length, true);
  endView.setUint32(16, offset, true);
  endView.setUint16(20, 0, true);

  const zipBytes = concatUint8Arrays([...localChunks, centralDirectory, endRecord]);
  return new BlobCtor([zipBytes], { type: "application/zip" });
}
