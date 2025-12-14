from __future__ import annotations

from typing import Any

from llama_index.core.base.llms.types import (
    ChatResponse,
    MessageRole,
)
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
from vllm import LLM as VllmLLM
from vllm import SamplingParams
from vllm.entrypoints.chat_utils import (
    ChatCompletionMessageParam,
    CustomChatCompletionMessageParam,
)
from vllm.entrypoints.harmony_utils import parse_chat_output
from vllm.sampling_params import StructuredOutputsParams

from kibad_llm.llms.base import LLM, SimpleChatMessage

# vLLM LLM.chat has these kwargs (non-sampling). Everything else we treat as SamplingParams kwargs.
_VLLM_CHAT_KWARGS = {
    "use_tqdm",
    "lora_request",
    "chat_template",
    "chat_template_content_format",
    "add_generation_prompt",
    "continue_final_message",
    "tools",
    "chat_template_kwargs",
    "mm_processor_kwargs",
}


def _chat_message_to_vllm_param(m: SimpleChatMessage) -> ChatCompletionMessageParam:
    role_any = getattr(m.role, "value", m.role)
    role = str(role_any)
    msg: CustomChatCompletionMessageParam = {"role": role, "content": m.content}
    return msg


class VllmInProcess(LLM):
    """
    In-process vLLM backend using vllm.LLM.chat() so the model's chat template
    is applied automatically.

    Supports guided decoding via StructuredOutputsParams(json=...).
    Splits Harmony reasoning/final via vLLM's parse_chat_output(token_ids).
    """

    def __init__(
        self,
        *,
        model: str,
        vllm_kwargs: dict[str, Any] | None = None,
        # default sampling
        temperature: float = 0.0,
        top_p: float = 1.0,
        max_tokens: int = 4096,
        # optional defaults for chat templating
        chat_template_kwargs: dict[str, Any] | None = None,
        add_generation_prompt: bool = True,
        **extra_default_sampling_kwargs: Any,
    ) -> None:

        self._llm = VllmLLM(model=model, **(vllm_kwargs or {}))
        self._default_sampling: dict[str, Any] = {
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": max_tokens,
            **extra_default_sampling_kwargs,
        }
        self._default_chat_kwargs: dict[str, Any] = {
            "chat_template_kwargs": chat_template_kwargs,
            "add_generation_prompt": add_generation_prompt,
            "use_tqdm": False,
        }

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs: Any,
    ) -> ChatResponse:

        # Convert simple messages -> vLLM chat messages format
        # Each message is a dict with role + content.
        convo = [_chat_message_to_vllm_param(m) for m in messages]

        # Split kwargs into (a) SamplingParams kwargs and (b) vLLM chat() kwargs
        sampling_kwargs = dict(self._default_sampling)
        sampling_kwargs.update(request_kwargs)

        # alias: some callers use max_new_tokens
        if "max_new_tokens" in sampling_kwargs and "max_tokens" not in sampling_kwargs:
            sampling_kwargs["max_tokens"] = sampling_kwargs.pop("max_new_tokens")

        chat_kwargs = dict(self._default_chat_kwargs)
        for k in list(sampling_kwargs.keys()):
            if k in _VLLM_CHAT_KWARGS:
                chat_kwargs[k] = sampling_kwargs.pop(k)

        # Guided decoding via structured_outputs in SamplingParams.
        if json_schema is not None:
            sampling_kwargs["structured_outputs"] = StructuredOutputsParams(json=json_schema)

        sampling_params = SamplingParams(**sampling_kwargs)

        # vLLM returns list[RequestOutput] in the same order as inputs.
        req_out = self._llm.chat(convo, sampling_params=sampling_params, **chat_kwargs)[0]
        comp_out = req_out.outputs[0]  # CompletionOutput: .text, .token_ids

        # Split Harmony into reasoning + final (final is what you want to JSON-parse).
        reasoning, final, _is_tool_call = parse_chat_output(comp_out.token_ids)
        content = final if final is not None else comp_out.text

        msg = LlamaIndexChatMessage(role=MessageRole.ASSISTANT, content=content)

        additional_kwargs: dict[str, Any] = {}
        if reasoning is not None:
            additional_kwargs["reasoning"] = reasoning
            msg.additional_kwargs["reasoning"] = reasoning

        return ChatResponse(message=msg, raw=req_out, additional_kwargs=additional_kwargs)
