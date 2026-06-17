import test from "node:test";
import assert from "node:assert/strict";

import {
  initializeGitHubTokenInput,
  initializeGitUrlInputFromQueryParam,
  buildGitUrlQueryParamUrl,
  clearGitUrlQueryParam,
  getStoredGitHubToken,
  normalizeSessionValue,
  persistGitHubToken,
  persistGitHubTokenInputValue,
  readGitUrlQueryParam,
  runGitUrlQueryParamBootstrap,
  setGitUrlQueryParam,
} from "../../../../docs/eval-dashboard/assets/js/browser/session.js";

function createStorageAdapter(initialValue = null) {
  const store = new Map();
  if (initialValue !== null) {
    store.set("evalDashboard.githubToken", initialValue);
  }
  return {
    getItem(key) {
      return store.has(key) ? store.get(key) : null;
    },
    setItem(key, value) {
      store.set(key, value);
    },
    removeItem(key) {
      store.delete(key);
    },
    snapshot() {
      return new Map(store);
    },
  };
}

test("normalizeSessionValue trims strings and converts nullish values to empty strings", () => {
  assert.equal(normalizeSessionValue("  token  "), "token");
  assert.equal(normalizeSessionValue(""), "");
  assert.equal(normalizeSessionValue(null), "");
});

test("GitHub token persistence trims values and clears empty tokens", () => {
  const storageLike = createStorageAdapter();

  persistGitHubToken("  abc123  ", { storageLike });
  assert.equal(getStoredGitHubToken({ storageLike }), "abc123");

  persistGitHubToken("   ", { storageLike });
  assert.equal(getStoredGitHubToken({ storageLike }), "");
  assert.equal(storageLike.snapshot().size, 0);
});

test("initializeGitHubTokenInput hydrates an input-like element from stored token state", () => {
  const storageLike = createStorageAdapter(" persisted-token ");
  const inputElement = { value: "" };

  const token = initializeGitHubTokenInput(inputElement, { storageLike });

  assert.equal(token, " persisted-token ");
  assert.equal(inputElement.value, " persisted-token ");
});

test("GitHub token reads tolerate storage adapter failures", () => {
  const failingStorage = {
    getItem() {
      throw new Error("boom");
    },
  };

  assert.equal(getStoredGitHubToken({ storageLike: failingStorage }), "");
});

test("GitHub token helpers honor custom storage keys and tolerate write failures", () => {
  const storageLike = createStorageAdapter();

  persistGitHubToken("  abc123  ", { storageLike, storageKey: "custom.github.token" });
  assert.equal(getStoredGitHubToken({ storageLike, storageKey: "custom.github.token" }), "abc123");
  assert.equal(getStoredGitHubToken({ storageLike }), "");

  const failingStorage = {
    setItem() {
      throw new Error("boom");
    },
    removeItem() {
      throw new Error("boom");
    },
  };
  assert.doesNotThrow(() => persistGitHubToken("abc123", { storageLike: failingStorage }));
  assert.doesNotThrow(() => persistGitHubToken("   ", { storageLike: failingStorage }));
});

test("persistGitHubTokenInputValue persists the current input value with the existing trim contract", () => {
  const storageLike = createStorageAdapter();
  const inputElement = { value: "  abc123  " };

  assert.equal(persistGitHubTokenInputValue(inputElement, { storageLike }), "abc123");
  assert.equal(getStoredGitHubToken({ storageLike }), "abc123");
});

test("readGitUrlQueryParam returns a trimmed git_url query parameter", () => {
  assert.equal(
    readGitUrlQueryParam({
      locationLike: { search: "?git_url=https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Ftree%2Fmain%2Flogs&other=1" },
    }),
    "https://github.com/org/repo/tree/main/logs"
  );
  assert.equal(readGitUrlQueryParam({ locationLike: { search: "?other=1" } }), "");
});

test("initializeGitUrlInputFromQueryParam hydrates an input-like element from git_url", () => {
  const inputElement = { value: "" };

  const gitUrl = initializeGitUrlInputFromQueryParam(inputElement, {
    locationLike: { search: "?git_url=https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Ftree%2Fmain%2Flogs" },
  });

  assert.equal(gitUrl, "https://github.com/org/repo/tree/main/logs");
  assert.equal(inputElement.value, "https://github.com/org/repo/tree/main/logs");
});

test("buildGitUrlQueryParamUrl sets and removes the git_url query parameter", () => {
  const href = "https://example.test/eval-dashboard/index.html?foo=1";

  assert.equal(
    buildGitUrlQueryParamUrl(href, " https://github.com/org/repo/tree/main/logs "),
    "https://example.test/eval-dashboard/index.html?foo=1&git_url=https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Ftree%2Fmain%2Flogs"
  );
  assert.equal(
    buildGitUrlQueryParamUrl(`${href}&git_url=https%3A%2F%2Fold.example`, ""),
    "https://example.test/eval-dashboard/index.html?foo=1"
  );
});

test("setGitUrlQueryParam and clearGitUrlQueryParam use injected history adapters", () => {
  const locationLike = { href: "https://example.test/eval-dashboard/index.html" };
  const calls = [];
  const historyLike = {
    replaceState: (state, title, url) => {
      calls.push({ state, title, url });
    },
  };

  setGitUrlQueryParam(" https://github.com/org/repo/tree/main/logs ", { locationLike, historyLike });
  clearGitUrlQueryParam({
    locationLike: {
      href: "https://example.test/eval-dashboard/index.html?git_url=https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Ftree%2Fmain%2Flogs",
    },
    historyLike,
  });

  assert.deepEqual(calls, [
    {
      state: null,
      title: "",
      url: "https://example.test/eval-dashboard/index.html?git_url=https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Ftree%2Fmain%2Flogs",
    },
    {
      state: null,
      title: "",
      url: "https://example.test/eval-dashboard/index.html",
    },
  ]);
});

test("runGitUrlQueryParamBootstrap hydrates the input and triggers the load callback only for non-empty git_url", async () => {
  const inputElement = { value: "" };
  const calls = [];

  const didLoad = await runGitUrlQueryParamBootstrap({
    inputElement,
    locationLike: { search: "?git_url=https%3A%2F%2Fgithub.com%2Forg%2Frepo%2Ftree%2Fmain%2Flogs" },
    onLoadRequested(gitUrl) {
      calls.push(gitUrl);
    },
  });
  const skippedLoad = await runGitUrlQueryParamBootstrap({
    inputElement: { value: "unchanged" },
    locationLike: { search: "?other=1" },
    onLoadRequested() {
      throw new Error("should not be called");
    },
  });

  assert.equal(didLoad, true);
  assert.equal(inputElement.value, "https://github.com/org/repo/tree/main/logs");
  assert.deepEqual(calls, ["https://github.com/org/repo/tree/main/logs"]);
  assert.equal(skippedLoad, false);
});
