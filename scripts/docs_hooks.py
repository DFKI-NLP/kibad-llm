"""
Properdocs hook that rewrites GitHub-style README links to properdocs page URLs.

The READMEs are included via snippets, so their links (e.g. ./models/README.md)
are relative to the GitHub repo root and can't be resolved by properdocs. This
hook fixes them in the rendered HTML, after snippets have been expanded.
"""

import re

# Maps href patterns (GitHub paths) to properdocs page directories
_REWRITES = [
    (re.compile(r'href="\./models/README\.md(#[^"]*)?'), "models-readme/"),
    (re.compile(r'href="\./podman/faktencheck-db/README\.md(#[^"]*)?'), "podman-readme/"),
    (re.compile(r'href="/CONTRIBUTING\.md(#[^"]*)?'), "contributing/"),
]


def on_page_content(html, page, config, files):
    # Number of levels deep the page sits (e.g. 'root-readme/' → 0, 'a/b/' → 1)
    depth = page.url.strip("/").count("/") + 1
    prefix = "../" * depth

    for pattern, target in _REWRITES:

        def _repl(m, prefix=prefix, target=target):
            anchor = m.group(1) or ""
            return f'href="{prefix}{target}{anchor}'

        html = pattern.sub(_repl, html)

    return html
