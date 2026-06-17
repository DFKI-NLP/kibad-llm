/**
 * Browser-free logic tests for the eval-dashboard GitHub loader helpers.
 */

import assert from "node:assert/strict";
import test from "node:test";

import {
  buildGitHubContentsUrl,
  createGitHubSourceLabel,
  fetchGitHubEntriesWithProgress,
  listGitHubFolderContentsRecursive,
  loadGitHubEntriesFromTreeUrl,
  normalizeFolderPath,
  parseGitHubTreeUrl,
  resolveGitHubRefAndFolder,
} from "../../../../docs/eval-dashboard/assets/js/data/git-loader.js";

function createJsonResponse(body, { status = 200, ok = true } = {}) {
  return {
    status,
    ok,
    async json() {
      return body;
    },
    async text() {
      return typeof body === "string" ? body : JSON.stringify(body);
    },
  };
}

function createTextResponse(body, { status = 200, ok = true } = {}) {
  return {
    status,
    ok,
    async json() {
      return { message: body };
    },
    async text() {
      return body;
    },
  };
}

/**
 * Ensure GitHub tree URL parsing preserves the Phase 8 source-adapter contract.
 */
test("git-loader parses GitHub tree URLs into owner, repo, and ref/path", () => {
  assert.deepEqual(
    parseGitHubTreeUrl("https://github.com/DFKI-NLP/kibad-llm/tree/main/logs/evaluate"),
    {
      owner: "DFKI-NLP",
      repo: "kibad-llm",
      refAndPath: "main/logs/evaluate",
    }
  );
  assert.throws(() => parseGitHubTreeUrl("https://example.com/foo"), /github\.com/);
  assert.throws(() => parseGitHubTreeUrl("https://github.com/DFKI-NLP/kibad-llm/issues/1"), /Use a GitHub folder URL/);
});

/**
 * Ensure ref resolution prefers matching branches or tags before falling back to commit SHAs.
 */
test("git-loader resolves refs and folder paths from tree URL suffixes", async () => {
  const branchResolved = await resolveGitHubRefAndFolder("DFKI-NLP", "kibad-llm", "feature/phase-8/logs/evaluate", {
    refExists: async (refKind, candidateRef) => refKind === "heads" && candidateRef === "feature/phase-8",
  });
  assert.deepEqual(branchResolved, {
    ref: "feature/phase-8",
    folderPath: "logs/evaluate",
    refType: "branch",
  });

  const commitResolved = await resolveGitHubRefAndFolder(
    "DFKI-NLP",
    "kibad-llm",
    "0123abcd/logs/evaluate",
    {
      refExists: async () => false,
    }
  );
  assert.deepEqual(commitResolved, {
    ref: "0123abcd",
    folderPath: "logs/evaluate",
    refType: "commit",
  });
});

/**
 * Ensure ref resolution also covers the tag branch and the unresolved-ref failure path.
 */
test("git-loader resolves tags and rejects unresolved refs", async () => {
  const tagResolved = await resolveGitHubRefAndFolder("DFKI-NLP", "kibad-llm", "release/v1.2/logs/evaluate", {
    refExists: async (refKind, candidateRef) => refKind === "tags" && candidateRef === "release/v1.2",
  });
  assert.deepEqual(tagResolved, {
    ref: "release/v1.2",
    folderPath: "logs/evaluate",
    refType: "tag",
  });

  await assert.rejects(
    () => resolveGitHubRefAndFolder("DFKI-NLP", "kibad-llm", "not-a-real-ref/logs/evaluate", {
      refExists: async () => false,
    }),
    /Could not resolve a matching GitHub branch, tag, or commit SHA/
  );
});

/**
 * Ensure contents URLs, folder normalization, and source labels remain deterministic helpers.
 */
test("git-loader builds deterministic contents URLs and source labels", () => {
  assert.equal(normalizeFolderPath("/logs/evaluate/"), "logs/evaluate");
  assert.equal(
    buildGitHubContentsUrl("DFKI-NLP", "kibad-llm", "logs/evaluate/run a", "main"),
    "https://api.github.com/repos/DFKI-NLP/kibad-llm/contents/logs/evaluate/run%20a?ref=main"
  );
  assert.equal(
    createGitHubSourceLabel({
      owner: "DFKI-NLP",
      repo: "kibad-llm",
      ref: "main",
      folderPath: "logs/evaluate",
    }),
    "github:DFKI-NLP/kibad-llm@main:logs/evaluate"
  );
});

/**
 * Ensure recursive GitHub listing stays focused on relevant dashboard files while reporting plain
 * status updates.
 */
test("git-loader recursively lists only relevant evaluation files", async () => {
  const statuses = [];
  const responses = new Map([
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/contents/logs/evaluate?ref=main",
      createJsonResponse([
        { type: "dir", path: "logs/evaluate/run_a" },
        { type: "file", path: "logs/evaluate/ignore.txt", url: "https://api.github.com/file-ignore", size: 1 },
      ]),
    ],
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/contents/logs/evaluate/run_a?ref=main",
      createJsonResponse([
        {
          type: "file",
          path: "logs/evaluate/run_a/job_return_value.json",
          url: "https://api.github.com/file-job",
          size: 2,
        },
        {
          type: "file",
          path: "logs/evaluate/run_a/.hydra/overrides.yaml",
          url: "https://api.github.com/file-overrides",
          size: 3,
        },
      ]),
    ],
  ]);
  const fetchImpl = async (url) => responses.get(url) || createJsonResponse({ message: "missing" }, { status: 404, ok: false });

  const files = await listGitHubFolderContentsRecursive("DFKI-NLP", "kibad-llm", "main", "logs/evaluate", {
    fetchImpl,
    onStatus: (status) => statuses.push(status),
  });

  assert.deepEqual(
    files.map((file) => file.path),
    [
      "logs/evaluate/run_a/.hydra/overrides.yaml",
      "logs/evaluate/run_a/job_return_value.json",
    ]
  );
  assert.ok(statuses.some((status) => status.title === "Enumerating GitHub folder"));
});

/**
 * Ensure GitHub file fetching keeps entry order stable and emits plain progress updates.
 */
test("git-loader fetches GitHub entries with stable order and progress callbacks", async () => {
  const progressEvents = [];
  const fetchImpl = async (url) => {
    if (url.includes("file-job")) {
      return createTextResponse('{"version": 2}');
    }
    if (url.includes("file-overrides")) {
      return createTextResponse("- name=example");
    }
    throw new Error(`Unexpected URL: ${url}`);
  };

  const entries = await fetchGitHubEntriesWithProgress(
    [
      {
        path: "logs/evaluate/run_a/job_return_value.json",
        size: 16,
        url: "https://api.github.com/file-job",
      },
      {
        path: "logs/evaluate/run_a/.hydra/overrides.yaml",
        size: 14,
        url: "https://api.github.com/file-overrides",
      },
    ],
    {
      ref: "main",
      sourceLabel: "github:DFKI-NLP/kibad-llm@main:logs/evaluate",
      folderPath: "logs/evaluate",
      fetchImpl,
      onProgress: (progress) => progressEvents.push(progress),
    }
  );

  assert.deepEqual(entries, [
    {
      path: "github:DFKI-NLP/kibad-llm@main:logs/evaluate/run_a/job_return_value.json",
      text: '{"version": 2}',
    },
    {
      path: "github:DFKI-NLP/kibad-llm@main:logs/evaluate/run_a/.hydra/overrides.yaml",
      text: "- name=example",
    },
  ]);
  assert.equal(progressEvents[0].completedFiles, 0);
  assert.equal(progressEvents.at(-1).completedFiles, 2);
  assert.equal(progressEvents.at(-1).totalFiles, 2);
});

/**
 * Ensure the high-level GitHub loader keeps its explicit empty-input validation.
 */
test("git-loader rejects empty tree URLs before issuing network requests", async () => {
  await assert.rejects(
    () => loadGitHubEntriesFromTreeUrl("   "),
    /Enter a GitHub tree URL first/
  );
});

/**
 * Ensure the high-level GitHub loader returns a clean no-files result when a resolved folder contains
 * no relevant dashboard files.
 */
test("git-loader returns an empty result when no relevant files are found", async () => {
  const statuses = [];
  const progressEvents = [];
  const responses = new Map([
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/git/ref/heads/main",
      createJsonResponse({ ref: "refs/heads/main" }),
    ],
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/contents/logs/evaluate?ref=main",
      createJsonResponse([]),
    ],
  ]);
  const fetchImpl = async (url) => responses.get(url) || createJsonResponse({ message: `missing ${url}` }, { status: 404, ok: false });

  const result = await loadGitHubEntriesFromTreeUrl(
    "https://github.com/DFKI-NLP/kibad-llm/tree/main/logs/evaluate",
    {
      fetchImpl,
      onStatus: (status) => statuses.push(status),
      onProgress: (progress) => progressEvents.push(progress),
    }
  );

  assert.equal(result.sourceLabel, "github:DFKI-NLP/kibad-llm@main:logs/evaluate");
  assert.deepEqual(result.files, []);
  assert.deepEqual(result.entries, []);
  assert.equal(result.totalBytes, 0);
  assert.ok(statuses.some((status) => status.title === "Resolved GitHub ref"));
  assert.ok(!statuses.some((status) => status.title === "Preparing GitHub file downloads"));
  assert.equal(progressEvents.length, 0);
});

/**
 * Ensure the high-level GitHub loader keeps the Phase 8 orchestration boundary intact by returning
 * plain source data plus plain status/progress events.
 */
test("git-loader loads GitHub tree URLs into plain entries, status updates, and progress updates", async () => {
  const statuses = [];
  const progressEvents = [];
  const responses = new Map([
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/git/ref/heads/main",
      createJsonResponse({ ref: "refs/heads/main" }),
    ],
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/contents/logs/evaluate?ref=main",
      createJsonResponse([
        { type: "dir", path: "logs/evaluate/run_a" },
      ]),
    ],
    [
      "https://api.github.com/repos/DFKI-NLP/kibad-llm/contents/logs/evaluate/run_a?ref=main",
      createJsonResponse([
        {
          type: "file",
          path: "logs/evaluate/run_a/job_return_value.json",
          url: "https://api.github.com/file-job",
          size: 16,
        },
        {
          type: "file",
          path: "logs/evaluate/run_a/.hydra/overrides.yaml",
          url: "https://api.github.com/file-overrides",
          size: 14,
        },
      ]),
    ],
    [
      "https://api.github.com/file-job?ref=main",
      createTextResponse('{"version": 2}'),
    ],
    [
      "https://api.github.com/file-overrides?ref=main",
      createTextResponse("- name=example"),
    ],
  ]);
  const fetchImpl = async (url) => responses.get(url) || createJsonResponse({ message: `missing ${url}` }, { status: 404, ok: false });

  const result = await loadGitHubEntriesFromTreeUrl(
    "https://github.com/DFKI-NLP/kibad-llm/tree/main/logs/evaluate",
    {
      fetchImpl,
      onStatus: (status) => statuses.push(status),
      onProgress: (progress) => progressEvents.push(progress),
    }
  );

  assert.equal(result.ref, "main");
  assert.equal(result.refType, "branch");
  assert.equal(result.sourceLabel, "github:DFKI-NLP/kibad-llm@main:logs/evaluate");
  assert.equal(result.entries.length, 2);
  assert.ok(statuses.some((status) => status.title === "Resolving GitHub ref"));
  assert.ok(statuses.some((status) => status.title === "Preparing GitHub file downloads"));
  assert.equal(progressEvents.at(-1).completedFiles, 2);
});
