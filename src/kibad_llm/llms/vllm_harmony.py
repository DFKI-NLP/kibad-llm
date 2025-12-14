import re
from typing import Any

from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.llms.vllm import Vllm as LlamaIndexVllm
from vllm.sampling_params import StructuredOutputsParams

from kibad_llm.llms.base import LLM
from kibad_llm.utils.log import warn_once

_ANALYSIS_RE = re.compile(r"<\|channel\|>analysis<\|message\|>(.*?)<\|end\|>", re.S)
_FINAL_RE = re.compile(
    r"<\|channel\|>final<\|message\|>(.*?)(?:<\|return\|>|<\|end\|>)",
    re.S,
)


def split_harmony(text: str) -> tuple[str, str | None]:
    # collect all analysis blocks (sometimes there can be multiple)
    analyses = [m.strip() for m in _ANALYSIS_RE.findall(text)]
    reasoning = "\n".join([a for a in analyses if a]) or None

    m = _FINAL_RE.search(text)
    if m:
        final = m.group(1).strip()
        return final, reasoning

    # fallback: no recognizable final marker -> treat whole thing as content
    return text.strip(), reasoning


class VllmWithHarmonyParsing(LLM):

    def __init__(self, *args, **kwargs) -> None:
        self.model = LlamaIndexVllm(*args, **kwargs)

    def call_llm_chat_with_guided_decoding(
        self,
        messages: list[ChatMessage],
        *,
        json_schema: dict[str, Any] | None = None,
        **request_kwargs,
    ) -> ChatResponse:
        if json_schema is not None:

            # vllm hosted models require json schema guided decoding via structured_outputs of type StructuredOutputParams
            if "structured_outputs" in request_kwargs:
                warn_once(
                    f'Overwriting existing "structured_outputs": {request_kwargs["structured_outputs"]} '
                    "in request_parameters with provided json schema for guided decoding."
                )
            request_kwargs["structured_outputs"] = StructuredOutputsParams(json=json_schema)

        response = self.model.chat(messages, **request_kwargs)

        content = self.get_response_content_from_chat_response(response)

        final, reasoning = split_harmony(content)

        # normalize
        response.message.content = final
        if reasoning is not None:
            response.additional_kwargs["reasoning"] = reasoning

        return response
