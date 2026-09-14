"""Extractors for structured information extraction from text using LLMs.

Modules:
    base: Core extraction function [`extract_from_text`][kibad_llm.extractors.base.extract_from_text]
        and related types.
    aggregation_utils: Aggregation functions for combining structured outputs across
        multiple extractions.
    chunking: [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor] for
        running extraction over document chunks.
    chunking_utils: Tokenization and chunk-iteration utilities used by
        [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor].
    conditional: [`ConditionalUnionExtractor`][kibad_llm.extractors.conditional.ConditionalUnionExtractor]
        for multi-pass extraction with chat history.
    repeat: [`RepeatingExtractor`][kibad_llm.extractors.repeat.RepeatingExtractor] for
        repeated extraction with majority-vote aggregation.
    union: [`UnionExtractor`][kibad_llm.extractors.union.UnionExtractor] for multi-pass
        extraction with per-pass parameter overrides.
"""

from .base import extract_from_text, extract_from_text_lenient
from .chunking import ChunkingExtractor
from .conditional import ConditionalUnionExtractor
from .conditional_chunking import ConditionalUnionChunkingExtractor
from .repeat import RepeatingExtractor
from .union import UnionExtractor
