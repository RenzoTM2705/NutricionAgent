"""Fixtures comunes para las pruebas."""

from __future__ import annotations

import pytest

from app.config import OllamaSettings


@pytest.fixture
def ollama_settings() -> OllamaSettings:
    return OllamaSettings(
        host="http://localhost:11434",
        model="test:model",
        temperature=0.0,
        num_ctx=4096,
        keep_alive="5m",
        timeout_s=30.0,
    )