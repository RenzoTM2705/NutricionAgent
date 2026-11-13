"""Script de humo de la Fase 9: reportes diario, semanal y mensual.

Uso:
    python -m app._smoke_fase9

No toca data/vault real. Usa una bóveda temporal en %TEMP%.
Escribe un log en data/backups/smoke_fase9_YYYYMMDD_HHMMSS.log.
Devuelve 0 si todo va bien, 1 si algo falla.
"""

from __future__ import annotations

import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

from app.config import get_settings
from app.core.reports import (
    generar_reporte_diario,
    generar_reporte_mensual,
    generar_reporte_semanal,
)
from app.models.domain import (
    ActividadDia,
    ActividadHabitual,
    Alimento,
    ItemComida,
    Perfil,
    RegistroDiario,
    Sexo,
    Unidad,
)
from app.storage.vault import Vault


def main() -> int:
    s = get_settings()
    log_path = (
        s.project_root / "data" / "backups"
        / f"smoke_fase9_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []
    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    log(f"data_dir real: {s.data_dir}")
    tmp_root = Path(tempfile.mkdtemp(prefix="nutricionagent_smoke9_"))
    log(f"bóveda temporal: {tmp_root}")
    vault = Vault(
        data_dir=tmp_root / "vault",
        backup_root=tmp_root / "backups",
        root_for_backup=tmp_root,
    )

    try:
        # Seed
        vault.write_perfil(
            Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)
        )
        vault.write_actividad(ActividadHabitual(frecuencia_gimnasio_semanal=3))
        vault.add_alimento(
            Alimento(
                id="arroz", nombre="Arroz",
                kcal_por_100=130.0, proteina_g_por_100=2.7,
                grasa_g_por_100=0.3, carbo_g_por_100=28.0,
            )
        )
        vault.add_alimento(
            Alimento(
                id="pollo", nombre="Pollo",
                kcal_por_100=165.0, proteina_g_por_100=31.0,
                grasa_g_por_100=3.6, carbo_g_por_100=0.0,
            )
        )

        hoy = date.today()
        # Tres días con datos: hoy, ayer, anteayer
        for i, gim in [(0, True), (1, False), (2, True)]:
            d = hoy - timedelta(days=i)
            reg = RegistroDiario(
                fecha=d,
                items=[
                    ItemComida(alimento_id="arroz", cantidad=150, unidad=Unidad.G),
                    ItemComida(alimento_id="pollo", cantidad=200, unidad=Unidad.G),
                ],
                actividad_dia=ActividadDia(
                    gimnasio=gim,
                    gimnasio_duracion_min=60 if gim else None,
                    pasos=12000 if gim else 5000,
                ),
            )
            vault.write_registro(reg)
            log(f"registro {d.isoformat()}: 2 items, gimnasio={gim}")

        # Reporte diario
        log("\n=== Reporte diario de hoy ===")
        r_d = generar_reporte_diario(hoy, vault)
        p_d = vault.write_reporte_diario(r_d)
        assert p_d.exists(), "No se escribió reporte diario"
        txt_d = p_d.read_text(encoding="utf-8")
        assert "# Reporte diario" in txt_d
        assert "| # | Ref |" in txt_d
        assert "## Totales" in txt_d
        assert "## Balance" in txt_d
        log(f"  items: {len(r_d.items)}")
        log(f"  totales: {r_d.totales.kcal} kcal")
        log(f"  balance: {r_d.balance.balance_kcal}")
        log(f"  archivo: {p_d.relative_to(vault.data_dir)}")

        # Reporte semanal
        log("\n=== Reporte semanal (últimos 7 días) ===")
        desde = hoy - timedelta(days=6)
        r_s = generar_reporte_semanal(desde, hoy, vault)
        p_s = vault.write_reporte_semanal(r_s)
        assert p_s.exists(), "No se escribió reporte semanal"
        txt_s = p_s.read_text(encoding="utf-8")
        assert "# Reporte semanal" in txt_s
        assert "## Resumen" in txt_s
        assert "## Promedios" in txt_s
        assert "## Balance promedio" in txt_s
        log(f"  días con datos: {r_s.dias_con_datos}")
        log(f"  días entrenados: {r_s.dias_entrenados}")
        log(f"  prom. kcal: {r_s.promedios.kcal}")
        log(f"  archivo: {p_s.relative_to(vault.data_dir)}")

        # Reporte mensual
        log("\n=== Reporte mensual ===")
        r_m = generar_reporte_mensual(hoy.year, hoy.month, vault)
        p_m = vault.write_reporte_mensual(r_m)
        assert p_m.exists(), "No se escribió reporte mensual"
        txt_m = p_m.read_text(encoding="utf-8")
        assert "# Reporte mensual" in txt_m
        assert "## Resumen" in txt_m
        assert "Consistencia" in txt_m
        log(f"  días con datos: {r_m.dias_con_datos}")
        log(f"  consistencia: {r_m.consistencia_pct}%")
        log(f"  archivo: {p_m.relative_to(vault.data_dir)}")

        # Lectura best-effort
        log("\n=== Relectura desde Markdown ===")
        rd = vault.read_reporte_diario(hoy)
        assert rd is not None
        log(f"  diario releído: fuente={rd.fuente.value}")
        iso = desde.isocalendar()
        rs = vault.read_reporte_semanal(iso[0], iso[1])
        assert rs is not None
        log(f"  semanal releído: días={rs.dias_con_datos}, entrenados={rs.dias_entrenados}")
        rm = vault.read_reporte_mensual(hoy.year, hoy.month)
        assert rm is not None
        log(f"  mensual releído: días={rm.dias_con_datos}, consistencia={rm.consistencia_pct}")

        # Bóveda real no tocada
        real = Vault(
            data_dir=s.data_dir,
            backup_root=s.data_dir.parent / "backups",
            root_for_backup=s.data_dir.parent,
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
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nlog guardado en: {log_path}")
        shutil.rmtree(tmp_root, ignore_errors=True)

    return rc


if __name__ == "__main__":
    sys.exit(main())