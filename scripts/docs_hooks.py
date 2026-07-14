"""
Properdocs hook that rewrites GitHub-style repository links to properdocs page URLs.

The READMEs are included via snippets, so their links (e.g. /models/README.md)
are relative to the GitHub repo root and can't be resolved by properdocs. This
hook fixes them in the rendered HTML, after snippets have been expanded.
"""

import os
import re

import git


def _get_git_branch_name(repo: git.Repo) -> str:
    """Return the current branch name without crashing on detached HEAD checkouts.

    Args:
        repo: Repo object to perform check on (this one).

    Returns:
        Name of the current branch, or ref or name of the currently checked out commit, or "detached".
    """
    if repo.head.is_detached:
        return os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME") or "detached"

    try:
        return repo.active_branch.name
    except TypeError:
        return os.getenv("GITHUB_HEAD_REF") or os.getenv("GITHUB_REF_NAME") or "detached"


try:
    GIT_BRANCH_NAME: str = _get_git_branch_name(git.Repo(search_parent_directories=True)).replace(
        " ", "-"
    )
except (git.InvalidGitRepositoryError, git.GitCommandError):
    # This fallback will most probably be wrong, but the safest bet.
    GIT_BRANCH_NAME: str = "main"

# Maps href patterns (GitHub paths) to properdocs page directories
_REWRITES = [
    # fix links of specific files
    (re.compile(r'href="/models/README\.md(#[^"]*)?'), "models-readme/", "local"),
    (re.compile(r'href="/podman/faktencheck-db/README\.md(#[^"]*)?'), "podman-readme/", "local"),
    (re.compile(r'href="/data/readme\.md(#[^"]*)?'), "data-readme/", "local"),
    # fix links from the rest of the repo into docs
    (re.compile(r'href="/docs/([^"]*)?\.md'), "", "local"),
    # fix links for inside docs into the rest of the repo
    # !IMPORTANT! THIS NEEDS TO COME LAST. IT PICKS UP WHAT THE OTHER REGEXES DIDN'T!
    (re.compile(r'href="/([^"]*)?'), "", "github"),
]


def on_page_content(html, page, config, files):
    # Number of levels deep the page sits (e.g. 'models-readme/' → 0, 'a/b/' → 1)
    depth = page.url.strip("/").count("/") + 1
    prefix = "../" * depth

    for pattern, target, location in _REWRITES:

        def _repl(m, prefix=prefix, target=target, location=location):
            anchor = m.group(1) or ""
            if location == "local":
                # "local" paths go from the docs to the docs and don't need more fixing
                pass
            elif location == "github":
                # "github" paths go from the docs to the github repo and thus need the github link prepended
                prefix = f"https://github.com/DFKI-NLP/kibad-llm/tree/{GIT_BRANCH_NAME}/"
            else:
                prefix = location
            return f'href="{prefix}{target}{anchor}'

        html = pattern.sub(_repl, html)

    return html
