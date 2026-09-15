/**
 * GitHub source adapter helpers for importing eval-dashboard runs.
 */

import { isRelevantEvaluationFilePath } from "./file-loader.js";

/**
 * Parse a GitHub tree URL into owner, repository, and unresolved ref/path components.
 *
 * @param {string} rawUrl - Raw GitHub tree URL.
 * @returns {{owner: string, repo: string, refAndPath: string}} Parsed tree-url parts.
 * @throws {Error} If the URL is invalid or not a GitHub tree URL.
 */
export function parseGitHubTreeUrl(rawUrl) {
  let parsedUrl;
  try {
    parsedUrl = new URL(String(rawUrl || "").trim());
  } catch {
    throw new Error("Enter a valid GitHub tree URL.");
  }
  const hostname = parsedUrl.hostname.replace(/^www\./, "").toLowerCase();
  if (hostname !== "github.com") {
    throw new Error("Only github.com tree URLs are supported right now.");
  }
  const pathParts = parsedUrl.pathname.split("/").filter(Boolean);
  if (pathParts.length < 4 || pathParts[2] !== "tree") {
    throw new Error("Use a GitHub folder URL of the form /OWNER/REPO/tree/REF/path/to/folder.");
  }
  return {
    owner: pathParts[0],
    repo: pathParts[1].replace(/\.git$/i, ""),
    refAndPath: pathParts.slice(3).join("/"),
  };
}

/**
 * Check whether a value looks like a commit SHA.
 *
 * @param {unknown} value - Candidate ref segment.
 * @returns {boolean} Whether the value looks like a Git commit SHA.
 */
export function looksLikeCommitSha(value) {
  return /^[0-9a-f]{7,40}$/i.test(String(value || ""));
}

/**
 * Normalize a GitHub folder path by stripping leading and trailing slashes.
 *
 * @param {string} folderPath - Raw folder path.
 * @returns {string} Normalized folder path.
 */
export function normalizeFolderPath(folderPath) {
  return String(folderPath || "").replace(/^\/+|\/+$/g, "");
}

/**
 * Build one GitHub contents API URL for a repository path and ref.
 *
 * @param {string} owner - Repository owner.
 * @param {string} repo - Repository name.
 * @param {string} path - Repository-relative contents path.
 * @param {string} ref - Git ref or commit SHA.
 * @returns {string} GitHub contents API URL.
 */
export function buildGitHubContentsUrl(owner, repo, path, ref) {
  const encodedOwner = encodeURIComponent(owner);
  const encodedRepo = encodeURIComponent(repo);
  const normalizedPath = String(path || "")
    .split("/")
    .filter(Boolean)
    .map((segment) => encodeURIComponent(segment))
    .join("/");
  const baseUrl = `https://api.github.com/repos/${encodedOwner}/${encodedRepo}/contents${normalizedPath ? `/${normalizedPath}` : ""}`;
  const url = new URL(baseUrl);
  url.searchParams.set("ref", ref);
  return url.toString();
}

/**
 * Derive the shared GitHub source label used by the dashboard load summary.
 *
 * @param {{owner: string, repo: string, ref: string, folderPath: string}} params - GitHub source parts.
 * @returns {string} Canonical GitHub source label.
 */
export function createGitHubSourceLabel({ owner, repo, ref, folderPath }) {
  const sourcePath = normalizeFolderPath(folderPath) || ".";
  return `github:${owner}/${repo}@${ref}:${sourcePath}`;
}

/**
 * Fetch a GitHub API resource with the dashboard's current transport defaults.
 *
 * @param {string} url - GitHub API URL.
 * @param {{token?: string, accept?: string, responseType?: "json" | "text" | "arrayBuffer", allowNotFound?: boolean, statusText?: string, fetchImpl?: typeof fetch}} [options={}] - Fetch options.
 * @returns {Promise<unknown>} Parsed response payload.
 */
async function fetchGitHubResource(url, options = {}) {
  const {
    token = "",
    accept = "application/vnd.github+json",
    responseType = "json",
    allowNotFound = false,
    statusText = "",
    fetchImpl = fetch,
  } = options;
  const headers = {
    Accept: accept,
    "X-GitHub-Api-Version": "2022-11-28",
  };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetchImpl(url, { headers });
  if (allowNotFound && response.status === 404) {
    return null;
  }
  if (!response.ok) {
    let detail = "";
    try {
      const errorPayload = await response.json();
      if (errorPayload?.message) {
        detail = ` ${errorPayload.message}`;
      }
    } catch {
      try {
        const errorText = await response.text();
        if (errorText.trim()) {
          detail = ` ${errorText.trim()}`;
        }
      } catch {
        // Ignore secondary error parsing failures.
      }
    }
    throw new Error(`${statusText || "GitHub request failed"} (${response.status}).${detail}`.trim());
  }
  if (responseType === "text") {
    return response.text();
  }
  if (responseType === "arrayBuffer") {
    return response.arrayBuffer();
  }
  return response.json();
}

/**
 * Check whether one GitHub branch or tag ref exists.
 *
 * @param {string} owner - Repository owner.
 * @param {string} repo - Repository name.
 * @param {string} refKind - GitHub ref namespace such as `heads` or `tags`.
 * @param {string} candidateRef - Candidate ref name.
 * @param {{token?: string, fetchImpl?: typeof fetch}} [options={}] - Transport options.
 * @returns {Promise<boolean>} Whether the candidate ref exists.
 */
export async function gitHubRefExists(owner, repo, refKind, candidateRef, options = {}) {
  const encodedOwner = encodeURIComponent(owner);
  const encodedRepo = encodeURIComponent(repo);
  const encodedRef = encodeURIComponent(candidateRef);
  const url = `https://api.github.com/repos/${encodedOwner}/${encodedRepo}/git/ref/${refKind}/${encodedRef}`;
  const result = await fetchGitHubResource(url, {
    ...options,
    allowNotFound: true,
    statusText: `GitHub ref lookup failed for ${candidateRef}`,
  });
  return Boolean(result);
}

/**
 * Resolve the `tree/REF/path` suffix of a GitHub tree URL into a concrete ref and folder path.
 *
 * @param {string} owner - Repository owner.
 * @param {string} repo - Repository name.
 * @param {string} refAndPath - Unresolved `tree/` suffix.
 * @param {{token?: string, fetchImpl?: typeof fetch, refExists?: (refKind: string, candidateRef: string) => Promise<boolean>}} [options={}] - Ref-resolution options.
 * @returns {Promise<{ref: string, folderPath: string, refType: "branch" | "tag" | "commit"}>} Resolved ref information.
 */
export async function resolveGitHubRefAndFolder(owner, repo, refAndPath, options = {}) {
  const { token = "", fetchImpl = fetch, refExists = null } = options;
  const segments = String(refAndPath || "").split("/").filter(Boolean);
  if (!segments.length) {
    throw new Error("The GitHub tree URL does not include a branch, tag, or commit SHA.");
  }

  const doesRefExist = refExists || ((refKind, candidateRef) => (
    gitHubRefExists(owner, repo, refKind, candidateRef, { token, fetchImpl })
  ));

  for (let segmentCount = segments.length; segmentCount >= 1; segmentCount -= 1) {
    const candidateRef = segments.slice(0, segmentCount).join("/");
    const folderPath = segments.slice(segmentCount).join("/");
    if (await doesRefExist("heads", candidateRef)) {
      return { ref: candidateRef, folderPath, refType: "branch" };
    }
    if (await doesRefExist("tags", candidateRef)) {
      return { ref: candidateRef, folderPath, refType: "tag" };
    }
  }

  const commitCandidate = segments[0];
  if (looksLikeCommitSha(commitCandidate)) {
    return {
      ref: commitCandidate,
      folderPath: segments.slice(1).join("/"),
      refType: "commit",
    };
  }

  throw new Error("Could not resolve a matching GitHub branch, tag, or commit SHA from the URL.");
}

/**
 * Recursively enumerate relevant dashboard files below one GitHub folder.
 *
 * @param {string} owner - Repository owner.
 * @param {string} repo - Repository name.
 * @param {string} ref - Resolved ref.
 * @param {string} folderPath - Repository-relative folder path.
 * @param {{token?: string, fetchImpl?: typeof fetch, onStatus?: ({title: string, details: string[]}) => void, isRelevantPath?: (path: string) => boolean}} [options={}] - Listing options.
 * @returns {Promise<Array<{type: string, path: string, size?: number, url: string}>>} Relevant GitHub file descriptors.
 */
export async function listGitHubFolderContentsRecursive(owner, repo, ref, folderPath, options = {}) {
  const {
    token = "",
    fetchImpl = fetch,
    onStatus = () => {},
    isRelevantPath = isRelevantEvaluationFilePath,
  } = options;
  const normalizedFolderPath = normalizeFolderPath(folderPath);
  const pendingDirs = [normalizedFolderPath];
  const relevantFiles = [];
  let scannedDirs = 0;

  while (pendingDirs.length) {
    const currentDir = pendingDirs.pop();
    onStatus({
      title: "Enumerating GitHub folder",
      details: [
        `${owner}/${repo}@${ref}`,
        `Folder: ${normalizedFolderPath || "."}`,
        `Directories scanned: ${scannedDirs}`,
        `Relevant files found: ${relevantFiles.length}`,
      ],
    });
    const payload = await fetchGitHubResource(buildGitHubContentsUrl(owner, repo, currentDir, ref), {
      token,
      fetchImpl,
      statusText: `GitHub directory listing failed for ${currentDir || "/"}`,
    });
    const items = Array.isArray(payload) ? payload : [payload];
    scannedDirs += 1;
    for (const item of items) {
      if (item.type === "dir") {
        pendingDirs.push(item.path);
      } else if (item.type === "file" && isRelevantPath(item.path)) {
        relevantFiles.push(item);
      }
    }
  }

  return relevantFiles.sort((left, right) => left.path.localeCompare(right.path));
}

/**
 * Fetch one GitHub file as text.
 *
 * @param {string} apiUrl - GitHub contents API URL.
 * @param {string} ref - Resolved Git ref.
 * @param {{token?: string, fetchImpl?: typeof fetch}} [options={}] - Transport options.
 * @returns {Promise<string>} Raw file text.
 */
async function fetchGitHubFileText(apiUrl, ref, options = {}) {
  const url = new URL(apiUrl);
  url.searchParams.set("ref", ref);
  return /** @type {Promise<string>} */ (fetchGitHubResource(url.toString(), {
    ...options,
    accept: "application/vnd.github.raw+json",
    responseType: "text",
    statusText: `GitHub file fetch failed for ${url.pathname}`,
  }));
}

/**
 * Fetch relevant GitHub files and emit plain progress updates while preserving file order.
 *
 * @param {Array<{path: string, size?: number, url: string}>} files - Relevant GitHub file descriptors.
 * @param {{ref: string, token?: string, sourceLabel: string, folderPath: string, fetchImpl?: typeof fetch, onProgress?: ({completedFiles: number, totalFiles: number, completedBytes: number, totalBytes: number, label: string}) => void}} options - File-fetch options.
 * @returns {Promise<Array<{path: string, text: string}>>} Raw ingestion entries.
 */
export async function fetchGitHubEntriesWithProgress(files, options) {
  const {
    ref,
    token = "",
    sourceLabel,
    folderPath,
    fetchImpl = fetch,
    onProgress = () => {},
  } = options;
  const normalizedFolderPath = normalizeFolderPath(folderPath);
  const prefix = normalizedFolderPath ? `${normalizedFolderPath}/` : "";
  const totalFiles = files.length;
  const totalBytes = files.reduce((sum, file) => sum + Math.max(0, Number(file.size || 0)), 0);
  let completedFiles = 0;
  let completedBytes = 0;
  const concurrency = Math.min(8, totalFiles || 1);
  const results = new Array(totalFiles);
  let nextIndex = 0;

  onProgress({
    completedFiles,
    totalFiles,
    completedBytes,
    totalBytes,
    label: "Fetching GitHub files",
  });

  async function worker() {
    while (true) {
      const currentIndex = nextIndex;
      nextIndex += 1;
      if (currentIndex >= totalFiles) {
        return;
      }
      const file = files[currentIndex];
      const relativePath = prefix && file.path.startsWith(prefix)
        ? file.path.slice(prefix.length)
        : file.path;
      const text = await fetchGitHubFileText(file.url, ref, { token, fetchImpl });
      results[currentIndex] = {
        path: `${sourceLabel}/${relativePath}`,
        text,
      };
      completedFiles += 1;
      completedBytes += Math.max(0, Number(file.size || 0));
      onProgress({
        completedFiles,
        totalFiles,
        completedBytes,
        totalBytes,
        label: "Fetching GitHub files",
      });
    }
  }

  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  return results;
}

/**
 * Load raw eval-dashboard entries from a GitHub tree URL.
 *
 * @param {string} rawUrl - GitHub tree URL.
 * @param {{token?: string, fetchImpl?: typeof fetch, onStatus?: ({title: string, details: string[]}) => void, onProgress?: ({completedFiles: number, totalFiles: number, completedBytes: number, totalBytes: number, label: string}) => void}} [options={}] - Loader options.
 * @returns {Promise<{parsed: {owner: string, repo: string, refAndPath: string}, ref: string, refType: "branch" | "tag" | "commit", folderPath: string, sourceLabel: string, files: Array<{type: string, path: string, size?: number, url: string}>, entries: Array<{path: string, text: string}>, totalBytes: number}>} Loaded raw source payload.
 */
export async function loadGitHubEntriesFromTreeUrl(rawUrl, options = {}) {
  const {
    token = "",
    fetchImpl = fetch,
    onStatus = () => {},
    onProgress = () => {},
  } = options;
  const trimmedUrl = String(rawUrl || "").trim();
  if (!trimmedUrl) {
    throw new Error("Enter a GitHub tree URL first.");
  }

  const parsed = parseGitHubTreeUrl(trimmedUrl);
  onStatus({ title: "Resolving GitHub ref", details: [trimmedUrl] });
  const { ref, folderPath, refType } = await resolveGitHubRefAndFolder(parsed.owner, parsed.repo, parsed.refAndPath, {
    token,
    fetchImpl,
  });
  const sourceLabel = createGitHubSourceLabel({
    owner: parsed.owner,
    repo: parsed.repo,
    ref,
    folderPath,
  });

  onStatus({
    title: "Resolved GitHub ref",
    details: [
      `Repository: ${parsed.owner}/${parsed.repo}`,
      `Ref (${refType}): ${ref}`,
      `Folder: ${normalizeFolderPath(folderPath) || "."}`,
    ],
  });
  const files = await listGitHubFolderContentsRecursive(parsed.owner, parsed.repo, ref, folderPath, {
    token,
    fetchImpl,
    onStatus,
  });
  const totalBytes = files.reduce((sum, file) => sum + Math.max(0, Number(file.size || 0)), 0);
  if (!files.length) {
    return {
      parsed,
      ref,
      refType,
      folderPath,
      sourceLabel,
      files,
      entries: [],
      totalBytes,
    };
  }

  onStatus({
    title: "Preparing GitHub file downloads",
    details: [sourceLabel, `Relevant files found: ${files.length}`],
  });
  const entries = await fetchGitHubEntriesWithProgress(files, {
    ref,
    token,
    sourceLabel,
    folderPath,
    fetchImpl,
    onProgress,
  });
  return {
    parsed,
    ref,
    refType,
    folderPath,
    sourceLabel,
    files,
    entries,
    totalBytes,
  };
}
