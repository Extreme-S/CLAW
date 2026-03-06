"""AI model router — OpenAI + Claude providers with streaming support."""

from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterator


class AIProvider(ABC):
    name: str = ""

    @abstractmethod
    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        """Yield text delta chunks."""
        ...


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = ""):
        import openai
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)
        self.model = model

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=messages,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


class ClaudeProvider(AIProvider):
    name = "claude"

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self.model = model

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        system = ""
        conv = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                conv.append(m)
        kwargs = {"model": self.model, "max_tokens": 2048, "messages": conv}
        if system:
            kwargs["system"] = system
        with self._client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text


class AIRouter:
    """Creates and caches the appropriate AI provider based on config."""

    def __init__(self, config: dict):
        self._config = config.get("ai", {})
        self._provider: AIProvider | None = None

    @property
    def provider(self) -> AIProvider:
        if self._provider is None:
            self._provider = self._create_provider()
        return self._provider

    @property
    def model_name(self) -> str:
        p = self.provider
        return getattr(p, "model", "unknown")

    def _create_provider(self) -> AIProvider:
        ai = self._config
        provider_type = ai.get("provider", "openai")

        if provider_type == "openai":
            key = ai.get("openai_api_key", "")
            if not key:
                raise ValueError("OpenAI API key not configured")
            return OpenAIProvider(
                api_key=key,
                model=ai.get("openai_model", "gpt-4o-mini"),
                base_url=ai.get("openai_base_url", ""),
            )
        elif provider_type == "claude":
            key = ai.get("claude_api_key", "")
            if not key:
                raise ValueError("Claude API key not configured")
            return ClaudeProvider(
                api_key=key,
                model=ai.get("claude_model", "claude-sonnet-4-20250514"),
            )
        else:
            raise ValueError(f"Unknown AI provider: {provider_type}")

    def stream(self, messages: list[dict]) -> Iterator[str]:
        return self.provider.chat_stream(messages)
