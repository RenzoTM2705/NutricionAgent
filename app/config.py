"""Configuración central de NutricionAgent.

Reglas:
- No hardcodear rutas absolutas del desarrollador.
- La raíz del proyecto se detecta desde la ubicación de este archivo.
- La ruta de datos es configurable vía NUTRICIONAGENT_DATA_DIR.
- Toda la configuración técnica se tipa y valida con Pydantic.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator


# --- Detección portable de la raíz del proyecto ---
# Este archivo vive en <raíz>/app/config.py.
# parents[1] = <raíz>.
PROJECT_ROOT: Path = Path(__file__).resolve().parents[1]

# Cargar .env desde la raíz, si existe. No es obligatorio.
_ENV_FILE = PROJECT_ROOT / ".env"
if _ENV_FILE.exists():
    load_dotenv(_ENV_FILE, override=False)


def _resolve_data_dir() -> Path:
    """Resuelve la ruta de datos del usuario.

    Prioridad:
    1. NUTRICIONAGENT_DATA_DIR (absoluta o relativa a PROJECT_ROOT).
    2. PROJECT_ROOT/data/vault
    """
    raw = os.getenv("NUTRICIONAGENT_DATA_DIR", "").strip()
    if not raw:
        return PROJECT_ROOT / "data" / "vault"
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (PROJECT_ROOT / p).resolve()
    return p


class OllamaSettings(BaseModel):
    host: str = "http://localhost:11434"
    model: str = "qwen3:4b-instruct-2507-q4_K_M"
    temperature: float = Field(default=0.0, ge=0.0, le=2.0)
    num_ctx: int = Field(default=4096, ge=512, le=131072)
    keep_alive: str = "5m"
    timeout_s: float = Field(default=120.0, gt=0.0)

    @field_validator("host")
    @classmethod
    def _strip_trailing_slash(cls, v: str) -> str:
        return v.rstrip("/")


class Settings(BaseModel):
    project_root: Path
    data_dir: Path
    log_level: str = "INFO"
    ollama: OllamaSettings

    @field_validator("log_level")
    @classmethod
    def _valid_log_level(cls, v: str) -> str:
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v = v.upper()
        if v not in allowed:
            raise ValueError(f"LOG_LEVEL inválido: {v}. Use uno de {sorted(allowed)}")
        return v

    def ensure_data_dir(self) -> Path:
        """Crea el directorio de datos si no existe y comprueba escritura."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        probe = self.data_dir / ".write_probe"
        try:
            probe.write_text("ok", encoding="utf-8")
        finally:
            try:
                probe.unlink()
            except FileNotFoundError:
                pass
        return self.data_dir


def _build_settings() -> Settings:
    ollama = OllamaSettings(
        host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        model=os.getenv("OLLAMA_MODEL", "qwen3:4b-instruct-2507-q4_K_M"),
        temperature=float(os.getenv("OLLAMA_TEMPERATURE", "0.0")),
        num_ctx=int(os.getenv("OLLAMA_NUM_CTX", "4096")),
        keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "5m"),
        timeout_s=float(os.getenv("OLLAMA_TIMEOUT_S", "120")),
    )
    return Settings(
        project_root=PROJECT_ROOT,
        data_dir=_resolve_data_dir(),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        ollama=ollama,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Devuelve la configuración (cacheada)."""
    s = _build_settings()
    s.ensure_data_dir()
    return s