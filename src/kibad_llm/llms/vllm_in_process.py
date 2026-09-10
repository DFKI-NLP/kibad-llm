import contextlib
import gc
import logging
from typing import Any

from llama_index.core.base.llms.types import ChatResponse, MessageRole
from llama_index.core.llms import ChatMessage as LlamaIndexChatMessage
import torch
from vllm import LLM as VllmLLM
from vllm import SamplingParams
from vllm.distributed import destroy_distributed_environment, destroy_model_parallel
from vllm.entrypoints.chat_utils import (
    ChatCompletionMessageParam,
    CustomChatCompletionMessageParam,
)
from vllm.entrypoints.harmony_utils import parse_chat_output
from vllm.entrypoints.openai.protocol import ChatCompletionRequest
from vllm.reasoning import ReasoningParser
from vllm.reasoning.gptoss_reasoning_parser import GptOssReasoningParser
from vllm.sampling_params import StructuredOutputsParams
from vllm.v1.structured_output import StructuredOutputManager

from kibad_llm.llms.base import (
    LLM,
    EmptyReasoningError,
    ReasoningExtractionError,
    SimpleChatMessage,
)

logger = logging.getLogger(__name__)


def cleanup():
    destroy_model_parallel()
    destroy_distributed_environment()
    with contextlib.suppress(AssertionError):
        torch.distributed.destroy_process_group()
    gc.collect()
    torch.cuda.empty_cache()


# vLLM LLM.chat has these kwargs (non-sampling). Everything else we treat as SamplingParams kwargs.
# Source: https://docs.vllm.ai/en/stable/api/vllm/entrypoints/llm/#vllm.entrypoints.llm.LLM.chat
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
    msg: CustomChatCompletionMessageParam = {"role": m.role.value, "content": m.content}
    return msg


class VllmInProcess(LLM):
    """
    In-process vLLM backend using vllm.LLM.chat() so the model's chat template
    is applied automatically.

    Supports guided decoding via StructuredOutputsParams(json=...).

    In offline mode, vLLM does not automatically split reasoning vs final content
    for you; we do it here using the configured ReasoningParser (and a Harmony fallback).
    """

    def __init__(
        self,
        *,
        model: str,
        vllm_kwargs: dict[str, Any] | None = None,
        lazy: bool = True,
        # for compatibility with other LlamaIndex LLMs (but directly supported kwargs take precedence)
        additional_kwargs: dict[str, Any] | None = None,
        **default_request_kwargs: Any,
    ) -> None:
        self._model_name = model
        self._vllm_kwargs = vllm_kwargs or {}
        if "enable_sleep_mode" not in self._vllm_kwargs:
            # enable sleep mode by default to allow calling llm.sleep() to free up GPU memory
            self._vllm_kwargs["enable_sleep_mode"] = True
        if not lazy:
            # trigger vLLM initialization now (instead of waiting for first call)
            # so that any errors are raised during LLM setup instead of at call time
            _ = self.llm
            _ = self.reasoning_parser

        self._default_request_kwargs: dict[str, Any] = additional_kwargs or {}
        self._default_request_kwargs.update(default_request_kwargs)

    @property
    def llm(self) -> VllmLLM:
        if not hasattr(self, "_llm"):
            self._llm = VllmLLM(model=self._model_name, **self._vllm_kwargs)

        return self._llm

    @property
    def reasoning_parser(self) -> ReasoningParser | None:
        if not hasattr(self, "_reasoning_parser"):
            # Uses vllm_config.structured_outputs_config.reasoning_parser
            # to create a ReasoningParser (if configured).
            structured_output_manager = StructuredOutputManager(
                vllm_config=self.llm.llm_engine.vllm_config
            )
            self._reasoning_parser: ReasoningParser | None = structured_output_manager.reasoner
            if self._reasoning_parser is not None:
                logger.info(
                    f"Using reasoning parser: {type(self._reasoning_parser).__name__} "
                    f"for model {self._model_name} to separate reasoning from final content."
                )
            else:
                logger.info(
                    f"No reasoning parser configured for model {self._model_name}. "
                    f"Assuming no reasoning content in outputs."
                )

        return self._reasoning_parser

    def destroy(self) -> None:
        """Clean up vLLM resources."""
        if hasattr(self, "_llm"):
            del self._llm
        if hasattr(self, "_reasoning_parser"):
            del self._reasoning_parser
        cleanup()

    def __del__(self):
        self.destroy()

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[SimpleChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs: Any,
    ) -> ChatResponse:
        convo = [_chat_message_to_vllm_param(m) for m in messages]

        sampling_kwargs = {**self._default_request_kwargs, **request_kwargs}

        # pull out vLLM chat() kwargs; everything else goes into SamplingParams
        chat_kwargs: dict[str, Any] = {"use_tqdm": False}
        for k in list(sampling_kwargs.keys()):
            if k in _VLLM_CHAT_KWARGS:
                chat_kwargs[k] = sampling_kwargs.pop(k)

        if json_schema is not None:
            sampling_kwargs["structured_outputs"] = StructuredOutputsParams(json=json_schema)

        sampling_params = SamplingParams(**sampling_kwargs)
        req_outputs = self.llm.chat(convo, sampling_params=sampling_params, **chat_kwargs)
        # take the first output (we only sent one conversation) and first generation
        out = req_outputs[0].outputs[0]

        if self.reasoning_parser is not None:
            if isinstance(self.reasoning_parser, GptOssReasoningParser):
                # Harmony (gpt-oss): split via token ids
                reasoning, content, _is_tool_call = parse_chat_output(out.token_ids)
            else:
                # create dummy request object for reasoning extraction
                request_obj = ChatCompletionRequest(messages=convo, model=self._model_name, seed=0)
                reasoning, content = self.reasoning_parser.extract_reasoning(
                    model_output=out.text, request=request_obj
                )
        else:
            reasoning = None
            content = out.text

        msg = LlamaIndexChatMessage(role=MessageRole.ASSISTANT, content=content)
        if reasoning is not None:
            msg.additional_kwargs["reasoning"] = reasoning

        return ChatResponse(message=msg, raw=req_outputs)

    def get_reasoning_from_chat_response(self, response: ChatResponse) -> str | None:
        """Extract reasoning from a chat response."""

        # don't attempt extraction if no reasoning parser configured (and thus don't raise errors)
        if self.reasoning_parser is None:
            return None

        reasoning = response.message.additional_kwargs.get("reasoning")
        if not isinstance(reasoning, str):
            raise ReasoningExtractionError("Could not extract reasoning from chat response.")
        if not reasoning.strip():
            raise EmptyReasoningError("Extracted reasoning is empty.")
        return reasoning
