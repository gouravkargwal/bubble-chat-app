"""Abstract LLM client interface."""

from abc import ABC, abstractmethod


class LlmClient(ABC):
    @abstractmethod
    async def vision_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        base64_image: str,
        temperature: float,
        model: str,
    ) -> str:
        """Send a vision request and return raw LLM text output."""
        ...
