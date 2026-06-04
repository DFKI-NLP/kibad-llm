/**
 * Shared DOM-free plot helpers for the eval dashboard.
 */

import { splitLabelByLastDot } from "../utils/text.js";
import { meanAndStd, normalizeValue } from "../utils/values.js";

export const TP_FP_FN_KEYS = ["tp", "fp", "fn"];
export const plotSortCollator = new Intl.Collator(undefined, {
  numeric: true,
  sensitivity: "base",
});

/**
 * Resolves the stable source run directory for a metric collection evaluation.
 *
 * @param {object} evaluation - Evaluation record.
 * @returns {string} Normalized source run directory.
 */
export function getMetricCollectionSourceRunDir(evaluation) {
  return normalizeValue(evaluation?.sourceRunDir ?? evaluation?.runDir).trim();
}

/**
 * Check whether a value is a plain object record.
 *
 * @param {*} value - Candidate record.
 * @returns {boolean} Whether the value is a non-array object.
 */
export function isMetricDataRecord(value) {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

/**
 * Resolves the non-enumerable prepared-data container for a metric evaluation.
 *
 * Collection views keep the raw dashboard evaluation on `.evaluation`; caching
 * on that source record lets rebuilt views reuse the same prepared data. Direct
 * aggregation inputs fall back to the object they received.
 *
 * @param {object} evaluation - Collection view or direct evaluation.
 * @returns {object} Mutable prepared-data container.
 * @throws {Error} If the input cannot own prepared data.
 */
export function getMetricPreparedDataContainer(evaluation) {
  const cacheTarget = evaluation?.evaluation && typeof evaluation.evaluation === "object"
    ? evaluation.evaluation
    : evaluation;
  if (!cacheTarget || typeof cacheTarget !== "object") {
    throw new Error("Metric preparation cache target must be an object.");
  }
  if (!cacheTarget.dataPrepared || typeof cacheTarget.dataPrepared !== "object") {
    Object.defineProperty(cacheTarget, "dataPrepared", {
      value: Object.create(null),
      enumerable: false,
      configurable: true,
      writable: true,
    });
  } else if (Object.getPrototypeOf(cacheTarget.dataPrepared) !== null) {
    const preparedData = Object.assign(Object.create(null), cacheTarget.dataPrepared);
    Object.defineProperty(cacheTarget, "dataPrepared", {
      value: preparedData,
      enumerable: false,
      configurable: true,
      writable: true,
    });
  }
  return cacheTarget.dataPrepared;
}

/**
 * Build a collection-view wrapper for one field-based metric evaluation.
 *
 * Collection metrics expose their field map by reference. Single-field metrics
 * are wrapped as one-field collections and must define a non-empty metric.field.
 *
 * @param {object} evaluation - Evaluation record to wrap.
 * @param {object} options - Collection type names, metric label, and field resolver.
 * @returns {object} Collection-view record.
 * @throws {Error} If the evaluation shape violates the metric contract.
 */
export function getMetricCollectionView(
  evaluation,
  { collectionType, singularType, metricLabel, evalTabState, getEvaluationEffectiveValue }
) {
  if (!evaluation || typeof evaluation !== "object") {
    throw new Error(`${metricLabel} evaluation must be an object.`);
  }

  const metricType = normalizeValue(evaluation?.jobReturnValue?.type).trim();
  const sourceRunDir = getMetricCollectionSourceRunDir(evaluation);
  if (metricType === collectionType) {
    const fieldEntries = evaluation.data;
    if (!isMetricDataRecord(fieldEntries)) {
      throw new Error(`${collectionType} data must be an object mapping metric fields to metric data.`);
    }

    const fields = new Map();
    for (const [rawField, fieldEntry] of Object.entries(fieldEntries)) {
      const fieldLabel = normalizeValue(rawField).trim();
      if (!fieldLabel) {
        throw new Error(`${collectionType} data contains an empty metric field name.`);
      }
      if (fields.has(fieldLabel)) {
        throw new Error(`${collectionType} data contains duplicate metric field ${JSON.stringify(fieldLabel)} after normalization.`);
      }
      if (!isMetricDataRecord(fieldEntry)) {
        throw new Error(`${collectionType} field ${JSON.stringify(fieldLabel)} must contain object metric data.`);
      }
      fields.set(fieldLabel, fieldEntry);
    }
    if (fields.size === 0) {
      throw new Error(`${collectionType} data must contain at least one metric field.`);
    }

    return {
      evaluation,
      runDir: normalizeValue(evaluation?.runDir) || sourceRunDir,
      sourceRunDir,
      fields,
    };
  }

  if (metricType === singularType) {
    const rawField = getEvaluationEffectiveValue
      ? getEvaluationEffectiveValue(evaluation, "metric.field", evalTabState)
      : evaluation?.overrides?.["metric.field"];
    const fieldLabel = normalizeValue(rawField).trim();
    if (!fieldLabel) {
      throw new Error(`${singularType} evaluation must define a non-empty metric.field.`);
    }
    if (!isMetricDataRecord(evaluation.data)) {
      throw new Error(`${singularType} data must be an object.`);
    }
    return {
      evaluation,
      runDir: normalizeValue(evaluation?.runDir) || sourceRunDir,
      sourceRunDir,
      fields: new Map([[fieldLabel, evaluation.data]]),
    };
  }

  throw new Error(`${metricLabel} plot received unsupported metric type: ${metricType || "(missing)"}.`);
}

/**
 * Formats a plot label, optionally shortening dotted paths to their suffix.
 *
 * @param {*} label - Raw label value.
 * @param {object} [options] - Display options.
 * @returns {string} Normalized label text.
 */
export function getPlotDisplayLabel(label, { shortenLabels = false } = {}) {
  const text = normalizeValue(label);
  return shortenLabels ? splitLabelByLastDot(text) : text;
}

/**
 * Resolves the display title for a metric plot entry.
 *
 * @param {object} plotEntry - Plot entry created by buildPlotEntries.
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
    return plotEntry.prefix === "(root)" ? plotEntry.metricLabel : plotEntry.prefix;
  }
  return getPlotDisplayLabel(plotEntry.metricLabel, { shortenLabels });
}

/**
 * Selects a deterministic bar color from the dashboard palette.
 *
 * @param {number} index - Zero-based series index.
 * @returns {string} Hex color value.
 */
export function getBarColor(index) {
  const palette = [
    "#60a5fa",
    "#f97316",
    "#22c55e",
    "#a78bfa",
    "#f43f5e",
    "#14b8a6",
    "#eab308",
    "#8b5cf6",
    "#06b6d4",
    "#ef4444",
  ];
  return palette[index % palette.length];
}

/**
 * Applies shared visual styling to an SVG error-bar line segment.
 *
 * @param {SVGLineElement} line - Line element to style.
 * @returns {void}
 */
export function styleErrorBarSegment(line) {
  line.setAttribute("stroke", "currentColor");
  line.setAttribute("stroke-opacity", "0.78");
}

/**
 * Expands an SVG viewport so all generated plot content is visible.
 *
 * @param {SVGSVGElement} svg - SVG element to resize.
 * @param {SVGGElement} contentGroup - Group whose bounding box is measured.
 * @param {number} minWidth - Minimum SVG width.
 * @param {number} minHeight - Minimum SVG height.
 * @returns {boolean} True when fitting succeeded.
 */
export function fitSvgToContents(svg, contentGroup, minWidth, minHeight) {
  if (!svg.isConnected) {
    return false;
  }
  let bbox;
  try {
    bbox = contentGroup.getBBox();
  } catch (error) {
    return false;
  }
  if (
    !bbox ||
    !Number.isFinite(bbox.x) ||
    !Number.isFinite(bbox.y) ||
    !Number.isFinite(bbox.width) ||
    !Number.isFinite(bbox.height)
  ) {
    return false;
  }

  const padding = 8;
  const shiftX = Math.max(0, padding - bbox.x);
  const shiftY = Math.max(0, padding - bbox.y);
  contentGroup.setAttribute("transform", `translate(${shiftX}, ${shiftY})`);

  const fittedWidth = Math.ceil(
    Math.max(minWidth + shiftX, bbox.x + bbox.width + shiftX + padding)
  );
  const fittedHeight = Math.ceil(
    Math.max(minHeight + shiftY, bbox.y + bbox.height + shiftY + padding)
  );

  svg.setAttribute("width", String(fittedWidth));
  svg.setAttribute("height", String(fittedHeight));
  svg.setAttribute("viewBox", `0 0 ${fittedWidth} ${fittedHeight}`);
  return true;
}

/**
 * Schedules repeated SVG fitting attempts after layout and font loading.
 *
 * @param {object} options - Fitting dependencies and dimensions.
 * @returns {void}
 */
export function scheduleAdaptiveSvgFit({
  documentLike = globalThis.document,
  requestAnimationFrameLike = globalThis.requestAnimationFrame,
  svg,
  contentGroup,
  minWidth,
  minHeight,
}) {
  let attempts = 4;
  const requestFrame = requestAnimationFrameLike || ((callback) => callback());
  const runFit = () => {
    const fitted = fitSvgToContents(svg, contentGroup, minWidth, minHeight);
    if (!fitted && attempts > 0) {
      attempts -= 1;
      requestFrame(runFit);
    }
  };

  requestFrame(runFit);
  if (documentLike?.fonts?.ready) {
    documentLike.fonts.ready
      .then(() => {
        requestFrame(runFit);
      })
      .catch(() => {});
  }
}

/**
 * Builds a shared legend model for grouped bar plot entries.
 *
 * @param {Array<object>} entries - Plot entries containing grouped points.
 * @returns {object} Series order, display labels, colors, and legend items.
 */
export function buildGroupedLegendModel(entries) {
  const seriesOrder = [];
  const seenSeries = new Set();
  const displayBySeries = new Map();

  for (const entry of entries) {
    for (const point of entry.points || []) {
      if (!seenSeries.has(point.series)) {
        seenSeries.add(point.series);
        seriesOrder.push(point.series);
      }
      if (!displayBySeries.has(point.series)) {
        displayBySeries.set(point.series, point.displaySeries || point.series);
      }
    }
  }

  const colorBySeries = new Map();
  const items = seriesOrder.map((series, index) => {
    const color = getBarColor(index);
    const label = displayBySeries.get(series) || series;
    colorBySeries.set(series, color);
    return { series, label, color };
  });

  return { seriesOrder, displayBySeries, colorBySeries, items };
}

/**
 * Filters a legend model down to the series present in a point collection.
 *
 * @param {Array<object>} points - Points rendered in a plot.
 * @param {?object} legendModel - Shared legend model.
 * @returns {Array<object>} Legend items used by the points.
 */
export function getLegendItemsForPoints(points, legendModel) {
  if (!legendModel) {
    return [];
  }
  const seriesInPoints = new Set(points.map((point) => point.series));
  return legendModel.items.filter((item) => seriesInPoints.has(item.series));
}

/**
 * Finds grouping fields whose values differ across groups.
 *
 * @param {Array<object>} groups - Plot groups with value maps.
 * @param {Array<string>} fields - Candidate field names.
 * @returns {Array<string>} Fields with more than one normalized value.
 */
export function getVaryingFields(groups, fields) {
  if (!fields.length || groups.length <= 1) {
    return [];
  }
  return fields.filter((field) => {
    const values = new Set(groups.map((group) => normalizeValue(group.values?.[field])));
    return values.size > 1;
  });
}

/**
 * Builds a readable label from selected group fields.
 *
 * @param {object} group - Plot group containing values.
 * @param {Array<string>} labelFields - Field names to include.
 * @param {string} fallback - Label used when no fields are selected.
 * @param {Function} [fieldNameFormatter] - Formatter for field names.
 * @returns {string} Group label text.
 */
export function getGroupLabelForFields(
  group,
  labelFields,
  fallback,
  fieldNameFormatter = (field) => field
) {
  if (labelFields.length === 0) {
    return fallback;
  }
  return labelFields
    .map((field) => `${fieldNameFormatter(field)}=${normalizeValue(group.values[field])}`)
    .join(" | ");
}

/**
 * Recursively collects numeric leaf paths from a metric data object.
 *
 * @param {*} value - Metric data value to inspect.
 * @param {Array<string>} [parts] - Current path parts during recursion.
 * @param {Map<string, Array<string>>} [out] - Accumulator keyed by encoded paths.
 * @returns {Map<string, Array<string>>} Numeric metric leaf paths.
 */
export function collectNumericMetricLeafPaths(value, parts = [], out = new Map()) {
  if (!value || typeof value !== "object") {
    return out;
  }
  for (const [key, child] of Object.entries(value)) {
    const pathParts = [...parts, key];
    if (typeof child === "number" && Number.isFinite(child)) {
      out.set(pathParts.join("|#|"), pathParts);
      continue;
    }
    if (child && typeof child === "object" && !Array.isArray(child)) {
      collectNumericMetricLeafPaths(child, pathParts, out);
    }
  }
  return out;
}

/**
 * Encodes metric path parts into the stable key used by prepared numeric data.
 *
 * @param {Array<string>} parts - Metric path parts.
 * @returns {string} Encoded metric path key.
 */
export function getNumericMetricPathKey(parts) {
  return (parts || []).join("|#|");
}

/**
 * Recursively collects numeric metric paths and values for one evaluation.
 *
 * @param {*} value - Metric data value to inspect.
 * @param {Array<string>} [parts] - Current path parts during recursion.
 * @param {Map<string, object>} [metricPaths] - Path accumulator keyed by encoded path.
 * @param {Map<string, number>} [values] - Numeric value accumulator keyed by encoded path.
 * @returns {{metricPaths: Map<string, object>, values: Map<string, number>}} Prepared numeric data.
 */
function collectNumericMetricLeafData(value, parts = [], metricPaths = new Map(), values = new Map()) {
  if (!value || typeof value !== "object") {
    return { metricPaths, values };
  }
  for (const [key, child] of Object.entries(value)) {
    const pathParts = [...parts, key];
    if (typeof child === "number" && Number.isFinite(child)) {
      const pathKey = getNumericMetricPathKey(pathParts);
      metricPaths.set(pathKey, { key: pathKey, parts: pathParts, label: pathParts.join(".") });
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
 * values. `buildPlotEntries()` uses the same prepared values for aggregation
 * and exposes them as point samples for future `Download data` support.
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
 * @param {Array<object>} evaluations - Evaluation records.
 * @returns {Array<object>} Sorted metric path records.
 */
export function collectPreparedNumericMetricPaths(evaluations) {
  const metricPaths = new Map();
  for (const evaluation of evaluations || []) {
    for (const [key, metricPath] of prepareNumericMetricEvaluationData(evaluation).metricPaths) {
      metricPaths.set(key, metricPath);
    }
  }
  return Array.from(metricPaths.values()).sort((a, b) => a.label.localeCompare(b.label));
}

/**
 * Splits a metric label into prefix and suffix at the final dot.
 *
 * @param {string} label - Metric label.
 * @returns {{prefix: string, suffix: string}} Split label components.
 */
export function splitMetricLabelAtLastDot(label) {
  const lastDotIndex = label.lastIndexOf(".");
  if (lastDotIndex === -1) {
    return { prefix: "(root)", suffix: label };
  }
  return {
    prefix: label.slice(0, lastDotIndex),
    suffix: label.slice(lastDotIndex + 1),
  };
}

/**
 * Converts metric paths and evaluation groups into plottable bar entries.
 *
 * @param {object} options - Plot entry construction inputs.
 * @returns {Array<object>} Plot entries with mean/std point data.
 */
export function buildPlotEntries({
  metricPaths,
  plotGroups,
  groupBarFields,
  categoryFields,
  getGroupLabel = getGroupLabelForFields,
  displayGroupFieldName = (field) => field,
}) {
  const entries = [];
  for (const metricPath of metricPaths) {
    const metricPathKey = metricPath.key || getNumericMetricPathKey(metricPath.parts);
    const points = [];
    plotGroups.forEach((group, index) => {
      const samples = group.evaluations
        .map((evaluation) => {
          const value = prepareNumericMetricEvaluationData(evaluation).values.get(metricPathKey);
          if (!Number.isFinite(value)) {
            return null;
          }
          return {
            runDir: normalizeValue(evaluation?.runDir),
            metricLabel: metricPath.label,
            metricPath: metricPath.parts,
            value,
          };
        })
        .filter(Boolean);
      const values = samples.map((sample) => sample.value);
      const stats = meanAndStd(values);
      if (!stats) {
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
        mean: stats.mean,
        std: stats.std,
        samples,
      });
    });
    if (!points.length) {
      continue;
    }
    const split = splitMetricLabelAtLastDot(metricPath.label);
    entries.push({ metricLabel: metricPath.label, parts: metricPath.parts, points, ...split });
  }
  return entries;
}

/**
 * Groups metric plot entries into bar plot tabs.
 *
 * @param {Array<object>} plotEntries - Entries produced by buildPlotEntries.
 * @param {object} [options] - Tab grouping options.
 * @returns {Map<string, Array<object>>} Tab map keyed by prefix or suffix.
 */
export function buildBarsTabMap(plotEntries, { plotTabsBy = "prefix" } = {}) {
  const tabMap = new Map();
  for (const entry of plotEntries) {
    const tabKey = plotTabsBy === "suffix" ? entry.suffix : entry.prefix;
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
 * @param {Array<object>} plotEntries - Error metric plot entries.
 * @returns {Map<string, Array<object>>} Tab map for available error sections.
 */
export function buildErrorsTabMap(plotEntries) {
  const totalKeys = new Set(["with_error", "no_error"]);
  const total = plotEntries.filter((entry) => totalKeys.has(entry.parts[0]));
  const details = plotEntries.filter((entry) => !totalKeys.has(entry.parts[0]));
  const tabMap = new Map();
  if (total.length) {
    tabMap.set("total", total);
  }
  if (details.length) {
    tabMap.set("details", details);
  }
  return tabMap;
}
