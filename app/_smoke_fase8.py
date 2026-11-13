"""Script de humo de la Fase 8: actividad del día y balance.

Uso:
    python -m app._smoke_fase8

No toca data/vault real. Usa una bóveda temporal en %TEMP%.
Escribe un log en data/backups/smoke_fase8_YYYYMMDD_HHMMSS.log.
Devuelve 0 si todo va bien, 1 si algo falla.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from rich.console import Console

from app.agent import loop as loop_module
from app.agent.loop import run_loop
from app.agent.tools import totales
from app.config import get_settings
from app.core.nutrition import calcular_balance
from app.models.domain import (
    ActividadDia,
    ActividadHabitual,
    Perfil,
    Sexo,
)
from app.ollama_client import OllamaClient
from app.storage.vault import Vault


def main() -> int:
    s = get_settings()
    log_path = (
        s.project_root / "data" / "backups"
        / f"smoke_fase8_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    log(f"modelo: {s.ollama.model}")
    log(f"host: {s.ollama.host}")
    log(f"data_dir real: {s.data_dir}")

    tmp_root = Path(tempfile.mkdtemp(prefix="nutricionagent_smoke8_"))
    log(f"bóveda temporal: {tmp_root}")
    vault = Vault(
        data_dir=tmp_root / "vault",
        backup_root=tmp_root / "backups",
        root_for_backup=tmp_root,
    )
    vault.write_perfil(
        Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)
    )
    vault.write_actividad(
        ActividadHabitual(frecuencia_gimnasio_semanal=3, pasos_diarios_promedio=6000)
    )

    client = OllamaClient(s.ollama)

    _orig = loop_module._ejecutar_operacion
    def _wrapped(op, registro, vault_, console):
        log(f"[turno] op={type(op).__name__} ({op.tipo})")
        reg_nuevo, cambio = _orig(op, registro, vault_, console)
        log(f"  cambio={cambio}, items={len(reg_nuevo.items)}, "
            f"act_dia={'sí' if reg_nuevo.actividad_dia else 'no'}")
        return reg_nuevo, cambio
    loop_module._ejecutar_operacion = _wrapped

    buffer = io.StringIO()
    console = Console(file=buffer, width=120)

    prompts = [
        "añade arroz, 130 kcal por 100 g, 2.7 g proteína, 0.3 g grasa, 28 g carbohidratos",
        "agregué 300 g de arroz",
        "/hoy",
        "hoy anduve 12000 pasos y fui al gimnasio 1 hora",
        "/salir",
    ]

    def _lines():
        it = iter(prompts)
        def _ask(*a, **k):
            try:
                return next(it)
            except StopIteration:
                raise EOFError
        return _ask

    confirmaciones = [True]
    def _confirm(*a, **k):
        return confirmaciones.pop(0) if confirmaciones else False

    rc = 0
    try:
        if not client.ping():
            log("Ollama no responde. Abortando.")
            return 1

        with patch("app.agent.loop.Prompt.ask", side_effect=_lines()), \
             patch("app.agent.loop.Confirm.ask", side_effect=_confirm):
            rc_bucle = run_loop(vault, client, console)
        log(f"run_loop devolvió: {rc_bucle}")
        log(f"salida del bucle:\n{buffer.getvalue()}")

        # Verificaciones
        reg = vault.read_registro(date.today())
        assert reg is not None, "No se guardó el registro."
        assert len(reg.items) == 1, f"Se esperaba 1 item, hay {len(reg.items)}."
        assert reg.items[0].cantidad == 300.0, (
            f"Se esperaba cantidad 300, hay {reg.items[0].cantidad}."
        )
        log(f"registro: {len(reg.items)} item(s), {reg.items[0].cantidad} g")

        assert reg.actividad_dia is not None, "No se guardó actividad_dia."
        log(f"actividad_dia: pasos={reg.actividad_dia.pasos}, "
            f"gimnasio={reg.actividad_dia.gimnasio}, "
            f"dur={reg.actividad_dia.gimnasio_duracion_min}")

        t = totales(reg, vault)
        assert t.total.kcal == 390.0, f"Se esperaban 390 kcal, hay {t.total.kcal}."
        log(f"totales: {t.total.kcal} kcal")

        perfil = vault.read_perfil()
        hab = vault.read_actividad()
        assert perfil is not None and hab is not None
        bal = calcular_balance(reg, perfil, hab, vault)
        log(f"balance: fuente={bal.fuente.value}, consumo={bal.consumo_kcal}, "
            f"gasto={bal.gasto_kcal}, balance={bal.balance_kcal}")
        assert bal.fuente.value == "calculado", (
            f"Se esperaba balance calculado, es {bal.fuente.value}."
        )
        # TDEE con 12000 pasos + gimnasio 60 -> 1.725 (regla 1)
        # 1717.5 * 1.725 = 2962.6875
        assert bal.gasto_kcal is not None and abs(bal.gasto_kcal - 2962.6875) < 0.01
        log("balance calculado con actividad del día: OK")

        real = Vault(
            data_dir=s.data_dir,
            backup_root=s.data_dir.parent / "backups",
            root_for_backup=s.data_dir.parent,
        )
        p = real.read_perfil()
        log(f"bóveda real: {'con perfil' if p else 'sin perfil'}")

        log("RESULTADO: OK")
        rc = 0
    except AssertionError as exc:
        log(f"RESULTADO: FALLO (assert): {exc}")
        rc = 1
    except Exception as exc:
        log(f"RESULTADO: FALLO ({type(exc).__name__}): {exc}")
        rc = 1
    finally:
        client.close()
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nlog guardado en: {log_path}")
        shutil.rmtree(tmp_root, ignore_errors=True)

    return rc


if __name__ == "__main__":
    sys.exit(main())