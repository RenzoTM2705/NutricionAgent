"""Script de humo del agente conversacional.

Uso:
    python -m app._smoke_agent

No toca data/vault real. Usa una bóveda temporal en %TEMP%.
Escribe un log en data/backups/smoke_agent_YYYYMMDD_HHMMSS.log.
Devuelve 0 si todo va bien, 1 si algo falla.
"""

from __future__ import annotations

import io
import shutil
import sys
import tempfile
from datetime import date, datetime
from pathlib import Path

from rich.console import Console

from app.agent.interpreter import interpretar
from app.agent.operations import (
    AgregarItemOp,
    ConsultarTotalesOp,
    EliminarItemOp,
)
from app.agent.tools import agregar_item, eliminar_item_por_indice, totales
from app.config import get_settings
from app.models.domain import (
    ActividadHabitual,
    Alimento,
    Perfil,
    RegistroDiario,
    Sexo,
)
from app.ollama_client import OllamaClient
from app.storage.vault import Vault


def main() -> int:
    s = get_settings()
    log_path = (
        s.project_root
        / "data"
        / "backups"
        / f"smoke_agent_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    log(f"modelo: {s.ollama.model}")
    log(f"host: {s.ollama.host}")
    log(f"data_dir real: {s.data_dir}")

    tmp_root = Path(tempfile.mkdtemp(prefix="nutricionagent_smoke_agent_"))
    log(f"bóveda temporal: {tmp_root}")
    vault = Vault(
        data_dir=tmp_root / "vault",
        backup_root=tmp_root / "backups",
        root_for_backup=tmp_root,
    )

    client = OllamaClient(s.ollama)
    console = Console(file=io.StringIO(), width=120)

    rc = 0
    try:
        # Seed
        vault.write_perfil(
            Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)
        )
        vault.write_actividad(ActividadHabitual(frecuencia_gimnasio_semanal=3))
        vault.write_alimentos([
            Alimento(
                id="arroz",
                nombre="Arroz blanco cocido",
                kcal_por_100=130.0,
                proteina_g_por_100=2.7,
                grasa_g_por_100=0.3,
                carbo_g_por_100=28.0,
            ),
            Alimento(
                id="pollo",
                nombre="Pechuga de pollo",
                kcal_por_100=165.0,
                proteina_g_por_100=31.0,
                grasa_g_por_100=3.6,
                carbo_g_por_100=0.0,
            ),
        ])

        if not client.ping():
            log("Ollama no responde. Abortando.")
            rc = 1
            return rc

        today = date.today()
        registro = RegistroDiario(fecha=today)

        # Turno 1: agregar arroz
        log("\n--- Turno 1: agregar 150 g de arroz ---")
        op1 = interpretar(
            "agregué 150 g de arroz blanco cocido",
            vault=vault,
            client=client,
            registro=registro,
        )
        log(f"operación: {op1.tipo}")
        if not isinstance(op1, AgregarItemOp):
            log(f"FALLO: se esperaba agregar_item, recibido {op1.tipo}")
            rc = 1
            return rc
        registro = agregar_item(
            registro, op1.alimento_id, op1.cantidad, op1.unidad, vault=vault
        )
        vault.write_registro(registro)
        log(f"registro guardado con {len(registro.items)} item(s)")

        # Turno 2: consultar totales
        log("\n--- Turno 2: consultar totales ---")
        op2 = interpretar(
            "¿cuántas kcal llevo hoy?",
            vault=vault,
            client=client,
            registro=registro,
        )
        log(f"operación: {op2.tipo}")
        if not isinstance(op2, ConsultarTotalesOp):
            log(f"FALLO: se esperaba consultar_totales, recibido {op2.tipo}")
            rc = 1
            return rc
        t = totales(registro, vault)
        log(f"totales: {t.total.kcal} kcal, fuente {t.fuente.value}")
        assert t.total.kcal is not None and t.total.kcal > 0

        # Turno 3: eliminar item 1
        log("\n--- Turno 3: eliminar el item 1 ---")
        op3 = interpretar(
            "elimina el primer item",
            vault=vault,
            client=client,
            registro=registro,
        )
        log(f"operación: {op3.tipo}")
        if not isinstance(op3, EliminarItemOp):
            log(f"FALLO: se esperaba eliminar_item, recibido {op3.tipo}")
            rc = 1
            return rc
        registro = eliminar_item_por_indice(registro, op3.indice)
        vault.write_registro(registro)
        log(f"registro guardado con {len(registro.items)} item(s)")
        assert len(registro.items) == 0

        # Verificar bóveda real no tocada
        real = Vault(
            data_dir=s.data_dir,
            backup_root=s.project_root / "data" / "backups",
            root_for_backup=s.project_root / "data",
        )
        p = real.read_perfil()
        log(f"\nbóveda real: {'con perfil' if p else 'sin perfil'}")

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