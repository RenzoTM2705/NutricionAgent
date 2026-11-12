"""Cliente HTTP mínimo para Ollama.

Solo transporte: no contiene lógica nutricional.
Todas las llamadas usan requests.Session y timeouts explícitos.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Iterable

import requests

from app.config import OllamaSettings

logger = logging.getLogger(__name__)


# --- Excepciones específicas ---
class OllamaError(Exception):
    """Base para errores del cliente Ollama."""


class OllamaNotRunning(OllamaError):
    """El servicio de Ollama no responde en el host configurado."""


class OllamaHTTPError(OllamaError):
    """Respuesta HTTP no exitosa."""

    def __init__(self, status_code: int, body: str, url: str) -> None:
        super().__init__(f"HTTP {status_code} en {url}: {body[:300]}")
        self.status_code = status_code
        self.body = body
        self.url = url


class OllamaResponseError(OllamaError):
    """Respuesta con formato inesperado o sin los campos requeridos."""


@dataclass(frozen=True)
class OllamaModel:
    name: str
    size: int
    digest: str
    modified_at: str


class OllamaClient:
    def __init__(self, settings: OllamaSettings) -> None:
        self._settings = settings
        self._session = requests.Session()
        self._base = settings.host.rstrip("/")

    # --- helpers ---
    def _url(self, path: str) -> str:
        return f"{self._base}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
        stream: bool = False,
        timeout: float | None = None,
    ) -> requests.Response:
        url = self._url(path)
        t = timeout if timeout is not None else self._settings.timeout_s
        try:
            resp = self._session.request(
                method,
                url,
                json=json_body,
                stream=stream,
                timeout=t,
            )
        except requests.exceptions.ConnectionError as exc:
            raise OllamaNotRunning(
                f"No se puede conectar con Ollama en {self._base}. "
                "¿Está el servicio en ejecución?"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise OllamaNotRunning(
                f"Timeout ({t}s) contactando Ollama en {url}."
            ) from exc
        if not resp.ok:
            raise OllamaHTTPError(resp.status_code, resp.text, url)
        return resp

    # --- API pública ---
    def ping(self) -> bool:
        """Devuelve True si /api/tags responde 200."""
        try:
            self._request("GET", "/api/tags", timeout=5.0)
            return True
        except OllamaError:
            return False

    def version(self) -> str:
        resp = self._request("GET", "/api/version", timeout=5.0)
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OllamaResponseError("Respuesta no es JSON.") from exc
        v = data.get("version")
        if not isinstance(v, str) or not v:
            raise OllamaResponseError("Falta 'version' en la respuesta.")
        return v

    def list_models(self) -> list[OllamaModel]:
        resp = self._request("GET", "/api/tags")
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OllamaResponseError("Respuesta no es JSON.") from exc
        models = data.get("models")
        if not isinstance(models, list):
            raise OllamaResponseError("Falta 'models' o no es lista.")
        out: list[OllamaModel] = []
        for m in models:
            if not isinstance(m, dict):
                continue
            name = m.get("name") or m.get("model")
            if not isinstance(name, str) or not name:
                continue
            out.append(
                OllamaModel(
                    name=name,
                    size=int(m.get("size", 0) or 0),
                    digest=str(m.get("digest", "") or ""),
                    modified_at=str(m.get("modified_at", "") or ""),
                )
            )
        return out

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        format_json: bool = False,
        options: dict[str, Any] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """Generación simple. Devuelve el texto de `response`."""
        body: dict[str, Any] = {
            "model": model or self._settings.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self._settings.temperature,
                "num_ctx": self._settings.num_ctx,
                **(options or {}),
            },
        }
        if format_json:
            body["format"] = "json"
        ka = keep_alive if keep_alive is not None else self._settings.keep_alive
        if ka:
            body["keep_alive"] = ka

        resp = self._request("POST", "/api/generate", json_body=body)
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OllamaResponseError("Respuesta no es JSON.") from exc
        text = data.get("response")
        if not isinstance(text, str):
            raise OllamaResponseError("Falta 'response' o no es string.")
        return text

    def chat(
        self,
        messages: Iterable[dict[str, str]],
        *,
        model: str | None = None,
        format_json: bool = False,
        options: dict[str, Any] | None = None,
        keep_alive: str | None = None,
    ) -> str:
        """Chat. Devuelve el contenido del último mensaje del asistente."""
        body: dict[str, Any] = {
            "model": model or self._settings.model,
            "messages": list(messages),
            "stream": False,
            "options": {
                "temperature": self._settings.temperature,
                "num_ctx": self._settings.num_ctx,
                **(options or {}),
            },
        }
        if format_json:
            body["format"] = "json"
        ka = keep_alive if keep_alive is not None else self._settings.keep_alive
        if ka:
            body["keep_alive"] = ka

        resp = self._request("POST", "/api/chat", json_body=body)
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise OllamaResponseError("Respuesta no es JSON.") from exc
        msg = data.get("message") or {}
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, str):
            raise OllamaResponseError("Falta 'message.content' o no es string.")
        return content

    # --- Selección y validación de modelo ---
    def has_model(self, name: str) -> bool:
        """True si el modelo está instalado (coincidencia exacta o por prefijo)."""
        try:
            models = self.list_models()
        except OllamaError:
            return False
        target = name.strip()
        for m in models:
            if m.name == target or m.name.startswith(target + ":") or m.name == target.split(":")[0]:
                return True
        return False

    def check_model(self, name: str, *, timeout_s: float = 60.0) -> None:
        """Valida que el modelo responde a una generación corta.

        Lanza OllamaError si el modelo no existe o no responde.
        """
        if not self.has_model(name):
            raise OllamaError(f"El modelo '{name}' no está instalado en Ollama.")
        text = self.generate(
            "Responde solo con la palabra: ok",
            model=name,
            options={"temperature": 0.0, "num_predict": 8},
            keep_alive=self._settings.keep_alive,
        )
        if not text.strip():
            raise OllamaResponseError(
                f"El modelo '{name}' devolvió una respuesta vacía."
            )

    def test_structured_output(
        self,
        name: str,
        *,
        timeout_s: float = 60.0,
    ) -> dict[str, Any]:
        """Valida que el modelo puede devolver JSON parseable.

        Devuelve el dict parseado. Lanza OllamaError/OllamaResponseError si no.
        """
        if not self.has_model(name):
            raise OllamaError(f"El modelo '{name}' no está instalado en Ollama.")
        prompt = (
            "Devuelve SOLO un objeto JSON con las claves "
            "'alimento' (string), 'gramos' (number) y 'calorias' (number) "
            "para: 150 gramos de arroz blanco cocido."
        )
        raw = self.generate(
            prompt,
            model=name,
            format_json=True,
            options={"temperature": 0.0, "num_predict": 128},
            keep_alive=self._settings.keep_alive,
        )
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise OllamaResponseError(
                f"El modelo '{name}' no devolvió JSON válido: {raw[:200]!r}"
            ) from exc
        if not isinstance(parsed, dict):
            raise OllamaResponseError(
                f"El modelo '{name}' devolvió JSON que no es objeto: {parsed!r}"
            )
        for k in ("alimento", "gramos", "calorias"):
            if k not in parsed:
                raise OllamaResponseError(
                    f"El modelo '{name}' devolvió JSON sin la clave '{k}'."
                )
        return parsed

    def select_model(self, name: str) -> str:
        """Valida el modelo (existencia + respuesta + JSON) y lo devuelve.

        No persiste nada. La persistencia corresponde a la capa de app.
        """
        self.check_model(name)
        self.test_structured_output(name)
        return name

    def close(self) -> None:
        self._session.close()