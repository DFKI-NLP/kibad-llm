"""LLM backend implementations for guided-decoding extraction.

Exports three :class:`~kibad_llm.llms.base.LLM` subclasses:

- :class:`~kibad_llm.llms.openai.OpenAI` – OpenAI Responses API with Structured Outputs
  (``json_schema`` strict mode) and optional reasoning summaries.
- :class:`~kibad_llm.llms.openai_like_vllm.OpenAILikeVllm` – OpenAI-compatible HTTP
  interface pointing at a remote vLLM server; passes the JSON schema via
  ``extra_body.structured_outputs``.
- :class:`~kibad_llm.llms.vllm_in_process.VllmInProcess` – loads the model directly
  in the current process using the ``vllm.LLM`` offline engine; suited for SLURM jobs
  with full GPU control.
"""

from .openai import OpenAI
from .openai_like_vllm import OpenAILikeVllm
from .vllm_in_process import VllmInProcess
