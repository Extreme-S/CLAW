from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict, Iterator, Optional
from PyQt6.QtCore import QThread, pyqtSignal


class AIProvider(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict]) -> str:
        ...

    @abstractmethod
    def chat_stream(self, messages: List[Dict]) -> Iterator[str]:
        """Yield partial text chunks."""
        ...


class OpenAIProvider(AIProvider):
    def __init__(self, api_key: str, model: str = "gpt-4o-mini", base_url: str = ""):
        import openai
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)
        self._model = model

    def chat(self, messages: list[dict]) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        return resp.choices[0].message.content

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        stream = self._client.chat.completions.create(
            model=self._model,
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
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def chat(self, messages: list[dict]) -> str:
        system, conv = self._split_system(messages)
        kwargs = {"model": self._model, "max_tokens": 1024, "messages": conv}
        if system:
            kwargs["system"] = system
        resp = self._client.messages.create(**kwargs)
        return resp.content[0].text

    def chat_stream(self, messages: list[dict]) -> Iterator[str]:
        system, conv = self._split_system(messages)
        kwargs = {"model": self._model, "max_tokens": 1024, "messages": conv}
        if system:
            kwargs["system"] = system
        with self._client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def _split_system(self, messages):
        system = ""
        conv = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            else:
                conv.append(m)
        return system, conv


class ChatWorker(QThread):
    """流式输出：逐块发送文字到 UI。"""
    chunk_received = pyqtSignal(str)   # 每收到一小段文字
    finished = pyqtSignal(str)          # 完整回复
    error = pyqtSignal(str)

    def __init__(self, provider: AIProvider, messages: list[dict]):
        super().__init__()
        self._provider = provider
        self._messages = messages

    def run(self):
        try:
            full_text = ""
            for chunk in self._provider.chat_stream(self._messages):
                full_text += chunk
                self.chunk_received.emit(full_text)
            self.finished.emit(full_text)
        except Exception as e:
            self.error.emit(str(e))


def create_provider(config) -> AIProvider | None:
    provider_type = config.get("ai", "provider")
    if provider_type == "openai":
        key = config.get("ai", "openai_api_key")
        if not key:
            return None
        return OpenAIProvider(
            api_key=key,
            model=config.get("ai", "openai_model") or "gpt-4o-mini",
            base_url=config.get("ai", "openai_base_url") or "",
        )
    elif provider_type == "claude":
        key = config.get("ai", "claude_api_key")
        if not key:
            return None
        return ClaudeProvider(
            api_key=key,
            model=config.get("ai", "claude_model") or "claude-sonnet-4-20250514",
        )
    return None
