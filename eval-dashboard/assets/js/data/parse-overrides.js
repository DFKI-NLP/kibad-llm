/**
 * Lightweight Hydra overrides parsing helpers for imported eval-dashboard runs.
 */

/**
 * Parse the current `.hydra/overrides.yaml` list-item format into a key-value object.
 *
 * Phase 7 intentionally preserves the dashboard's existing permissive semantics:
 * blank lines, comments, non-list-item lines, and lines without `=` are ignored.
 *
 * @param {string} text - Raw overrides file contents.
 * @returns {Record<string, string>} Parsed override map.
 */
export function parseOverridesYaml(text) {
  const result = {};
  const lines = text.split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    if (!trimmed.startsWith("- ")) {
      continue;
    }
    const item = trimmed.slice(2).trim();
    const separatorIndex = item.indexOf("=");
    if (separatorIndex === -1) {
      continue;
    }
    const key = item.slice(0, separatorIndex).replace(/^\++/, "").trim();
    result[key] = item.slice(separatorIndex + 1).trim();
  }
  return result;
}
