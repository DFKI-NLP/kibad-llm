from typing import Any

from llama_index.core.base.llms.types import MessageRole

from kibad_llm.llms.base import SimpleChatMessage

from .base import extract_from_text_lenient
from .union import UnionExtractor, _aggregate_structured_outputs_union


class ChunkingExtractor(UnionExtractor):
    """Extractor that chunks extraction and aggregates results per key.
    This extractor calls the base extraction function multiple times
    (for each chunk in the document) on the same input text, 
    passing some previous context to each subsequent call.

    TODO: adapt ->
    See UnionExtractor for accepted parameters and details about the aggregation logic.
    """

    def __call__(self, *args, **kwargs) -> dict[str, Any]:
        combined_kwargs = {**self.default_kwargs, **kwargs}
        breakpoint()
        current_kwargs = {
            **combined_kwargs,
            "return_messages_formatted": True,
            "truncate_user_message_formatted": None,
        }       
        # text: The document text to process.
        # text_id: Document text identifier for logging.
        # prompt_template: A dictionary with at least one of 'system_message' and 'user_message'
        #     templates (or both).
        # schema: Optional JSON schema for structured output.
        # use_guided_decoding: Whether to use guided decoding.
        # validate_with_schema: Whether to validate the output against the provided schema.
        #     IMPORTANT: Disabling validation may lead to invalid structured outputs and, thus,
        #     may break result serialization (since we use .map() and .to_json() from datasets).
        # llm: The LLM model to use. Must be a chat model (i.e. is_chat_model=True) and support extra_body
        #     parameters for guided decoding if schema is provided. If None, no LLM call is made.
        # request_parameters: Additional parameters to pass to the LLM chat call. If 'seed' is not provided,
        #     a seed is derived from the messages and added to request_parameters for determinism.
        # return_reasoning: Whether to return the reasoning done by the model.
        # **build_messages_kwargs: Additional keyword arguments for build_chat_messages.
        current_result = extract_from_text_lenient(*args, **current_kwargs)



        # results = []
        # history: list[SimpleChatMessage] = []
        # for override_params in self.overrides:
        #     # adjust kwargs:
        #     # 1) to return formatted messages for history
        #     current_kwargs = {
        #         **combined_kwargs,
        #         **override_params,
        #         "return_messages_formatted": True,
        #         "truncate_user_message_formatted": None,
        #     }
        #     # 2) if history exists, pass it and disable system message
        #     if len(history) > 0:
        #         current_kwargs["prompt_template"]["system_message"] = None
        #         current_kwargs["history"] = history
        #
        #     current_result = extract_from_text_lenient(*args, **current_kwargs)
        #
        #     # collect messages for history
        #     for role_str, content in current_result["messages_formatted"].items():
        #         role = MessageRole(role_str)
        #         history.append(SimpleChatMessage(role=role, content=content))
        #     # append assistant response or error to history
        #     history.append(
        #         SimpleChatMessage(
        #             role=MessageRole.ASSISTANT,
        #             content=current_result["response_content"] or current_result["error"],
        #         )
        #     )
        #
        #     results.append(current_result)
        #
        # structured_outputs = [v.get("structured", None) for v in results]
        # aggregated_structured = _aggregate_structured_outputs_union(
        #     structured_outputs, skip_type_mismatches=self.skip_type_mismatches
        # )
        #
        # result: dict[str, Any] = {
        #     "structured": aggregated_structured,
        # }
        # for field in self.return_as_list:
        #     result[f"{field}_list"] = [v.get(field, None) for v in results]
        # return result
