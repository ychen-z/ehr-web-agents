from typing import Protocol, runtime_checkable

from openai import OpenAI

from app.shared.config import Settings


@runtime_checkable
class ChatModelAdapter(Protocol):
    def invoke(self, messages: list[dict], **kwargs) -> str:
        ...


class DeepSeekChatAdapter:
    def __init__(self, settings: Settings):
        self._api_key = settings.deepseek_api_key
        self._model = settings.deepseek_model

    def invoke(self, messages: list[dict], **kwargs) -> str:
        if not self._api_key:
            raise RuntimeError("DeepSeek API key not configured")
        client = OpenAI(api_key=self._api_key, base_url="https://api.deepseek.com")
        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("DeepSeek returned no content")
        return content


class MinimaxChatAdapter:
    def __init__(self, settings: Settings):
        self._api_key = settings.minimax_api_key
        self._base_url = settings.minimax_base_url
        self._model = settings.minimax_model

    def invoke(self, messages: list[dict], **kwargs) -> str:
        if not self._api_key:
            raise RuntimeError("Minimax API key not configured")
        client = OpenAI(api_key=self._api_key, base_url=self._base_url)
        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("Minimax returned no content")
        return content


class OpenAIChatAdapter:
    def __init__(self, settings: Settings):
        self._api_key = settings.openai_api_key
        self._model = settings.openai_model

    def invoke(self, messages: list[dict], **kwargs) -> str:
        if not self._api_key:
            raise RuntimeError("OpenAI API key not configured")
        client = OpenAI(api_key=self._api_key)
        completion = client.chat.completions.create(
            model=self._model,
            messages=messages,
        )
        content = completion.choices[0].message.content
        if not content:
            raise RuntimeError("OpenAI returned no content")
        return content
