
from abc import ABC, abstractmethod
from typing import Any, Dict
from langchain_openai import ChatOpenAI
from harness.config import get_settings

class BaseAgent(ABC):
    def __init__(self, name: str, model: str | None = None):
        self.name = name
        self.model = model

    def has_model_credentials(self) -> bool:
        settings = get_settings()
        return bool(settings.openai_api_key or settings.minimax_api_key)

    def llm(self, temperature: float = 0.2) -> ChatOpenAI:
        settings = get_settings()
        api_key = settings.openai_api_key or settings.minimax_api_key
        base_url = settings.openai_base_url
        model = self.model or settings.default_model
        if settings.minimax_api_key and not settings.openai_api_key:
            base_url = settings.openai_base_url or settings.minimax_base_url
            model = self.model or settings.minimax_model
        kwargs: dict[str, Any] = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["api_key"] = api_key
        if base_url:
            kwargs["base_url"] = base_url
        return ChatOpenAI(**kwargs)

    @abstractmethod
    async def run(self, context: Dict[str, Any]) -> Dict[str, Any]:
        ...
