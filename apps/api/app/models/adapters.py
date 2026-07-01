from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from openai import OpenAI

from app.shared.config import Settings


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    model_name: str = ""


@runtime_checkable
class ChatModelAdapter(Protocol):
    last_usage: TokenUsage

    def invoke(self, messages: list[dict], **kwargs) -> str:
        ...


class DeepSeekChatAdapter:
    def __init__(self, settings: Settings):
        self._api_key = settings.deepseek_api_key
        self._model = settings.deepseek_model
        self.last_usage = TokenUsage()

    def invoke(self, messages: list[dict], **kwargs) -> str:
        if not self._api_key:
            raise RuntimeError("DeepSeek API key not configured")
        client = OpenAI(api_key=self._api_key, base_url="https://api.deepseek.com")
        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        self._capture_usage(completion)
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("DeepSeek returned no content")
        return content

    def _capture_usage(self, completion) -> None:
        usage = getattr(completion, "usage", None)
        if usage:
            self.last_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                total_tokens=usage.total_tokens or 0,
                model_name=completion.model or self._model,
            )
        else:
            self.last_usage = TokenUsage(model_name=self._model)


class MinimaxChatAdapter:
    def __init__(self, settings: Settings):
        self._api_key = settings.minimax_api_key
        self._base_url = settings.minimax_base_url
        self._model = settings.minimax_model
        self.last_usage = TokenUsage()

    def invoke(self, messages: list[dict], **kwargs) -> str:
        if not self._api_key:
            raise RuntimeError("Minimax API key not configured")
        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        self._capture_usage(completion)
        choice = completion.choices[0]
        content = choice.message.content
        if not content:
            raise RuntimeError("Minimax 返回空内容")
        return content

    def _capture_usage(self, completion) -> None:
        usage = getattr(completion, "usage", None)
        if usage:
            self.last_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                total_tokens=usage.total_tokens or 0,
                model_name=completion.model or self._model,
            )
        else:
            self.last_usage = TokenUsage(model_name=self._model)


class OpenAIChatAdapter:
    def __init__(self, settings: Settings):
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model
        self.last_usage = TokenUsage()

    def invoke(self, messages: list[dict], **kwargs) -> str:
        if not self._api_key:
            raise RuntimeError("OpenAI API key not configured")
        client = OpenAI(api_key=self._api_key)
        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        self._capture_usage(completion)
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned no content")
        return content

    def _capture_usage(self, completion) -> None:
        usage = getattr(completion, "usage", None)
        if usage:
            self.last_usage = TokenUsage(
                prompt_tokens=usage.prompt_tokens or 0,
                completion_tokens=usage.completion_tokens or 0,
                total_tokens=usage.total_tokens or 0,
                model_name=completion.model or self._model,
            )
        else:
            self.last_usage = TokenUsage(model_name=self._model)
