"""Config API routes for LLM settings."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter

router = APIRouter()


def _get_env() -> dict[str, str]:
    """ get env.

Retorna:
    Descrição do valor retornado."""
    return {
        "EMASDEP_LLM_PROVIDER": os.environ.get("EMASDEP_LLM_PROVIDER", "ollama"),
        "EMASDEP_LLM_MODEL": os.environ.get("EMASDEP_LLM_MODEL", "llama3.2:1b"),
        "EMASDEP_LLM_BASE_URL": os.environ.get("EMASDEP_LLM_BASE_URL", "http://127.0.0.1:11434"),
        "EMASDEP_LLM_TEMPERATURE": os.environ.get("EMASDEP_LLM_TEMPERATURE", "0.0"),
        "EMASDEP_LLM_MAX_TOKENS": os.environ.get("EMASDEP_LLM_MAX_TOKENS", "8192"),
        "EMASDEP_ENV": os.environ.get("EMASDEP_ENV", "development"),
    }


def _mask_key(key: str) -> str:
    """ mask key.

Args:
    key: Descrição do parâmetro key.

Retorna:
    Descrição do valor retornado."""
    if len(key) <= 8:
        return key
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@router.get("/api/config/ollama-models")
async def list_ollama_models():
    """list ollama models.

Retorna:
    None"""
    import httpx
    base = os.environ.get("EMASDEP_LLM_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{base}/api/tags")
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        return {"models": [], "error": str(e)}


@router.get("/api/config")
async def get_config():
    """get config.

Retorna:
    None"""
    env = _get_env()
    raw_key = os.environ.get("EMASDEP_LLM_API_KEY", "")
    env["EMASDEP_LLM_API_KEY"] = _mask_key(raw_key) if raw_key else ""
    return env


@router.post("/api/config/test")
async def test_config(body: dict[str, Any]):
    """test config.

Args:
    body: Descrição do parâmetro body.

Retorna:
    None"""
    import httpx
    provider = body.get("EMASDEP_LLM_PROVIDER", os.environ.get("EMASDEP_LLM_PROVIDER", "ollama"))
    base_url = body.get("EMASDEP_LLM_BASE_URL", os.environ.get("EMASDEP_LLM_BASE_URL", ""))
    api_key = body.get("EMASDEP_LLM_API_KEY", os.environ.get("EMASDEP_LLM_API_KEY", ""))
    model = body.get("EMASDEP_LLM_MODEL", os.environ.get("EMASDEP_LLM_MODEL", ""))

    if provider == "mock":
        return {"status": "ok", "message": "Mock provider — always available"}

    if not base_url:
        if provider == "ollama":
            base_url = "http://127.0.0.1:11434"
        elif provider == "gemini":
            base_url = "https://generativelanguage.googleapis.com"
        else:
            base_url = "https://api.openai.com/v1"
    base_url = base_url.rstrip("/")

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            if provider == "ollama":
                resp = await client.get(f"{base_url}/api/tags")
                resp.raise_for_status()
                models = resp.json().get("models", [])
                model_name = model or "llama3.2:1b"
                model_found = any(m["name"] == model_name or m["name"] == f"{model_name}:latest" for m in models)
                if not model_found:
                    names = [m["name"] for m in models]
                    return {"status": "ok", "message": f"Ollama reachable, but model '{model_name}' not found. Available: {', '.join(names) or 'none'}"}
                chat_resp = await client.post(
                    f"{base_url}/api/chat",
                    json={"model": model_name, "messages": [{"role": "user", "content": "Say hello in one word"}], "stream": False},
                )
                chat_resp.raise_for_status()
                reply = chat_resp.json().get("message", {}).get("content", "")
                return {"status": "ok", "message": f"Model '{model_name}' responded: {reply[:100]}"}
            elif provider == "gemini":
                model_name = model or "gemini-2.0-flash"
                params = {"key": api_key} if api_key else {}
                chat_body = {
                    "contents": [{"role": "user", "parts": [{"text": "Say hello in one word"}]}],
                }
                resp = await client.post(
                    f"{base_url}/v1beta/models/{model_name}:generateContent",
                    params=params,
                    json=chat_body,
                )
                resp.raise_for_status()
                reply = resp.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return {"status": "ok", "message": f"Gemini responded: {reply[:100]}"}
            else:
                headers = {"Content-Type": "application/json"}
                if api_key:
                    headers["Authorization"] = f"Bearer {api_key}"
                chat_body = {
                    "model": model or "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Say hello in one word"}],
                    "max_tokens": 20,
                }
                resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=chat_body)
                resp.raise_for_status()
                reply = resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                return {"status": "ok", "message": f"Model responded: {reply[:100]}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@router.put("/api/config")
async def update_config(body: dict[str, Any]):
    """update config.

Args:
    body: Descrição do parâmetro body.

Retorna:
    None"""
    allowed_keys = {
        "EMASDEP_LLM_PROVIDER",
        "EMASDEP_LLM_MODEL",
        "EMASDEP_LLM_BASE_URL",
        "EMASDEP_LLM_API_KEY",
        "EMASDEP_LLM_TEMPERATURE",
        "EMASDEP_LLM_MAX_TOKENS",
    }
    for key, value in body.items():
        if key in allowed_keys:
            os.environ[key] = str(value)
    return _get_env()
