from __future__ import annotations

import httpx
from typing import Any
from ..config import settings


class LLMClient:
  """Minimal LLM client supporting ollama and openai via HTTP."""

  def __init__(self) -> None:
    self.provider = settings.llm_provider.lower()

  async def generate(self, prompt: str, temperature: float = 0.2, max_tokens: int | None = None) -> str:
    if self.provider == "ollama":
      return await self._generate_ollama(prompt, temperature)
    if self.provider == "openai":
      return await self._generate_openai(prompt, temperature, max_tokens)
    raise ValueError(f"Unsupported LLM provider: {self.provider}")

  async def _generate_ollama(self, prompt: str, temperature: float) -> str:
    url = f"{settings.ollama_base_url}/api/chat"
    payload = {
      "model": settings.ollama_model,
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
      ],
      "options": {"temperature": temperature},
      "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
      resp = await client.post(url, json=payload)
      resp.raise_for_status()
      data: dict[str, Any] = resp.json()
      # ollama chat returns { message: { content } }
      message = data.get("message", {})
      content = message.get("content", "")
      return content.strip()

  async def _generate_openai(self, prompt: str, temperature: float, max_tokens: int | None) -> str:
    url = f"{settings.openai_base_url}/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    payload = {
      "model": settings.openai_model,
      "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
      ],
      "temperature": temperature,
    }
    if max_tokens is not None:
      payload["max_tokens"] = max_tokens
    async with httpx.AsyncClient(timeout=120) as client:
      resp = await client.post(url, headers=headers, json=payload)
      resp.raise_for_status()
      data = resp.json()
      content = data["choices"][0]["message"]["content"]
      return content.strip()

