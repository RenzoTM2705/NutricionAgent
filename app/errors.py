"""Errores comunes de NutricionAgent.

Por ahora reexporta los errores del cliente Ollama para que el resto
del código no dependa del módulo de transporte.
"""

from __future__ import annotations

from app.ollama_client import (
    OllamaError,
    OllamaHTTPError,
    OllamaNotRunning,
    OllamaResponseError,
)

__all__ = [
    "OllamaError",
    "OllamaHTTPError",
    "OllamaNotRunning",
    "OllamaResponseError",
]