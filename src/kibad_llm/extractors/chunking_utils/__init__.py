"""Chunking utilities: tokenizers and the core chunk-iteration logic.

Re-exports [`RegexTokenizer`][kibad_llm.extractors.chunking_utils.tokenizers.RegexTokenizer]
as the default tokenizer used by [`ChunkingExtractor`][kibad_llm.extractors.chunking.ChunkingExtractor].
The [`core`][kibad_llm.extractors.chunking_utils.core] submodule contains
[`ChunkIterator`][kibad_llm.extractors.chunking_utils.core.ChunkIterator] which drives the
actual document splitting.
"""

from .tokenizers import RegexTokenizer
