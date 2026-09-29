"""
LLM generation layer.

Sends the messages built by prompts.build_messages() to an LLM via
OpenRouter (an OpenAI-compatible API that gives access to many model
providers through one endpoint) and returns the plain-text answer.

The API key is NEVER hardcoded here -- it must be passed in by the
caller (read from Colab Secrets / an environment variable, not from
this file), so this module has no secrets of its own and is safe to
inspect or share.
"""
from __future__ import annotations

from typing import List

from openai import OpenAI

DEFAULT_MODEL = "openai/gpt-4o-mini"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class Generator:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.model = model
        self._client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
            timeout=60.0,
        )

    def generate(self, messages: List[dict], temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Send chat-style messages to the LLM and return its text reply.
        temperature=0.0 by default -- we want grounded, repeatable answers
        for a RAG system, not creative variation."""
        response = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content
