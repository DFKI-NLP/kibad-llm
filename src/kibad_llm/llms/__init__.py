"""LLM provider integrations behind a common project-internal LLM interface.

All wrappers subclass [`LLM`][kibad_llm.llms.base.LLM], which is the interface used by
[`extract_from_text`][kibad_llm.extractors.base.extract_from_text].

Modules:
    base: Base class [`LLM`][kibad_llm.llms.base.LLM] defining the project internal LLM API,
        plus [`SimpleChatMessage`][kibad_llm.llms.base.SimpleChatMessage] and related errors.
    openai: [`OpenAI`][kibad_llm.llms.openai.OpenAI] wrapper for OpenAI endpoints using the
        Responses API with Structured Outputs and optional reasoning summaries.
    openai_like_vllm: [`OpenAILikeVllm`][kibad_llm.llms.openai_like_vllm.OpenAILikeVllm]
        wrapper for OpenAI-compatible servers backed by vLLM.
    vllm_in_process: [`VllmInProcess`][kibad_llm.llms.vllm_in_process.VllmInProcess] wrapper
        for vLLM models running in the current process.

Classes:
    OpenAI: OpenAI wrapper that supports Structured Outputs + (optional) reasoning summaries via Responses API.
    OpenAILikeVllm: Wrapper around OpenAI-like LLMs served by vLLM, with guided decoding.
    VllmInProcess: Wrapper around vLLM models running in this process.
"""

from .openai import OpenAI
from .openai_like_vllm import OpenAILikeVllm
from .vllm_in_process import VllmInProcess
