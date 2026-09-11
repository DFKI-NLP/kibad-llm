/**
 * Text-formatting helpers shared across eval dashboard plot labels and filenames.
 */

/**
 * Strip display-only suffixes from a plot title to recover a stable export prefix.
 *
 * @param {unknown} title - The raw title text.
 * @returns {string} A stable title prefix suitable for export naming.
 */
export function getFigureTitlePrefix(title) {
  const text = String(title ?? "").trim();
  return text
    .replace(/\s*\(mean ± std\).*$/u, "")
    .replace(/\s*\(\d+\s+grouped\s+evals?(?:\s+per\s+cell)?\)$/iu, "")
    .replace(/\s*\(\d+\s+grouped\s+evaluations\)$/iu, "")
    .trim() || text || "figure";
}

/**
 * Normalize free-form figure titles into filesystem-safe export filenames.
 *
 * @param {unknown} title - The raw title text.
 * @returns {string} A sanitized filename stem.
 */
export function sanitizeFigureFilename(title) {
  const normalized = String(title ?? "")
    .normalize("NFKD")
    .replace(/[<>:"/\\|?*\u0000-\u001f]+/g, " - ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/[. ]+$/g, "");
  return (normalized || "figure").slice(0, 180);
}

/**
 * Shorten a dotted label to the segment after its last dot.
 *
 * @param {unknown} label - The raw label text.
 * @returns {string} The shortened label.
 */
export function splitLabelByLastDot(label) {
  const text = String(label ?? "");
  const lastDotIndex = text.lastIndexOf(".");
  return lastDotIndex === -1 ? text : text.slice(lastDotIndex + 1);
}
