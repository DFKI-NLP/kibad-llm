/**
 * Value-normalization helpers shared by eval dashboard selectors and renderers.
 */

/**
 * Normalize dashboard values into the string/object representation used by the UI.
 *
 * @param {unknown} value - The raw value.
 * @returns {string} The normalized display value.
 */
export function normalizeValue(value) {
  if (value === null || value === undefined) return "";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

/**
 * Determine whether a value is effectively blank after normalization.
 *
 * @param {unknown} value - The value to inspect.
 * @returns {boolean} Whether the value should be treated as missing.
 */
export function isMissingValue(value) {
  return normalizeValue(value).trim() === "";
}

/**
 * Apply a configured default when the raw value is missing.
 *
 * @param {unknown} rawValue - The primary value.
 * @param {unknown} defaultValue - The fallback value.
 * @returns {string} The effective normalized value.
 */
export function getEffectiveValue(rawValue, defaultValue) {
  if (isMissingValue(rawValue) && !isMissingValue(defaultValue)) {
    return normalizeValue(defaultValue);
  }
  return normalizeValue(rawValue);
}

/**
 * Collect sorted, distinct, non-empty suggestion values.
 *
 * @param {unknown[]} values - Candidate values collected from dashboard data.
 * @returns {string[]} Sorted normalized suggestions.
 */
export function collectSuggestionValues(values) {
  return Array.from(
    new Set(
      values
        .map((value) => normalizeValue(value))
        .filter((value) => value.trim() !== "")
    )
  ).sort((a, b) => a.localeCompare(b));
}

/**
 * Find columns whose normalized values vary across the provided items.
 *
 * @template T
 * @param {T[]} items - Items to inspect.
 * @param {string[]} columns - Candidate columns.
 * @param {(item: T, column: string) => unknown} valueGetter - Callback returning the value for a given item/column.
 * @returns {string[]} Columns containing more than one distinct value.
 */
export function getColumnsWithMultipleValues(items, columns, valueGetter) {
  if (!Array.isArray(items) || items.length <= 1) {
    return [];
  }
  return columns.filter((column) => {
    const values = new Set();
    for (const item of items) {
      values.add(normalizeValue(valueGetter(item, column)));
      if (values.size > 1) {
        return true;
      }
    }
    return false;
  });
}

/**
 * Build a stable JSON signature from an object's normalized key-value pairs.
 *
 * @param {Record<string, unknown>} obj - Object to serialize.
 * @returns {string} Stable normalized signature text.
 */
export function getStableObjectSignature(obj) {
  return JSON.stringify(
    Object.fromEntries(
      Object.entries(obj)
        .map(([key, value]) => [key, normalizeValue(value)])
        .sort(([keyA], [keyB]) => keyA.localeCompare(keyB))
    )
  );
}

/**
 * Compute the population mean and standard deviation of a numeric sample.
 *
 * @param {number[]} values - Numeric sample values.
 * @returns {{mean: number, std: number} | null} Aggregate statistics, or `null` for an empty sample.
 */
export function meanAndStd(values) {
  if (values.length === 0) {
    return null;
  }
  // Dashboard plots aggregate complete selected-run populations, so the
  // standard deviation divides by N rather than N - 1.
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variance =
    values.reduce((sum, value) => sum + (value - mean) ** 2, 0) / values.length;
  return { mean, std: Math.sqrt(variance) };
}

/**
 * Format a numeric value using a fixed decimal precision.
 *
 * @param {number | string} value - Value to format.
 * @param {number} precision - Number of decimal places.
 * @returns {string} Fixed-precision string representation.
 */
export function formatRounded(value, precision) {
  return Number(value).toFixed(precision);
}

/**
 * Linearly interpolate between two RGB colors.
 *
 * @param {[number, number, number]} startRgb - Start color.
 * @param {[number, number, number]} endRgb - End color.
 * @param {number} t - Interpolation factor, clamped to `[0, 1]`.
 * @returns {string} CSS `rgb(...)` string.
 */
export function interpolateColor(startRgb, endRgb, t) {
  const clamp = Math.max(0, Math.min(1, t));
  const mix = (a, b) => Math.round(a + (b - a) * clamp);
  return `rgb(${mix(startRgb[0], endRgb[0])}, ${mix(startRgb[1], endRgb[1])}, ${mix(startRgb[2], endRgb[2])})`;
}
