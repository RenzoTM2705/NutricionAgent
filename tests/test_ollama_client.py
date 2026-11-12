"""Pruebas del cliente Ollama con mocks (sin red)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
import requests

from app.config import OllamaSettings
from app.ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaHTTPError,
    OllamaNotRunning,
    OllamaResponseError,
)


# --- Helpers ---
def _mock_response(status: int = 200, payload: dict | list | None = None, text: str | None = None) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status
    resp.ok = 200 <= status < 300
    if payload is not None:
        resp.json.return_value = payload
        resp.text = json.dumps(payload)
    else:
        resp.json.side_effect = json.JSONDecodeError("no json", "", 0)
        resp.text = text or ""
    return resp


def _install_mock(monkeypatch, resp: MagicMock) -> MagicMock:
    """Instala un mock de requests.Session.request y lo devuelve."""
    mock = MagicMock(return_value=resp)
    monkeypatch.setattr(requests.Session, "request", mock)
    return mock


# --- ping ---
def test_ping_true(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(200, {"models": []}))
    c = OllamaClient(ollama_settings)
    assert c.ping() is True


def test_ping_false_on_connection_error(monkeypatch, ollama_settings):
    def boom(*a, **kw):
        raise requests.exceptions.ConnectionError("nope")
    monkeypatch.setattr(requests.Session, "request", boom)
    c = OllamaClient(ollama_settings)
    assert c.ping() is False


# --- version ---
def test_version_ok(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(200, {"version": "0.40.16"}))
    c = OllamaClient(ollama_settings)
    assert c.version() == "0.40.16"


def test_version_missing_field(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(200, {}))
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaResponseError):
        c.version()


# --- list_models ---
def test_list_models_ok(monkeypatch, ollama_settings):
    _install_mock(
        monkeypatch,
        _mock_response(
            200,
            {
                "models": [
                    {"name": "a:1b", "size": 123, "digest": "d", "modified_at": "t"},
                    {"model": "b:2b", "size": 456, "digest": "d2", "modified_at": "t2"},
                ]
            },
        ),
    )
    c = OllamaClient(ollama_settings)
    models = c.list_models()
    assert [m.name for m in models] == ["a:1b", "b:2b"]
    assert models[0].size == 123


def test_list_models_tolerates_garbage(monkeypatch, ollama_settings):
    _install_mock(
        monkeypatch,
        _mock_response(
            200,
            {"models": ["garbage", {"no_name": True}, {"name": "ok:1b"}]},
        ),
    )
    c = OllamaClient(ollama_settings)
    models = c.list_models()
    assert [m.name for m in models] == ["ok:1b"]


# --- generate ---
def test_generate_builds_payload(monkeypatch, ollama_settings):
    mock = _install_mock(
        monkeypatch,
        _mock_response(200, {"response": "hola"}),
    )
    c = OllamaClient(ollama_settings)
    out = c.generate("di hola", format_json=True, options={"num_predict": 8})
    assert out == "hola"
    args, kwargs = mock.call_args
    method, url = args[0], args[1]
    assert method == "POST"
    assert url.endswith("/api/generate")
    body = kwargs["json"]
    assert body["model"] == "test:model"
    assert body["format"] == "json"
    assert body["keep_alive"] == "5m"
    assert body["options"]["temperature"] == 0.0
    assert body["options"]["num_ctx"] == 4096
    assert body["options"]["num_predict"] == 8


def test_generate_connection_error(monkeypatch, ollama_settings):
    def boom(*a, **kw):
        raise requests.exceptions.ConnectionError("nope")
    monkeypatch.setattr(requests.Session, "request", boom)
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaNotRunning):
        c.generate("x")


def test_generate_http_error(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(500, text="boom"))
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaHTTPError):
        c.generate("x")


def test_generate_missing_field(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(200, {"not_response": "x"}))
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaResponseError):
        c.generate("x")


# --- chat ---
def test_chat_ok(monkeypatch, ollama_settings):
    _install_mock(
        monkeypatch,
        _mock_response(200, {"message": {"role": "assistant", "content": "hola"}}),
    )
    c = OllamaClient(ollama_settings)
    assert c.chat([{"role": "user", "content": "di hola"}]) == "hola"


def test_chat_missing_content(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(200, {"message": {}}))
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaResponseError):
        c.chat([{"role": "user", "content": "x"}])


# --- selección y validación ---
def test_has_model_prefix(monkeypatch, ollama_settings):
    _install_mock(
        monkeypatch,
        _mock_response(200, {"models": [{"name": "qwen3:4b-instruct-2507-q4_K_M"}]}),
    )
    c = OllamaClient(ollama_settings)
    assert c.has_model("qwen3") is True
    assert c.has_model("qwen3:4b-instruct-2507-q4_K_M") is True
    assert c.has_model("otro") is False


def test_check_model_missing(monkeypatch, ollama_settings):
    _install_mock(monkeypatch, _mock_response(200, {"models": []}))
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaError):
        c.check_model("nope")


def test_check_model_ok(monkeypatch, ollama_settings):
    # Primera llamada: list_models. Segunda: generate.
    responses = [
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": "ok"}),
    ]
    mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "request", mock)
    c = OllamaClient(ollama_settings)
    c.check_model("test:model")


def test_check_model_empty_response(monkeypatch, ollama_settings):
    responses = [
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": "   "}),
    ]
    mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "request", mock)
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaResponseError):
        c.check_model("test:model")


def test_structured_output_invalid_json(monkeypatch, ollama_settings):
    responses = [
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": "not json"}),
    ]
    mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "request", mock)
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaResponseError):
        c.test_structured_output("test:model")


def test_structured_output_missing_key(monkeypatch, ollama_settings):
    responses = [
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": json.dumps({"alimento": "x", "gramos": 1})}),
    ]
    mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "request", mock)
    c = OllamaClient(ollama_settings)
    with pytest.raises(OllamaResponseError):
        c.test_structured_output("test:model")


def test_structured_output_ok(monkeypatch, ollama_settings):
    payload = {"alimento": "arroz", "gramos": 150, "calorias": 210}
    responses = [
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": json.dumps(payload)}),
    ]
    mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "request", mock)
    c = OllamaClient(ollama_settings)
    assert c.test_structured_output("test:model") == payload


def test_select_model_calls_both(monkeypatch, ollama_settings):
    payload = {"alimento": "arroz", "gramos": 150, "calorias": 210}
    responses = [
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": "ok"}),
        _mock_response(200, {"models": [{"name": "test:model"}]}),
        _mock_response(200, {"response": json.dumps(payload)}),
    ]
    mock = MagicMock(side_effect=responses)
    monkeypatch.setattr(requests.Session, "request", mock)
    c = OllamaClient(ollama_settings)
    assert c.select_model("test:model") == "test:model"