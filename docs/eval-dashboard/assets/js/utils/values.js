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
