# Fix schema description ownership and duplicate evidence instructions

Closes #614.

Evidence-enabled prompts repeated field instructions as nested type descriptions.
The formatter now assigns descriptions to fields, types, or enum choices before
rendering, so each source annotation appears once per field occurrence. Distinct
annotations with equal wording and documentation for each use of a shared type are
preserved.

- Separate schema interpretation from text rendering in `schema/description.py`,
    retaining the existing `schema.utils.build_schema_description` import.
- Fix duplication for evidence wrappers, inline objects, and inline enums. Apply
    description visibility and formatting options consistently at every depth.
- Preserve array item, nullable branch, referenced type, and enum documentation;
    combine enum choices across unions/intersections and report unsupported reference
    expansion explicitly.
- Add 45 focused regression cases, remove 51 duplicate lines from 18 description fixtures, and
    document ownership rules and supported schema shapes in `docs/USAGE.md`.

Migration: no import or schema changes are required. Generated prompt text changes
where it previously repeated instructions. `include_field_descriptions=False` now
fully hides field documentation; `choices_description_prefix` applies at every
depth, independently of `choices_prefix`. Unresolved/recursive references,
list-valued types, and multi-branch structural `allOf` now raise `ValueError`.
No dependent PRs.

Validation:

- `uv run --no-sync pytest tests/unit tests/integration/test_evaluation.py -q`: 594 passed.
- Code quality checks, static type checking, and the documentation build passed.
    Link checking reports GitHub 404s for the current unpublished branch.
- The full non-slow Python run has 12 extractor/prediction integration failures:
    changed prompts require new LLM replay recordings. All 12 pass with the original
    formatter. No GPT-OSS-20B backend is listening at the configured local endpoint,
    so recordings have not been regenerated. This PR is not yet CI-ready.

With a reachable GPT-OSS-20B backend configured through `LLM_API_BASE`, regenerate
only the affected integration recordings and expected results, then check fixture usage:

```bash
WRITE_LLM_CHAT_FIXTURE_DATA=1 WRITE_FIXTURE_DATA=1 uv run --group cicd pytest -m "not slow" tests/integration/test_extractors.py tests/integration/test_predict.py
uv run --group cicd python tests/fixtures/map_llm_chat_usage.py
```

To review the formatter independently, run `uv run --no-sync pytest tests/unit/schema -q`.
