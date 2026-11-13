"""Pruebas de app/setup/checks.py con mocks."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.ollama_client import OllamaError, OllamaModel
from app.setup.checks import (
    EstadoOllama,
    estado_ollama,
    mensaje_modelo_no_disponible,
    mensaje_si_no_disponible,
    mensaje_si_sin_modelos,
    probar_modelo,
)


def _client_mock(ping=True, version="0.40.16", modelos=None, has=True) -> MagicMock:
    c = MagicMock()
    c.ping.return_value = ping
    c.version.return_value = version
    c.list_models.return_value = [
        OllamaModel(name=m, size=0, digest="", modified_at="") for m in (modelos or [])
    ]
    c.has_model.return_value = has
    return c


def test_estado_disponible_con_modelo():
    c = _client_mock(modelos=["qwen3:4b"], has=True)
    e = estado_ollama(c, modelo_configurado="qwen3:4b")
    assert e.disponible is True
    assert e.version == "0.40.16"
    assert e.modelos == ["qwen3:4b"]
    assert e.modelo_configurado == "qwen3:4b"
    assert e.modelo_disponible is True
    assert e.error is None


def test_estado_disponible_sin_modelo_configurado():
    c = _client_mock(modelos=["otro"], has=False)
    e = estado_ollama(c, modelo_configurado="qwen3:4b")
    assert e.disponible is True
    assert e.modelo_configurado == "qwen3:4b"
    assert e.modelo_disponible is False


def test_estado_no_disponible_por_ping():
    c = _client_mock(ping=False)
    e = estado_ollama(c)
    assert e.disponible is False
    assert e.error is not None


def test_estado_no_disponible_por_version():
    c = _client_mock(ping=True)
    c.version.side_effect = OllamaError("boom")
    e = estado_ollama(c)
    assert e.disponible is False
    assert e.error and "version" in e.error


def test_estado_error_al_listar_modelos():
    c = _client_mock(ping=True)
    c.list_models.side_effect = OllamaError("boom")
    e = estado_ollama(c)
    assert e.disponible is True
    assert e.modelos == []
    assert e.error and "listar" in e.error


def test_probar_modelo_ok():
    c = _client_mock()
    c.check_model.return_value = None
    r = probar_modelo(c, "qwen3:4b")
    assert r.ok is True
    assert r.modelo == "qwen3:4b"
    assert r.error is None
    assert r.tiempo_s is not None


def test_probar_modelo_falla():
    c = _client_mock()
    c.check_model.side_effect = OllamaError("no responde")
    r = probar_modelo(c, "qwen3:4b")
    assert r.ok is False
    assert r.error and "no responde" in r.error


def test_mensaje_si_no_disponible_incluye_enlace():
    e = EstadoOllama(disponible=False, error="x")
    msg = mensaje_si_no_disponible(e)
    assert "ollama.com" in msg
    assert "ollama pull" in msg


def test_mensaje_si_sin_modelos_incluye_pull():
    e = EstadoOllama(disponible=True, modelos=[], version="0.40.16")
    msg = mensaje_si_sin_modelos(e)
    assert "ollama pull" in msg


def test_mensaje_modelo_no_disponible_lista():
    e = EstadoOllama(
        disponible=True,
        version="0.40.16",
        modelos=["a", "b"],
        modelo_configurado="qwen3:4b",
        modelo_disponible=False,
    )
    msg = mensaje_modelo_no_disponible(e)
    assert "qwen3:4b" in msg
    assert "a, b" in msg