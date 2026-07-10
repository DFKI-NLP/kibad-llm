"""
Properdocs hook that rewrites GitHub-style repository links to properdocs page URLs.

The READMEs are included via snippets, so their links (e.g. /models/README.md)
are relative to the GitHub repo root and can't be resolved by properdocs. This
hook fixes them in the rendered HTML, after snippets have been expanded.
"""

import re

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
                prefix = "https://github.com/DFKI-NLP/kibad-llm/tree/main/"
            else:
                prefix = location
            return f'href="{prefix}{target}{anchor}'

        html = pattern.sub(_repl, html)

    return html
