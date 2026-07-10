"""
Properdocs hook that rewrites GitHub-style repository links to properdocs page URLs.

The READMEs are included via snippets, so their links (e.g. ./models/README.md)
are relative to the GitHub repo root and can't be resolved by properdocs. This
hook fixes them in the rendered HTML, after snippets have been expanded.
"""

import re

# Maps href patterns (GitHub paths) to properdocs page directories
_REWRITES = [
    (re.compile(r'href="/models/README\.md(#[^"]*)?'), "models-readme/", "local"),
    (re.compile(r'href="/podman/faktencheck-db/README\.md(#[^"]*)?'), "podman-readme/", "local"),
    (re.compile(r'href="/data/readme\.md(#[^"]*)?'), "data-readme/", "local"),
    (re.compile(r'href="/docs/USAGE\.md(#[^"]*)?'), "USAGE/", "local"),
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
                pass
            elif location == "github":
                prefix = "https://github.com/DFKI-NLP/kibad-llm/tree/main/"
            else:
                prefix = location
            return f'href="{prefix}{target}{anchor}'

        html = pattern.sub(_repl, html)

    return html
