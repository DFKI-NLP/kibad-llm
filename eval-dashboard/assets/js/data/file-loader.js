/**
 * Local-file source adapter helpers for importing eval-dashboard runs.
 */

/**
 * Return the browser-relative path for one selected file.
 *
 * @param {{webkitRelativePath?: unknown} | null | undefined} file - Selected browser file-like object.
 * @returns {string} Relative path string, or an empty string when absent.
 */
export function getFileRelativePath(file) {
  return String(file?.webkitRelativePath || "");
}

/**
 * Check whether a browser-relative file path is one of the dashboard's relevant run files.
 *
 * @param {string} path - Browser-relative file path.
 * @returns {boolean} Whether the path points to a supported evaluation-run file.
 */
export function isRelevantEvaluationFilePath(path) {
  return /(^|\/)\.hydra\/overrides\.yaml$/.test(path) || /(^|\/)job_return_value\.json$/.test(path);
}

/**
 * Derive the current local source label from a browser file selection.
 *
 * @param {ArrayLike<{webkitRelativePath?: unknown}> | Iterable<{webkitRelativePath?: unknown}>} files - Selected files.
 * @returns {string} Human-readable source label.
 */
export function deriveLocalSourceLabel(files) {
  const firstFile = Array.from(files || [])[0];
  const rootSegment = getFileRelativePath(firstFile).split("/").filter(Boolean)[0];
  return rootSegment || "selected folder";
}

/**
 * Read one selected file as UTF-8 text while keeping browser compatibility.
 *
 * @param {{text?: () => Promise<string>}} file - Selected browser file-like object.
 * @returns {Promise<string>} File text.
 */
export async function readTextFile(file) {
  if (typeof file?.text === "function") {
    return String(await file.text());
  }

  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("Failed to read file."));
    reader.readAsText(file);
  });
}

/**
 * Convert a browser file/folder selection into raw `{ path, text }` entries for shared ingestion.
 *
 * @param {ArrayLike<{webkitRelativePath?: unknown, text?: () => Promise<string>}> | Iterable<{webkitRelativePath?: unknown, text?: () => Promise<string>}>} files - Selected files.
 * @returns {Promise<{rootLabel: string, entries: Array<{path: string, text: string}>}>} Raw ingestion payload.
 */
export async function collectLocalEvaluationEntries(files) {
  const normalizedFiles = Array.from(files || []);
  const rootLabel = deriveLocalSourceLabel(normalizedFiles);
  const relevantFiles = normalizedFiles.filter((file) => {
    const relativePath = getFileRelativePath(file);
    return relativePath && isRelevantEvaluationFilePath(relativePath);
  });
  const entries = await Promise.all(relevantFiles.map(async (file) => ({
    path: getFileRelativePath(file),
    text: await readTextFile(file),
  })));
  return { rootLabel, entries };
}
