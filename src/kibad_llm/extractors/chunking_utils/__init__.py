"""Chunking utilities: tokenizers and the core chunk-iteration logic.

Re-exports :class:`~kibad_llm.extractors.chunking_utils.tokenizers.RegexTokenizer`
as the default tokenizer used by :class:`~kibad_llm.extractors.chunking.ChunkingExtractor`.
The :mod:`~kibad_llm.extractors.chunking_utils.core` submodule contains
:class:`~kibad_llm.extractors.chunking_utils.core.ChunkIterator` which drives the
actual document splitting.
"""

from .tokenizers import RegexTokenizer
