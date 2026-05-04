"""Extractor classes and core extraction functions for the prediction pipeline.

Extractors are callables that receive ``(text, file_name)`` and return a dict
containing at least a ``structured`` field with the LLM-extracted JSON output.
They differ in *how many times* and *on what text spans* the underlying
[`extract_from_text`][kibad_llm.extractors.base.extract_from_text] function is called, and how
the resulting partial outputs are aggregated:

- [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] – slides a window over
  the document and aggregates per-chunk results.
- [`RepeatingExtractor`][kibad_llm.extractors.repeat.RepeatingExtractor] – runs extraction *n*
  times on the full text and aggregates via majority vote (reduces LLM variability).
- [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] – runs extraction once per
  entry in ``overrides``, each with different parameters, and aggregates results.
- [`ConditionalUnionExtractor`][kibad_llm.extractors.conditional.ConditionalUnionExtractor] – like
  ``UnionExtractor`` but feeds each run's output back as conversation history to the
  next run (multi-turn extraction).
"""

from .base import extract_from_text, extract_from_text_lenient
from .chunking import ChunkingExtractor
from .conditional import ConditionalUnionExtractor
from .repeat import RepeatingExtractor
from .union import UnionExtractor
