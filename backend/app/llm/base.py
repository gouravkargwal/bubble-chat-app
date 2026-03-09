"""Abstract LLM client interface."""

from abc import ABC, abstractmethod


class LlmClient(ABC):
    @abstractmethod
    async def vision_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        base64_images: list[str],
        temperature: float,
        model: str,
        max_output_tokens: int = 2000,
    ) -> str:
        """Send a vision request and return raw LLM text output."""
        ...
