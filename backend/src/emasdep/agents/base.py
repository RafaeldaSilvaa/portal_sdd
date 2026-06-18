"""Base LLM Agent - supports any OpenAI-compatible API or Ollama (local)."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import httpx

from ..core.types import InferenceAnalytics

logger = logging.getLogger("emasdep.agents")


class LLMProvider(Enum):
    OPENAI_COMPATIBLE = "openai"
    OLLAMA = "ollama"
    GEMINI = "gemini"
    MOCK = "mock"


@dataclass
class LLMConfig:
    provider: LLMProvider = LLMProvider.OPENAI_COMPATIBLE
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o-mini"
    temperature: float = 0.0
    max_tokens: int = 8192
    thinking_mode: bool = False

    @classmethod
    def from_env(cls, env: dict | None = None) -> LLMConfig:
        e = env or {}
        provider_str = e.get("EMASDEP_LLM_PROVIDER", "openai").lower()
        provider_map = {
            "openai": LLMProvider.OPENAI_COMPATIBLE,
            "ollama": LLMProvider.OLLAMA,
            "gemini": LLMProvider.GEMINI,
            "mock": LLMProvider.MOCK,
            "local": LLMProvider.OLLAMA,
        }
        provider = provider_map.get(provider_str, LLMProvider.OPENAI_COMPATIBLE)

        base_url = e.get("EMASDEP_LLM_BASE_URL", "").strip()
        if not base_url:
            if provider == LLMProvider.OLLAMA:
                base_url = "http://localhost:11434"
            elif provider == LLMProvider.GEMINI:
                base_url = "https://generativelanguage.googleapis.com"
            else:
                base_url = "https://api.openai.com/v1"

        return cls(
            provider=provider,
            api_key=e.get("EMASDEP_LLM_API_KEY", ""),
            base_url=base_url,
            model=e.get("EMASDEP_LLM_MODEL", "gpt-4o-mini"),
            temperature=float(e.get("EMASDEP_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(e.get("EMASDEP_LLM_MAX_TOKENS", "8192")),
        )


@dataclass
class LLMResponse:
    content: str
    analytics: InferenceAnalytics | None = None
    provider: str = "mock"


class LLMAgent(ABC):
    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig(provider=LLMProvider.MOCK)

    def _enrich_with_skills(self, system_prompt: str) -> str:
        try:
            from ..skills.registry import SkillRegistry
            skills = SkillRegistry().discover()
            if skills:
                extra = "\n\n## Injected Skills\n" + "\n---\n".join(s.name + "\n" + s.content for s in skills)
                return system_prompt + extra
        except Exception:
            pass
        return system_prompt

    async def call(self, prompt: str, system_prompt: str | None = None) -> LLMResponse:
        if system_prompt:
            system_prompt = self._enrich_with_skills(system_prompt)
        cfg = self.config
        if cfg.provider == LLMProvider.MOCK:
            return self._mock_response(prompt)
        if cfg.provider == LLMProvider.OLLAMA:
            return await self._call_ollama(prompt, system_prompt)
        if cfg.provider == LLMProvider.GEMINI:
            return await self._call_gemini(prompt, system_prompt)
        return await self._call_openai(prompt, system_prompt)

    async def _call_openai(self, prompt: str, system_prompt: str | None) -> LLMResponse:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        headers = {
            "Content-Type": "application/json",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(
                    f"{self.config.base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return LLMResponse(
                    content=content,
                    provider="openai",
                    analytics=InferenceAnalytics(
                        engine_model_resolved=self.config.model,
                        prompt_tokens_total=usage.get("prompt_tokens", 0),
                        prompt_tokens_cache_hits=usage.get("prompt_cache_hit_tokens", 0),
                        completion_reasoning_tokens=usage.get("completion_tokens", 0),
                        latency_duration_ms=0,
                        financial_token_cost_usd=0.0,
                    ),
                )
            except Exception as e:
                logger.warning("OpenAI call failed, falling back to mock: %s", e)
                return self._mock_response(prompt)

    async def _call_ollama(self, prompt: str, system_prompt: str | None) -> LLMResponse:
        payload = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(
                    f"{self.config.base_url.rstrip('/')}/api/generate",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return LLMResponse(
                    content=data.get("response", ""),
                    provider="ollama",
                    analytics=InferenceAnalytics(
                        engine_model_resolved=self.config.model,
                        prompt_tokens_total=data.get("prompt_eval_count", 0),
                        prompt_tokens_cache_hits=0,
                        completion_reasoning_tokens=data.get("eval_count", 0),
                        latency_duration_ms=0,
                        financial_token_cost_usd=0.0,
                    ),
                )
            except Exception as e:
                logger.warning("Ollama call failed, falling back to mock: %s", e)
                return self._mock_response(prompt)

    async def _call_gemini(self, prompt: str, system_prompt: str | None) -> LLMResponse:
        model = self.config.model or "gemini-2.0-flash"
        url = f"{self.config.base_url.rstrip('/')}/v1beta/models/{model}:generateContent"
        payload: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        headers = {"Content-Type": "application/json"}
        params = {"key": self.config.api_key}

        async with httpx.AsyncClient(timeout=300.0) as client:
            try:
                resp = await client.post(url, headers=headers, json=payload, params=params)
                resp.raise_for_status()
                data = resp.json()
                content = data["candidates"][0]["content"]["parts"][0]["text"]
                usage = data.get("usageMetadata", {})
                return LLMResponse(
                    content=content,
                    provider="gemini",
                    analytics=InferenceAnalytics(
                        engine_model_resolved=model,
                        prompt_tokens_total=usage.get("promptTokenCount", 0),
                        prompt_tokens_cache_hits=0,
                        completion_reasoning_tokens=usage.get("candidatesTokenCount", 0),
                        latency_duration_ms=0,
                        financial_token_cost_usd=0.0,
                    ),
                )
            except Exception as e:
                safe_msg = str(e).replace(self.config.api_key, "***") if self.config.api_key else str(e)
                logger.warning("Gemini call failed, falling back to mock: %s", safe_msg)
                return self._mock_response(prompt)

    def _mock_response(self, prompt: str) -> LLMResponse:
        return LLMResponse(
            content=json.dumps({
                "simulated": True,
                "message": f"Simulated response from {self.__class__.__name__}",
            }),
            provider="mock",
            analytics=InferenceAnalytics(
                engine_model_resolved="mock",
                prompt_tokens_total=len(prompt),
                prompt_tokens_cache_hits=len(prompt),
                completion_reasoning_tokens=50,
                latency_duration_ms=0,
                financial_token_cost_usd=0.0,
            ),
        )

    @abstractmethod
    def build_system_prompt(self) -> str:
        ...
