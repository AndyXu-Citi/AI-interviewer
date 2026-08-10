"""
Shared LLM client + model — private module (starts with _), not a route.

Both the interviewer agent, the job-agent, and the data-layer reranker need the
same OpenAI-compatible client. Centralise it here so we only read env once.
"""

import os

from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel


def get_llm_client() -> AsyncOpenAI:
    """Return the OpenAI-compatible async client (EdgeOne AI Gateway / Makers)."""
    return AsyncOpenAI(
        api_key=os.getenv("AI_GATEWAY_API_KEY"),
        base_url=os.getenv("AI_GATEWAY_BASE_URL"),
    )


def get_model() -> OpenAIChatCompletionsModel:
    """Return the chat-completions model wrapper used by the Agents SDK."""
    return OpenAIChatCompletionsModel(
        model=os.getenv("AI_GATEWAY_MODEL", "@makers/deepseek-v4-flash"),
        openai_client=get_llm_client(),
    )
