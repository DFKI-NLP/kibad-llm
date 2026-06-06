/**
 * Generic bar/error plot entry and tab-map helpers.
 *
 * This module keeps numeric metric preparation, pre-aggregation sample data,
 * mean/std calculation, tab grouping, and SVG rendering separate so downloads
 * can export the same raw values that rendering aggregates.
 */

import { meanAndStd } from "../utils/values.js";
import {
  getGroupLabelForFields,
  getMetricPreparedDataContainer,
  getPlotDisplayLabel,
  scheduleAdaptiveSvgFit,
} from "./shared.js";
import {
  buildGroupedLegendModel,
  createPlotLegendElement,
  getBarColor,
  getLegendItemsForPoints,
} from "./legend.js";

/**
 * Applies shared visual styling to an SVG error-bar line segment.
 *
 * Bar and grouped-bar renderers draw several SVG line elements for error bars;
 * this helper keeps those segments visually consistent within numeric plots.
 *
 * @param {SVGLineElement} line - Line element to style.
 * @returns {void}
 */
function styleErrorBarSegment(line) {
  line.setAttribute("stroke", "currentColor");
  line.setAttribute("stroke-opacity", "0.78");
}

/**
 * Resolves the display title for a metric plot entry.
 *
 * Most metric families display the full metric label, optionally shortened.
 * F1 micro multi-field plots need a special suffix-tab title so the figure
 * title stays stable while tabs expose the leaf metric names.
 *
 * @param {object} plotEntry - Numeric plot entry.
 * @param {string} metricType - Metric type for special title handling.
 * @param {object} [options] - Label and tab display options.
 * @returns {string} Display title label.
 */
export function getPlotTitleLabel(plotEntry, metricType, { shortenLabels = false, plotTabsBy = "prefix" } = {}) {
  if (
    metricType === "F1MicroMultipleFieldsMetric" &&
    shortenLabels &&
    plotTabsBy === "suffix"
  ) {
    return plotEntry.metricPrefix === "(root)" ? plotEntry.metricLabel : plotEntry.metricPrefix;
  }
  return getPlotDisplayLabel(plotEntry.metricLabel, { shortenLabels });
}

/**
 * Encodes metric path parts into the stable key used by prepared numeric data.
 *
 * Prepared numeric values are stored in a flat map so later plot-entry
 * construction can look up each metric path without rewalking nested metric
 * objects for every plot group.
 *
 * @param {Array<string>} parts - Metric path parts.
 * @returns {string} Encoded metric path key.
 */
function getNumericMetricPathKey(parts) {
  return (parts || []).join("|#|");
}

/**
 * Defaults that are semantically valid when a numeric metric path is absent.
 *
 * ErrorCollector output is sparse: counters with zero occurrences are omitted.
 * Other numeric metric types must provide every discovered path explicitly.
 */
const NUMERIC_METRIC_MISSING_DEFAULTS = new Map([
  ["ErrorCollector", 0],
]);

/**
 * Resolves one numeric plotting sample under the metric type's missing-value contract.
 *
 * @param {object} evaluation - Source evaluation record.
 * @param {object} metricPath - Prepared metric path descriptor.
 * @param {string} metricType - Numeric metric implementation type.
 * @returns {number} Finite numeric sample value.
 * @throws {Error} If a required path is absent.
 */
function getNumericMetricSampleValue(evaluation, metricPath, metricType) {
  const values = prepareNumericMetricEvaluationData(evaluation).values;
  if (values.has(metricPath.key)) {
    return values.get(metricPath.key);
  }

  if (NUMERIC_METRIC_MISSING_DEFAULTS.has(metricType)) {
    return NUMERIC_METRIC_MISSING_DEFAULTS.get(metricType);
  }

  throw new Error(
    `Numeric metric ${JSON.stringify(metricPath.label)} is missing from evaluation ` +
    `${JSON.stringify(evaluation?.runDir || "(unknown)")} and metric type ` +
    `${JSON.stringify(metricType)} has no missing-value default.`
  );
}

/**
 * Recursively collects numeric metric paths and values for one evaluation.
 *
 * This is the per-evaluation preparation step behind numeric plots: it records
 * both path metadata for cross-run metric discovery and flat values for fast
 * aggregation once the active plot groups are known.
 *
 * @param {*} value - Metric data value to inspect.
 * @param {Array<string>} [parts] - Current path parts during recursion.
 * @param {Map<string, object>} [metricPaths] - Path accumulator keyed by encoded path.
 * @param {Map<string, number>} [values] - Numeric value accumulator keyed by encoded path.
 * @returns {{metricPaths: Map<string, object>, values: Map<string, number>}} Prepared numeric data.
 * @throws {Error} If a numeric leaf is not finite.
 */
function collectNumericMetricLeafData(value, parts = [], metricPaths = new Map(), values = new Map()) {
  if (!value || typeof value !== "object") {
    return { metricPaths, values };
  }
  for (const [key, child] of Object.entries(value)) {
    const pathParts = [...parts, key];
    if (typeof child === "number") {
      if (!Number.isFinite(child)) {
        throw new Error(
          `Numeric metric ${JSON.stringify(pathParts.join("."))} must be finite.`
        );
      }
      const pathKey = getNumericMetricPathKey(pathParts);
      metricPaths.set(pathKey, {
        key: pathKey,
        root: pathParts[0],
        parts: pathParts,
        label: pathParts.join("."),
      });
      values.set(pathKey, child);
      continue;
    }
    if (child && typeof child === "object" && !Array.isArray(child)) {
      collectNumericMetricLeafData(child, pathParts, metricPaths, values);
    }
  }
  return { metricPaths, values };
}

/**
 * Lazily prepares one evaluation's numeric metric data for bar/error plots.
 *
 * The prepared shape stores metric path metadata and flat per-path numeric
 * values. The cache avoids repeated nested metric walks when tab maps,
 * download payloads, and render entries are rebuilt for the same evaluation.
 *
 * @param {object} evaluation - Raw evaluation record with metric data.
 * @returns {{metricPaths: Map<string, object>, values: Map<string, number>}} Prepared per-evaluation numeric data.
 */
export function prepareNumericMetricEvaluationData(evaluation) {
  const cache = getMetricPreparedDataContainer(evaluation);
  if (cache?.numericMetrics) {
    return cache.numericMetrics;
  }

  const prepared = collectNumericMetricLeafData(evaluation?.data);
  if (cache) {
    cache.numericMetrics = prepared;
  }
  return prepared;
}

/**
 * Collects the union of numeric metric paths from prepared evaluation data.
 *
 * Numeric plot tabs need the complete metric set across all selected
 * evaluations, including metrics that only appear in some runs. Returning a
 * sorted union keeps tab and figure order deterministic.
 *
 * @param {Array<object>} evaluations - Evaluation records.
 * @returns {Array<object>} Sorted metric path records.
 */
function collectPreparedNumericMetricPaths(evaluations) {
  const metricPaths = new Map();
  for (const evaluation of evaluations || []) {
    for (const [key, metricPath] of prepareNumericMetricEvaluationData(evaluation).metricPaths) {
      metricPaths.set(key, metricPath);
    }
  }
  return Array.from(metricPaths.values()).sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Splits a metric label into metric prefix and suffix at the final dot.
 *
 * Bar plots use these display-oriented pieces for prefix/suffix tab grouping
 * and titles. Structural classification stays separate in `metricRoot`.
 *
 * @param {string} label - Metric label.
 * @returns {{metricPrefix: string, metricSuffix: string}} Split label components.
 */
function splitMetricLabelAtLastDot(label) {
  const lastDotIndex = label.lastIndexOf(".");
  if (lastDotIndex === -1) {
    return { metricPrefix: "(root)", metricSuffix: label };
  }
  return {
    metricPrefix: label.slice(0, lastDotIndex),
    metricSuffix: label.slice(lastDotIndex + 1),
  };
}

/**
 * Converts prepared metric paths and evaluation groups into sample-only entries.
 *
 * Metric paths and plot groups must represent the same selected evaluation
 * population. Keeping this helper private prevents callers from supplying
 * paths discovered from a different population.
 *
 * @param {object} options - Prepared paths and plot grouping inputs.
 * @returns {Array<object>} Plot entries whose points contain raw samples only.
 */
function buildNumericPlotEntriesForMetricPaths({
  metricType,
  metricPaths,
  plotGroups,
  groupBarFields,
  categoryFields,
  getGroupLabel,
  displayGroupFieldName,
}) {
  const entries = [];
  for (const metricPath of metricPaths) {
    const points = [];
    plotGroups.forEach((group, index) => {
      const samples = (group.evaluations || []).map((evaluation) =>
        getNumericMetricSampleValue(evaluation, metricPath, metricType)
      );
      if (!samples.length) {
        return;
      }
      const categoryLabel = groupBarFields.length
        ? getGroupLabel(group, categoryFields, "all")
        : getGroupLabel(group, categoryFields, `group ${index + 1}`);
      const displayCategoryLabel = groupBarFields.length
        ? getGroupLabel(group, categoryFields, "all", displayGroupFieldName)
        : getGroupLabel(group, categoryFields, `group ${index + 1}`, displayGroupFieldName);
      const seriesLabel = groupBarFields.length
        ? getGroupLabel(group, groupBarFields, "series")
        : "__single__";
      const displaySeriesLabel = groupBarFields.length
        ? getGroupLabel(group, groupBarFields, "series", displayGroupFieldName)
        : "__single__";
      points.push({
        label: categoryLabel,
        displayLabel: displayCategoryLabel,
        category: categoryLabel,
        displayCategory: displayCategoryLabel,
        series: seriesLabel,
        displaySeries: displaySeriesLabel,
        samples,
      });
    });
    if (!points.length) {
      continue;
    }
    const split = splitMetricLabelAtLastDot(metricPath.label);
    entries.push({
      metricLabel: metricPath.label,
      metricRoot: metricPath.root,
      points,
      ...split,
    });
  }
  return entries;
}

/**
 * Builds sample-only numeric plot input from the selected plot groups.
 *
 * Rendering and data download both need the same grouped sample data. Keeping
 * this step separate from mean/std calculation makes numeric plots follow the
 * same pre-aggregation data flow as confusion and TP/FP/FN matrices.
 *
 * Metric-path discovery is part of this boundary and uses exactly the
 * evaluations contained in `plotGroups`. This guarantees that discovered
 * metrics and aligned samples always describe the same selected population.
 *
 * @param {object} options - Plot entry input construction inputs.
 * @returns {Array<object>} Plot entries whose points contain raw samples only.
 */
export function buildNumericPlotEntriesInput({
  metricType,
  plotGroups,
  groupBarFields,
  categoryFields,
  getGroupLabel = getGroupLabelForFields,
  displayGroupFieldName = (field) => field,
}) {
  if (!metricType) {
    throw new Error("Numeric plot entry construction requires a metric type.");
  }
  const selectedEvaluations = (plotGroups || [])
    .flatMap((group) => group.evaluations || []);
  const metricPaths = collectPreparedNumericMetricPaths(selectedEvaluations);

  return buildNumericPlotEntriesForMetricPaths({
    metricType,
    metricPaths,
    plotGroups: plotGroups || [],
    groupBarFields: groupBarFields || [],
    categoryFields: categoryFields || [],
    getGroupLabel,
    displayGroupFieldName,
  });
}

/**
 * Builds the public download metadata for a numeric plot.
 *
 * Keep this allowlist explicit so renderer-only plot-entry fields cannot leak
 * into the downloaded JSON when the internal entry shape changes.
 *
 * @param {object} plotEntry - Numeric plot input entry.
 * @returns {{metricLabel: string}} Public numeric plot metadata.
 */
export function buildNumericDownloadMetadata(plotEntry = {}) {
  return {
    metricLabel: plotEntry.metricLabel,
  };
}

/**
 * Builds the JSON-safe numeric plotting data used by downloads.
 *
 * Numeric input entries are already sample-only before rendering adds mean/std.
 * Downloads expose those raw sample values directly, keeping metric identity in
 * `plotEntry` and leaving UI grouping helpers out of the public JSON schema.
 *
 * @param {object} plotEntry - Numeric plot input entry.
 * @returns {object} JSON-safe numeric plotting data.
 */
export function buildJsonSafeNumericPlottingData(plotEntry) {
  return {
    points: (plotEntry?.points || []).map((point) => ({
      category: point.category,
      displayCategory: point.displayCategory,
      series: point.series,
      displaySeries: point.displaySeries,
      samples: point.samples || [],
    })),
  };
}

/**
 * Adds mean/std render values to sample-only numeric plot input.
 *
 * This keeps derived statistics out of the download source data while
 * preserving the existing render-entry shape expected by bar/error SVG code.
 * Rendering consumes the derived entries; downloads continue to consume the
 * sample-only input entries.
 *
 * @param {Array<object>} plotEntriesInput - Output of buildNumericPlotEntriesInput.
 * @returns {Array<object>} Plot entries with mean/std point data for rendering.
 */
export function getNumericPlotEntriesFromInput(plotEntriesInput) {
  return (plotEntriesInput || [])
    .map((entry) => ({
      ...entry,
      points: (entry.points || [])
        .map((point) => {
          const stats = meanAndStd(point.samples || []);
          if (!stats) {
            return null;
          }
          return {
            ...point,
            mean: stats.mean,
            std: stats.std,
          };
        })
        .filter(Boolean),
    }))
    .filter((entry) => entry.points.length > 0);
}

/**
 * Builds render-ready numeric entries from selected plot groups.
 *
 * This convenience wrapper applies render-only mean/std aggregation directly.
 * Callers that also need download data should retain the sample-only output of
 * `buildNumericPlotEntriesInput()` and aggregate it separately.
 *
 * @param {object} options - Plot entry construction inputs.
 * @returns {Array<object>} Plot entries with mean/std point data.
 */
export function buildPlotEntries(options) {
  return getNumericPlotEntriesFromInput(buildNumericPlotEntriesInput(options));
}

/**
 * Groups metric plot entries into bar plot tabs.
 *
 * Numeric metrics can be browsed by metric prefix or suffix depending on the
 * dashboard control state. Keeping this as a separate tab-map step lets the
 * same plot entries feed both rendering and active-tab download selection.
 *
 * @param {Array<object>} plotEntries - Entries produced by buildPlotEntries.
 * @param {object} [options] - Tab grouping options.
 * @returns {Map<string, Array<object>>} Tab map keyed by metric prefix or suffix.
 */
export function buildBarsTabMap(plotEntries, { plotTabsBy = "prefix" } = {}) {
  const tabMap = new Map();
  for (const entry of plotEntries) {
    const tabKey = plotTabsBy === "suffix" ? entry.metricSuffix : entry.metricPrefix;
    if (!tabMap.has(tabKey)) {
      tabMap.set(tabKey, []);
    }
    tabMap.get(tabKey).push(entry);
  }
  return tabMap;
}

/**
 * Splits error metric entries into total and details tabs.
 *
 * ErrorCollector plots use fixed semantic tabs instead of prefix/suffix metric
 * tabs. `metricRoot` identifies top-level total counters such as `with_error`
 * and keeps that classification independent from display labels.
 *
 * @param {Array<object>} plotEntries - Error metric plot entries.
 * @returns {Map<string, Array<object>>} Tab map for available error sections.
 */
export function buildErrorsTabMap(plotEntries) {
  const totalKeys = new Set(["with_error", "no_error"]);
  const total = plotEntries.filter((entry) => totalKeys.has(entry.metricRoot));
  const details = plotEntries.filter((entry) => !totalKeys.has(entry.metricRoot));
  const tabMap = new Map();
  if (total.length) {
    tabMap.set("total", total);
  }
  if (details.length) {
    tabMap.set("details", details);
  }
  return tabMap;
}

/**
 * Creates an SVG bar plot with mean bars and standard-deviation error bars.
 *
 * The renderer is dependency-injected so tests and the dashboard can share the
 * same DOM-free plotting code, while the SVG only receives already-aggregated
 * render points.
 *
 * @param {object} options - Rendering dependencies, points, and tooltip handlers.
 * @returns {SVGSVGElement} Rendered bar plot SVG.
 */
export function createBarPlotSvg({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  points,
  showTooltip,
  moveTooltip,
  hideTooltip,
}) {
  const width = Math.max(720, points.length * 150);
  const height = 320;
  const margin = { top: 18, right: 20, bottom: 95, left: 60 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const yMax = Math.max(
    0.05,
    ...points.map((point) => point.mean + point.std)
  );
  const step = chartWidth / Math.max(points.length, 1);
  const barWidth = Math.max(20, Math.min(60, step * 0.55));

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = documentLike.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const yTicks = 5;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = (yMax * tick) / yTicks;
    const y = margin.top + chartHeight - (value / yMax) * chartHeight;
    const grid = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    grid.setAttribute("x1", String(margin.left));
    grid.setAttribute("x2", String(width - margin.right));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("stroke", "#64748b66");
    grid.setAttribute("stroke-width", "1");
    contentGroup.appendChild(grid);

    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = value.toFixed(2);
    contentGroup.appendChild(label);
  }

  for (const [index, point] of points.entries()) {
    const centerX = margin.left + step * index + step / 2;
    const barHeight = (point.mean / yMax) * chartHeight;
    const barY = margin.top + chartHeight - barHeight;
    const barX = centerX - barWidth / 2;

    const rect = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
    rect.setAttribute("x", String(barX));
    rect.setAttribute("y", String(barY));
    rect.setAttribute("width", String(barWidth));
    rect.setAttribute("height", String(Math.max(0, barHeight)));
    rect.setAttribute("fill", "#60a5fa");
    rect.style.cursor = "crosshair";
    rect.addEventListener("mouseover", (event) => {
      showTooltip(event, [
        point.label,
        `mean: ${Number(point.mean).toFixed(4)}`,
        `std:  ${Number(point.std).toFixed(4)}`,
      ]);
    });
    rect.addEventListener("mousemove", moveTooltip);
    rect.addEventListener("mouseout", hideTooltip);
    contentGroup.appendChild(rect);

    const errTop = margin.top + chartHeight - ((point.mean + point.std) / yMax) * chartHeight;
    const errBottom = margin.top + chartHeight - ((point.mean - point.std) / yMax) * chartHeight;
    const errorLine = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    errorLine.setAttribute("x1", String(centerX));
    errorLine.setAttribute("x2", String(centerX));
    errorLine.setAttribute("y1", String(errTop));
    errorLine.setAttribute("y2", String(errBottom));
    styleErrorBarSegment(errorLine);
    errorLine.setAttribute("stroke-width", "2");
    contentGroup.appendChild(errorLine);

    const capTop = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    capTop.setAttribute("x1", String(centerX - 6));
    capTop.setAttribute("x2", String(centerX + 6));
    capTop.setAttribute("y1", String(errTop));
    capTop.setAttribute("y2", String(errTop));
    styleErrorBarSegment(capTop);
    capTop.setAttribute("stroke-width", "2");
    contentGroup.appendChild(capTop);

    const capBottom = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    capBottom.setAttribute("x1", String(centerX - 6));
    capBottom.setAttribute("x2", String(centerX + 6));
    capBottom.setAttribute("y1", String(errBottom));
    capBottom.setAttribute("y2", String(errBottom));
    styleErrorBarSegment(capBottom);
    capBottom.setAttribute("stroke-width", "2");
    contentGroup.appendChild(capBottom);

    const xLabel = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    xLabel.setAttribute("x", String(centerX));
    xLabel.setAttribute("y", String(height - margin.bottom + 16));
    xLabel.setAttribute("transform", `rotate(-28 ${centerX} ${height - margin.bottom + 16})`);
    xLabel.setAttribute("text-anchor", "end");
    xLabel.setAttribute("fill", "currentColor");
    xLabel.setAttribute("font-size", "11");
    xLabel.textContent = point.displayLabel;
    contentGroup.appendChild(xLabel);
  }

  scheduleAdaptiveSvgFit({ documentLike, requestAnimationFrameLike, svg, contentGroup, minWidth: width, minHeight: height });
  return svg;
}

/**
 * Creates an SVG grouped bar plot with one bar per category/series pair.
 *
 * Grouped plots use the same render-point contract as plain bars, but arrange
 * points by category and series so model/seed or other varying fields can be
 * compared within each category.
 *
 * @param {object} options - Rendering dependencies, points, legend model, and tooltip handlers.
 * @returns {SVGSVGElement} Rendered grouped bar plot SVG.
 */
export function createGroupedBarPlotSvg({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  points,
  legendModel = null,
  showTooltip,
  moveTooltip,
  hideTooltip,
}) {
  const categoryOrder = [];
  const categorySet = new Set();
  const categoryDisplayMap = new Map();
  const valueMap = new Map();

  for (const point of points) {
    if (!categorySet.has(point.category)) {
      categorySet.add(point.category);
      categoryOrder.push(point.category);
    }
    if (!categoryDisplayMap.has(point.category)) {
      categoryDisplayMap.set(point.category, point.displayCategory);
    }
    valueMap.set(`${point.category}|#|${point.series}`, point);
  }

  const localSeriesOrder = [];
  const localSeriesSet = new Set();
  for (const point of points) {
    if (!localSeriesSet.has(point.series)) {
      localSeriesSet.add(point.series);
      localSeriesOrder.push(point.series);
    }
  }

  const seriesOrder = legendModel?.seriesOrder?.length ? legendModel.seriesOrder : localSeriesOrder;

  const seriesCount = Math.max(1, seriesOrder.length);
  const width = Math.max(760, categoryOrder.length * (120 + seriesCount * 26));
  const height = 340;
  const margin = { top: 18, right: 20, bottom: 95, left: 60 };
  const chartWidth = width - margin.left - margin.right;
  const chartHeight = height - margin.top - margin.bottom;
  const yMax = Math.max(
    0.05,
    ...points.map((point) => point.mean + point.std)
  );
  const categoryStep = chartWidth / Math.max(categoryOrder.length, 1);
  const categoryWidth = categoryStep * 0.82;
  const barGap = 4;
  const barWidth = Math.max(
    10,
    Math.min(26, (categoryWidth - barGap * Math.max(0, seriesCount - 1)) / seriesCount)
  );
  const groupPixelWidth = barWidth * seriesCount + barGap * Math.max(0, seriesCount - 1);

  const svg = documentLike.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.setAttribute("viewBox", `0 0 ${width} ${height}`);
  const contentGroup = documentLike.createElementNS("http://www.w3.org/2000/svg", "g");
  svg.appendChild(contentGroup);

  const yTicks = 5;
  for (let tick = 0; tick <= yTicks; tick += 1) {
    const value = (yMax * tick) / yTicks;
    const y = margin.top + chartHeight - (value / yMax) * chartHeight;
    const grid = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
    grid.setAttribute("x1", String(margin.left));
    grid.setAttribute("x2", String(width - margin.right));
    grid.setAttribute("y1", String(y));
    grid.setAttribute("y2", String(y));
    grid.setAttribute("stroke", "#64748b66");
    grid.setAttribute("stroke-width", "1");
    contentGroup.appendChild(grid);

    const label = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", String(margin.left - 8));
    label.setAttribute("y", String(y + 4));
    label.setAttribute("text-anchor", "end");
    label.setAttribute("fill", "currentColor");
    label.setAttribute("font-size", "11");
    label.textContent = value.toFixed(2);
    contentGroup.appendChild(label);
  }

  for (const [categoryIndex, category] of categoryOrder.entries()) {
    const centerX = margin.left + categoryStep * categoryIndex + categoryStep / 2;
    const groupStartX = centerX - groupPixelWidth / 2;

    for (const [seriesIndex, series] of seriesOrder.entries()) {
      const point = valueMap.get(`${category}|#|${series}`);
      if (!point) {
        continue;
      }
      const barHeight = (point.mean / yMax) * chartHeight;
      const barY = margin.top + chartHeight - barHeight;
      const barX = groupStartX + seriesIndex * (barWidth + barGap);
      const color = legendModel?.colorBySeries?.get(series) || getBarColor(seriesIndex);

      const rect = documentLike.createElementNS("http://www.w3.org/2000/svg", "rect");
      rect.setAttribute("x", String(barX));
      rect.setAttribute("y", String(barY));
      rect.setAttribute("width", String(barWidth));
      rect.setAttribute("height", String(Math.max(0, barHeight)));
      rect.setAttribute("fill", color);
      rect.style.cursor = "crosshair";
      rect.addEventListener("mouseover", (event) => {
        const tooltipLines = [category];
        if (seriesOrder.length > 1) {
          tooltipLines.push(`series: ${point.displaySeries || legendModel?.displayBySeries?.get(series) || series}`);
        }
        tooltipLines.push(
          `mean: ${Number(point.mean).toFixed(4)}`,
          `std:  ${Number(point.std).toFixed(4)}`
        );
        showTooltip(event, tooltipLines);
      });
      rect.addEventListener("mousemove", moveTooltip);
      rect.addEventListener("mouseout", hideTooltip);
      contentGroup.appendChild(rect);

      const errTop = margin.top + chartHeight - ((point.mean + point.std) / yMax) * chartHeight;
      const errBottom = margin.top + chartHeight - ((point.mean - point.std) / yMax) * chartHeight;
      const centerBarX = barX + barWidth / 2;

      const errorLine = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
      errorLine.setAttribute("x1", String(centerBarX));
      errorLine.setAttribute("x2", String(centerBarX));
      errorLine.setAttribute("y1", String(errTop));
      errorLine.setAttribute("y2", String(errBottom));
      styleErrorBarSegment(errorLine);
      errorLine.setAttribute("stroke-width", "2");
      contentGroup.appendChild(errorLine);

      const capTop = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
      capTop.setAttribute("x1", String(centerBarX - 5));
      capTop.setAttribute("x2", String(centerBarX + 5));
      capTop.setAttribute("y1", String(errTop));
      capTop.setAttribute("y2", String(errTop));
      styleErrorBarSegment(capTop);
      capTop.setAttribute("stroke-width", "2");
      contentGroup.appendChild(capTop);

      const capBottom = documentLike.createElementNS("http://www.w3.org/2000/svg", "line");
      capBottom.setAttribute("x1", String(centerBarX - 5));
      capBottom.setAttribute("x2", String(centerBarX + 5));
      capBottom.setAttribute("y1", String(errBottom));
      capBottom.setAttribute("y2", String(errBottom));
      styleErrorBarSegment(capBottom);
      capBottom.setAttribute("stroke-width", "2");
      contentGroup.appendChild(capBottom);
    }

    const xLabel = documentLike.createElementNS("http://www.w3.org/2000/svg", "text");
    xLabel.setAttribute("x", String(centerX));
    xLabel.setAttribute("y", String(height - margin.bottom + 16));
    xLabel.setAttribute("transform", `rotate(-28 ${centerX} ${height - margin.bottom + 16})`);
    xLabel.setAttribute("text-anchor", "end");
    xLabel.setAttribute("fill", "currentColor");
    xLabel.setAttribute("font-size", "11");
    xLabel.textContent = categoryDisplayMap.get(category) || category;
    contentGroup.appendChild(xLabel);
  }

  scheduleAdaptiveSvgFit({ documentLike, requestAnimationFrameLike, svg, contentGroup, minWidth: width, minHeight: height });
  return svg;
}

/**
 * Renders plot tab buttons, optional legends, and the active plot grid.
 *
 * This is the shared DOM adapter for numeric bar-like plots. It keeps tab
 * resolution, shared legend behavior, and card rendering in one place so the
 * dashboard can reuse the same flow for ordinary metrics and ErrorCollector
 * metrics.
 *
 * @param {object} options - Current tab state, plot data, DOM nodes, and renderer callbacks.
 * @returns {{activeEvalPlotTab: string, activePlotLegendItems: Array<object>}} Updated active tab and shared legend items.
 */
export function renderBarPlotTabsAndGrid({
  documentLike = globalThis.document,
  tabMap,
  activeExperiment,
  groupBarFields,
  metricType,
  activeEvalPlotTab,
  plotShowLegendOnce,
  plotShowLegendOnceRow,
  evalPlotTabs,
  evalPlotContent,
  buildCountTabButtonModels,
  renderTabButtons,
  resolveActiveTabValue,
  getPlotTitleLabel,
  displayPlotGroupFieldName,
  createBarSvg = (points) => createBarPlotSvg({ documentLike, points }),
  createGroupedBarSvg = (points, legendModel) => createGroupedBarPlotSvg({ documentLike, points, legendModel }),
  createLegendElement = createPlotLegendElement,
  onActiveTabChange,
}) {
  const tabPriority = ["total", "details"];
  const sortedTabKeys = Array.from(tabMap.keys()).sort((a, b) => {
    const pa = tabPriority.indexOf(a);
    const pb = tabPriority.indexOf(b);
    if (pa !== -1 && pb !== -1) return pa - pb;
    if (pa !== -1) return -1;
    if (pb !== -1) return 1;
    return a.localeCompare(b);
  });
  const nextActiveTab = resolveActiveTabValue(activeEvalPlotTab, sortedTabKeys);
  renderTabButtons({
    documentLike,
    containerElement: evalPlotTabs,
    tabModels: buildCountTabButtonModels(sortedTabKeys, {
      activeValue: nextActiveTab,
      getLabelText: (key) => key,
      getCount: (key) => tabMap.get(key).length,
      getTitle: (key) => key,
    }),
    onSelect: (key) => onActiveTabChange(key),
  });

  const activeEntries = tabMap.get(nextActiveTab) || [];
  const groupedLegendModel = groupBarFields.length
    ? buildGroupedLegendModel(activeEntries)
    : null;
  evalPlotContent.innerHTML = "";

  if (plotShowLegendOnceRow) {
    plotShowLegendOnceRow.style.display = groupedLegendModel?.items.length > 1 ? "" : "none";
  }
  const hasSharedLegend = Boolean(groupedLegendModel && groupedLegendModel.items.length > 1);
  if (hasSharedLegend && plotShowLegendOnce) {
    evalPlotContent.appendChild(createLegendElement({
      documentLike,
      legendItems: groupedLegendModel.items,
    }));
  }

  const grid = documentLike.createElement("div");
  grid.className = "plot-grid";
  for (const entry of activeEntries) {
    const card = documentLike.createElement("section");
    card.className = "plot-card";
    const title = documentLike.createElement("p");
    title.className = "plot-title";
    const groupedByText = groupBarFields.length
      ? ` | grouped by: ${groupBarFields.map((field) => displayPlotGroupFieldName(field)).join(", ")}`
      : "";
    title.textContent = `${getPlotTitleLabel(entry, metricType)} (mean ± std)${groupedByText}`;
    card.appendChild(title);
    if (groupBarFields.length) {
      const plotLegendItems = getLegendItemsForPoints(entry.points, groupedLegendModel);
      if (plotLegendItems.length > 1 && !plotShowLegendOnce) {
        card.appendChild(createLegendElement({
          documentLike,
          legendItems: plotLegendItems,
        }));
      }
      card.appendChild(createGroupedBarSvg(entry.points, groupedLegendModel));
    } else {
      card.appendChild(createBarSvg(entry.points));
    }
    grid.appendChild(card);
  }

  if (!grid.childElementCount) {
    const msg = documentLike.createElement("p");
    msg.className = "plot-empty";
    msg.textContent = "No plottable metric values found for the active tab.";
    evalPlotContent.appendChild(msg);
  } else {
    evalPlotContent.appendChild(grid);
  }

  return {
    activeEvalPlotTab: nextActiveTab,
    activePlotLegendItems: hasSharedLegend ? groupedLegendModel.items : [],
  };
}
