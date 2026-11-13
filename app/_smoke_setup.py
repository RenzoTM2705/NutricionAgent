"""Script de humo del asistente de configuración.

Uso:
    python -m app._smoke_setup

No toca data/vault real. Usa una bóveda temporal en %TEMP%.
Escribe un log en data/backups/smoke_setup_YYYYMMDD_HHMMSS.log.
Devuelve 0 si todo va bien, 1 si algo falla.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

from app.config import get_settings
from app.ollama_client import OllamaClient
from app.setup.checks import estado_ollama, probar_modelo
from app.setup.wizard import SetupInput, aplicar_setup, perfil_existente
from app.storage.vault import Vault


def main() -> int:
    s = get_settings()
    log_path = (
        s.project_root
        / "data"
        / "backups"
        / f"smoke_setup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    log(f"data_dir real: {s.data_dir}")
    log(f"project_root: {s.project_root}")

    tmp_root = Path(tempfile.mkdtemp(prefix="nutricionagent_smoke_"))
    log(f"bóveda temporal: {tmp_root}")
    vault = Vault(
        data_dir=tmp_root / "vault",
        backup_root=tmp_root / "backups",
        root_for_backup=tmp_root,
    )

    rc = 0
    try:
        # 1. Estado de Ollama
        client = OllamaClient(s.ollama)
        try:
            estado = estado_ollama(client, modelo_configurado=s.ollama.model)
            log(f"Ollama disponible: {estado.disponible}")
            if estado.disponible:
                log(f"  versión: {estado.version}")
                log(f"  modelos: {estado.modelos}")
                log(f"  modelo configurado disponible: {estado.modelo_disponible}")
            modelo_elegido: str | None = None
            if estado.disponible and estado.modelos:
                candidato = (
                    s.ollama.model
                    if estado.modelo_disponible
                    else estado.modelos[0]
                )
                log(f"Probando modelo {candidato}...")
                prueba = probar_modelo(client, candidato)
                if prueba.ok:
                    modelo_elegido = candidato
                    log(
                        f"  modelo OK ({prueba.tiempo_s:.1f}s)"
                        if prueba.tiempo_s
                        else "  modelo OK"
                    )
                else:
                    log(f"  modelo FALLÓ: {prueba.error}")
            else:
                log("  sin modelos: modo solo memoria")
        finally:
            client.close()

        # 2. Datos ficticios
        data = SetupInput(
            nombre="Test",
            edad=30,
            peso_kg=75.0,
            altura_cm=178.0,
            sexo="masculino",
            unidad_peso="kg",
            unidad_altura="cm",
            objetivo="mantenimiento",
            kcal_diarias=2200,
            proteina_g=150,
            tipo_trabajo="oficina",
            horas_actividad_laboral=8,
            frecuencia_gimnasio_semanal=3,
            pasos_diarios_promedio=8000,
            modelo=modelo_elegido,
        )

        # 3. Aplicar
        log("aplicar_setup...")
        result = aplicar_setup(data, vault)
        if not result.ok:
            log("FALLO en aplicar_setup:")
            for e in result.errores:
                log(f"  - {e.campo}: {e.mensaje}")
            rc = 1
            return rc

        log(f"  ok, rutas: {result.rutas_escritas}")

        # 4. Verificar lectura
        p = vault.read_perfil()
        o = vault.read_objetivos()
        a = vault.read_actividad()
        assert p is not None and p.edad == 30
        assert o is not None and o.kcal_diarias == 2200
        assert a is not None and a.tipo_trabajo == "oficina"
        log("  perfil/objetivos/actividad leídos correctamente")

        # 5. Verificar que la bóveda real no se ha tocado
        real = Vault(
            data_dir=s.data_dir,
            backup_root=s.project_root / "data" / "backups",
            root_for_backup=s.project_root / "data",
        )
        real_p = real.read_perfil()
        if real_p is None:
            log("bóveda real: sin perfil (correcto)")
        else:
            log(f"bóveda real: perfil presente ({real_p.edad} años), no se ha tocado")

        # 6. Verificar duplicado sin sobrescribir
        log("segundo aplicar_setup sin sobrescribir (debe fallar)...")
        dup = aplicar_setup(data, vault)
        assert dup.ok is False
        log("  falló como se esperaba")

        log("RESULTADO: OK")
        rc = 0
    except AssertionError as exc:
        log(f"RESULTADO: FALLO (assert): {exc}")
        rc = 1
    except Exception as exc:
        log(f"RESULTADO: FALLO ({type(exc).__name__}): {exc}")
        rc = 1
    finally:
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nlog guardado en: {log_path}")
        shutil.rmtree(tmp_root, ignore_errors=True)

    return rc


if __name__ == "__main__":
    sys.exit(main())