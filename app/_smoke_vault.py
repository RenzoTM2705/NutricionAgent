"""Script de humo: ejercita la capa Vault contra la bóveda real.

Uso:
    python -m app._smoke_vault

No borra datos existentes: los sobrescribe con backup previo.
Escribe un log en data/backups/smoke_vault_YYYYMMDD_HHMMSS.log.
Devuelve 0 si todo va bien, 1 si algo falla.
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from app.config import get_settings
from app.models.domain import (
    ActividadHabitual,
    Alimento,
    IngredienteReceta,
    ItemComida,
    Objetivos,
    Perfil,
    Receta,
    RegistroDiario,
    Sexo,
    Unidad,
)
from app.storage.vault import Vault, VaultError


def main() -> int:
    s = get_settings()
    log_path = (
        s.project_root
        / "data"
        / "backups"
        / f"smoke_vault_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = []

    def log(msg: str) -> None:
        print(msg)
        lines.append(msg)

    log(f"data_dir: {s.data_dir}")
    log(f"backup_root: {s.project_root / 'data' / 'backups'}")

    vault = Vault(
        data_dir=s.data_dir,
        backup_root=s.project_root / "data" / "backups",
        root_for_backup=s.project_root / "data",
    )

    try:
        # --- Perfil ---
        log("write_perfil...")
        vault.write_perfil(
            Perfil(
                edad=30,
                peso_kg=75.0,
                altura_cm=178.0,
                sexo=Sexo.MASCULINO,
            )
        )
        p = vault.read_perfil()
        assert p is not None and p.edad == 30 and p.sexo == Sexo.MASCULINO
        log(f"  OK -> {p.edad} años, {p.peso_kg} kg")

        # --- Objetivos ---
        log("write_objetivos...")
        vault.write_objetivos(Objetivos(kcal_diarias=2200, proteina_g=150))
        o = vault.read_objetivos()
        assert o is not None and o.kcal_diarias == 2200
        log(f"  OK -> {o.kcal_diarias} kcal, {o.proteina_g} g prot")

        # --- Actividad ---
        log("write_actividad...")
        vault.write_actividad(
            ActividadHabitual(
                tipo_trabajo="oficina",
                horas_actividad_laboral=8,
                pasos_diarios_promedio=6000,
            )
        )
        a = vault.read_actividad()
        assert a is not None and a.tipo_trabajo == "oficina"
        log(f"  OK -> {a.tipo_trabajo}, {a.horas_actividad_laboral} h")

        # --- Alimentos ---
        log("write_alimentos...")
        vault.write_alimentos([
            Alimento(
                id="arroz-blanco-cocido",
                nombre="Arroz blanco cocido",
                kcal_por_100=130.0,
                proteina_g_por_100=2.7,
                grasa_g_por_100=0.3,
                carbo_g_por_100=28.0,
                fuente="USDA",
            ),
            Alimento(
                id="huevo-entero",
                nombre="Huevo entero",
                unidad_base=Unidad.UNIDAD,
                peso_referencia_g=50.0,
                kcal_por_100=155.0,
                proteina_g_por_100=13.0,
                grasa_g_por_100=11.0,
                carbo_g_por_100=1.1,
            ),
        ])
        als = vault.read_alimentos()
        assert [x.id for x in als] == ["arroz-blanco-cocido", "huevo-entero"]
        log(f"  OK -> {len(als)} alimentos")

        # --- Receta ---
        log("write_recetas...")
        vault.write_recetas([
            Receta(
                id="arroz-con-pollo",
                nombre="Arroz con pollo",
                ingredientes=[
                    IngredienteReceta(
                        alimento_id="arroz-blanco-cocido",
                        cantidad=150.0,
                        unidad=Unidad.G,
                    ),
                ],
                rendimiento_porciones=2.0,
                notas="Receta de ejemplo",
            )
        ])
        rs = vault.read_recetas()
        assert len(rs) == 1 and rs[0].id == "arroz-con-pollo"
        assert rs[0].ingredientes[0].alimento_id == "arroz-blanco-cocido"
        log(f"  OK -> {len(rs)} receta(s)")

        # --- Registro diario ---
        log("write_registro...")
        d = date(2026, 11, 12)
        vault.write_registro(
            RegistroDiario(
                fecha=d,
                items=[
                    ItemComida(
                        alimento_id="huevo-entero",
                        cantidad=2.0,
                        unidad=Unidad.UNIDAD,
                        etiqueta="desayuno",
                    ),
                    ItemComida(
                        alimento_id="arroz-blanco-cocido",
                        cantidad=150.0,
                        unidad=Unidad.G,
                        etiqueta="almuerzo",
                    ),
                ],
                actividad=ActividadHabitual(
                    tipo_trabajo="oficina",
                    horas_actividad_laboral=8,
                ),
                observaciones="Registro de ejemplo generado por smoke_vault",
            )
        )
        r = vault.read_registro(d)
        assert r is not None and len(r.items) == 2
        assert r.items[0].etiqueta == "desayuno"
        assert r.actividad is not None
        log(f"  OK -> {len(r.items)} items, {r.observaciones!r}")

        # --- Listado ---
        log("list_registros...")
        fechas = vault.list_registros(date(2026, 11, 1), date(2026, 11, 30))
        assert d in fechas
        log(f"  OK -> {[f.isoformat() for f in fechas]}")

        log("RESULTADO: OK")
        rc = 0
    except (AssertionError, VaultError) as exc:
        log(f"RESULTADO: FALLO ({type(exc).__name__}: {exc})")
        rc = 1
    finally:
        log_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"\nlog guardado en: {log_path}")

    return rc


if __name__ == "__main__":
    sys.exit(main())