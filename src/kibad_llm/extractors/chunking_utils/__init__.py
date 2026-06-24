"""Tokenization and chunk-iteration utilities for document chunking.

Modules:
    tokenizers: Tokenizer implementations ([`RegexTokenizer`][kibad_llm.extractors.chunking_utils.tokenizers.RegexTokenizer],
        [`UnicodeTokenizer`][kibad_llm.extractors.chunking_utils.tokenizers.UnicodeTokenizer])
        and supporting data types.
    core: [`ChunkIterator`][kibad_llm.extractors.chunking_utils.core.ChunkIterator] and
        [`SentenceIterator`][kibad_llm.extractors.chunking_utils.core.SentenceIterator] for
        splitting tokenized text into bounded chunks.
"""

from .tokenizers import RegexTokenizer
