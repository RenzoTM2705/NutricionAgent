"""Script de humo: valida el cliente Ollama contra el servicio real.

Uso:
    python -m app._smoke_ollama

Escribe un log en data/backups/smoke_ollama_YYYYMMDD_HHMMSS.log
y devuelve código de salida 0 si todo va bien, 1 si algo falla.
"""

from __future__ import annotations

import sys
from datetime import datetime

from app.config import get_settings
from app.ollama_client import OllamaClient, OllamaError


def _log(lines: list[str], msg: str) -> None:
    print(msg)
    lines.append(msg)


def main() -> int:
    s = get_settings()
    log_path = (
        s.project_root
        / "data"
        / "backups"
        / f"smoke_ollama_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    _log(lines, f"host: {s.ollama.host}")
    _log(lines, f"model: {s.ollama.model}")

    c = OllamaClient(s.ollama)
    try:
        _log(lines, f"ping: {c.ping()}")
        _log(lines, f"version: {c.version()}")

        models = c.list_models()
        _log(lines, f"modelos instalados: {len(models)}")
        for m in models:
            _log(lines, f"  - {m.name} ({m.size / 1e9:.2f} GB)")

        if not c.has_model(s.ollama.model):
            _log(lines, f"ERROR: el modelo configurado no está instalado: {s.ollama.model}")
            return 1

        _log(lines, "check_model...")
        c.check_model(s.ollama.model)
        _log(lines, "  OK")

        _log(lines, "test_structured_output...")
        data = c.test_structured_output(s.ollama.model)
        _log(lines, f"  OK -> {data}")

        _log(lines, "select_model...")
        sel = c.select_model(s.ollama.model)
        _log(lines, f"  seleccionado: {sel}")

        _log(lines, "RESULTADO: OK")
        rc = 0
    except OllamaError as exc:
        _log(lines, f"RESULTADO: FALLO ({type(exc).__name__}: {exc})")
        rc = 1
    finally:
        c.close()
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nlog guardado en: {log_path}")

    return rc


if __name__ == "__main__":
    sys.exit(main())