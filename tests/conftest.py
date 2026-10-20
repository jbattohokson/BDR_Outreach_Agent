from __future__ import annotations

import os
from collections import deque

import pytest
from crewai import BaseLLM

os.environ["LLM_MODEL"] = "stub"
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")


class ScriptedLLM(BaseLLM):
    """Returns canned replies in order, so crew wiring and retries can be tested without a model."""

    replies: deque = deque()
    prompts: list = []

    def call(self, messages, *args, **kwargs):
        self.prompts.append(messages)
        if not self.replies:
            raise AssertionError("ScriptedLLM ran out of replies; the crew made more calls than expected.")
        return f"Thought: I now can give a great answer\nFinal Answer: {self.replies.popleft()}"


@pytest.fixture
def scripted():
    def make(*replies: str) -> ScriptedLLM:
        llm = ScriptedLLM(model="stub")
        llm.replies = deque(replies)
        llm.prompts = []
        return llm
    return make
