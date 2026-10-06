/**
 * Generic object-flattening helpers for the eval dashboard runtime.
 */

/**
 * Flatten a nested object into dot-separated keys.
 *
 * Arrays keep the dashboard's existing behavior and are serialized as JSON strings.
 *
 * @param {unknown} obj - The value to flatten.
 * @param {string} [prefix=""] - Optional key prefix for nested recursion.
 * @param {Record<string, unknown>} [out={}] - Mutable output accumulator.
 * @returns {Record<string, unknown>} The flattened key-value mapping.
 */
export function flattenObject(obj, prefix = "", out = {}) {
  if (!obj || typeof obj !== "object") {
    return out;
  }
  for (const [key, value] of Object.entries(obj)) {
    const fullKey = prefix ? `${prefix}.${key}` : key;
    if (Array.isArray(value)) {
      out[fullKey] = JSON.stringify(value);
    } else if (value && typeof value === "object") {
      flattenObject(value, fullKey, out);
    } else {
      out[fullKey] = value;
    }
  }
  return out;
}

/**
 * Return a shallow copy without the excluded top-level keys.
 *
 * @param {Record<string, unknown>} obj - Source object.
 * @param {Set<string>} excludedKeys - Keys to omit from the copy.
 * @returns {Record<string, unknown>} The filtered object.
 */
export function omitTopLevelKeys(obj, excludedKeys) {
  return Object.fromEntries(
    Object.entries(obj).filter(([key]) => !excludedKeys.has(key))
  );
}

/**
 * Traverse an object-like value by a list of path segments.
 *
 * @param {unknown} value - Root value.
 * @param {string[]} pathParts - Ordered property names to follow.
 * @returns {unknown | null} The resolved value, or `null` when the path does not exist.
 */
export function getValueAtPath(value, pathParts) {
  let current = value;
  for (const part of pathParts) {
    if (!current || typeof current !== "object" || !(part in current)) {
      return null;
    }
    current = current[part];
  }
  return current;
}
