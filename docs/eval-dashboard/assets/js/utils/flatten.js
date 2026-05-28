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
