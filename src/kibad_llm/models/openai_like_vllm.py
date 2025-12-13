from llama_index.llms.openai_like import OpenAILike


class OpenAILikeVllm(OpenAILike):
    """Simple wrapper around OpenAI-like LLMs to indicate vLLM usage in extractors.extract_from_text"""

    pass
