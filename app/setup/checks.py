"""Comprobaciones de Ollama para el asistente de configuración.

No descarga modelos. No crea clientes. Recibe un OllamaClient y devuelve
estados tipados con mensajes legibles.
"""

from __future__ import annotations

import time
from typing import Optional

from pydantic import BaseModel, Field

from app.ollama_client import OllamaClient, OllamaError


class EstadoOllama(BaseModel):
    model_config = {"extra": "forbid"}

    disponible: bool
    version: Optional[str] = None
    modelos: list[str] = Field(default_factory=list)
    modelo_configurado: Optional[str] = None
    modelo_disponible: bool = False
    error: Optional[str] = None


class ResultadoPrueba(BaseModel):
    model_config = {"extra": "forbid"}

    ok: bool
    modelo: str
    error: Optional[str] = None
    tiempo_s: Optional[float] = None


def estado_ollama(
    client: OllamaClient,
    *,
    modelo_configurado: Optional[str] = None,
) -> EstadoOllama:
    """Comprueba ping, versión, modelos y disponibilidad del modelo configurado."""
    if not client.ping():
        return EstadoOllama(
            disponible=False,
            error="Ollama no responde en el host configurado.",
        )
    try:
        version = client.version()
    except OllamaError as exc:
        return EstadoOllama(
            disponible=False,
            error=f"Ollama responde pero /api/version falla: {exc}",
        )
    try:
        modelos = [m.name for m in client.list_models()]
    except OllamaError as exc:
        return EstadoOllama(
            disponible=True,
            version=version,
            modelos=[],
            modelo_configurado=modelo_configurado,
            modelo_disponible=False,
            error=f"No se pudo listar modelos: {exc}",
        )

    disp = False
    if modelo_configurado:
        disp = client.has_model(modelo_configurado)

    return EstadoOllama(
        disponible=True,
        version=version,
        modelos=modelos,
        modelo_configurado=modelo_configurado,
        modelo_disponible=disp,
    )


def probar_modelo(client: OllamaClient, modelo: str) -> ResultadoPrueba:
    """Prueba que el modelo responde con una generación corta.

    Devuelve ResultadoPrueba; nunca lanza OllamaError al llamante.
    """
    t0 = time.monotonic()
    try:
        client.check_model(modelo)
    except OllamaError as exc:
        return ResultadoPrueba(
            ok=False,
            modelo=modelo,
            error=str(exc),
            tiempo_s=time.monotonic() - t0,
        )
    return ResultadoPrueba(
        ok=True,
        modelo=modelo,
        tiempo_s=time.monotonic() - t0,
    )


def mensaje_si_no_disponible(estado: EstadoOllama) -> str:
    """Texto para el usuario cuando Ollama no está disponible."""
    return (
        "Ollama no está disponible.\n"
        f"Detalle: {estado.error or 'sin detalle'}\n"
        "Puedes continuar sin IA (solo memoria). Para habilitar la IA:\n"
        "  1. Instala Ollama: https://ollama.com/download/windows\n"
        "  2. Arranca Ollama (menú Inicio > Ollama).\n"
        "  3. Descarga un modelo compatible, por ejemplo:\n"
        "     ollama pull qwen3:4b-instruct-2507-q4_K_M"
    )


def mensaje_si_sin_modelos(estado: EstadoOllama) -> str:
    """Texto para el usuario cuando Ollama está activo pero no hay modelos."""
    return (
        "Ollama está activo pero no hay modelos descargados.\n"
        "Descarga uno compatible, por ejemplo:\n"
        "  ollama pull qwen3:4b-instruct-2507-q4_K_M\n"
        "Después vuelve a ejecutar NutricionAgent."
    )


def mensaje_modelo_no_disponible(estado: EstadoOllama) -> str:
    """Texto cuando hay modelos pero el configurado no está entre ellos."""
    lista = ", ".join(estado.modelos) if estado.modelos else "(ninguno)"
    return (
        f"El modelo configurado {estado.modelo_configurado!r} no está instalado.\n"
        f"Modelos disponibles: {lista}\n"
        "Elige otro modelo o descarga el configurado con `ollama pull <modelo>`."
    )