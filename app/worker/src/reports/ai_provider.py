"""AI provider abstraction for DeepSeek API (MVP — single model).

When AI is disabled or the API key is missing, all calls return a safe
fallback without throwing.  This ensures the recommendation pipeline
never breaks due to AI failures.
"""

from __future__ import annotations

import os
from typing import Any

import requests
from dotenv import load_dotenv

from app.shared.paths import load_config

load_dotenv()


def is_ai_enabled() -> bool:
    """Return True when AI is turned on in config AND an API key is set."""

    config = load_config(overlay_settings=True)
    ai = config.get("ai", {})
    if not ai.get("enabled", False):
        return False

    provider = ai.get("provider", "deepseek")
    key = _get_api_key(provider)
    return key is not None and len(key) > 0


def get_ai_config() -> dict[str, Any]:
    """Return the active AI configuration (provider, model, base_url)."""

    config = load_config(overlay_settings=True)
    ai = config.get("ai", {})
    provider = ai.get("provider", "deepseek")
    return {
        "provider": provider,
        "model": ai.get("model", "deepseek-v4-flash"),
        "api_key": _get_api_key(provider) or "",
        "base_url": _get_base_url(provider),
    }


def chat(prompt: str, system: str = "") -> str | None:
    """Send a single chat completion and return the message text.

    Returns None on any failure — the caller must handle fallback gracefully.
    """

    if not is_ai_enabled():
        return None

    cfg = get_ai_config()
    headers = {
        "Authorization": f"Bearer {cfg['api_key']}",
        "Content-Type": "application/json",
    }
    messages: list[dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body = {
        "model": cfg["model"],
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.3,
    }

    try:
        resp = requests.post(
            f"{cfg['base_url']}/v1/chat/completions",
            headers=headers,
            json=body,
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]
    except Exception:
        return None


def _get_api_key(provider: str) -> str | None:
    """Read API key from environment variables."""

    env_map = {
        "deepseek": "DEEPSEEK_API_KEY",
        "openai": "OPENAI_API_KEY",
        "qwen": "QWEN_API_KEY",
        "zhipu": "ZHIPU_API_KEY",
    }
    key_name = env_map.get(provider, f"{provider.upper()}_API_KEY")
    return os.getenv(key_name)


def _get_base_url(provider: str) -> str:
    """Return the base URL for the provider's chat API."""

    urls = {
        "deepseek": "https://api.deepseek.com",
        "openai": "https://api.openai.com",
    }
    return urls.get(provider, f"https://api.{provider}.com")
