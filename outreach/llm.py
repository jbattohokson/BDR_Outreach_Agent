"""Model selection lives here so swapping free local models for Claude is one env var.

LLM_MODEL examples:
    ollama/qwen2.5:7b                  free, runs on your machine (default)
    ollama/llama3.1:8b                 free, runs on your machine
    anthropic/claude-sonnet-5-5        paid, needs ANTHROPIC_API_KEY and crewai[anthropic]
    stub                               offline test double, no model at all
"""
from __future__ import annotations

import os

from crewai import LLM, BaseLLM

DEFAULT_MODEL = "ollama/qwen2.5:7b"
DEFAULT_OLLAMA_URL = "http://localhost:11434"


class MissingProviderError(RuntimeError):
    """Raised when the configured model needs a key or package that isn't present."""


def get_llm(stub: BaseLLM | None = None) -> BaseLLM:
    model = os.getenv("LLM_MODEL", DEFAULT_MODEL).strip()
    if model == "stub":
        if stub is None:
            raise MissingProviderError("LLM_MODEL=stub needs a stub LLM passed in (tests only).")
        return stub

    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    if model.startswith("ollama/"):
        # Low temperature keeps small local models from drifting into rewrites.
        return LLM(model=model, base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL),
                   temperature=temperature)

    if model.startswith("anthropic/") and not os.getenv("ANTHROPIC_API_KEY"):
        raise MissingProviderError("Set ANTHROPIC_API_KEY in .env to use a Claude model.")

    try:
        return LLM(model=model, temperature=temperature)
    except ImportError as exc:
        raise MissingProviderError(
            f"{model} needs its provider package. For Claude run: pip install 'crewai[anthropic]'"
        ) from exc
