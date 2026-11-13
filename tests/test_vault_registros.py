"""Pruebas de Vault para registro diario."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.models.domain import (
    ActividadHabitual,
    ItemComida,
    RegistroDiario,
    Unidad,
)
from app.storage.vault import Vault, VaultError


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _reg(fecha=date(2026, 11, 12), **kw) -> RegistroDiario:
    base = dict(
        fecha=fecha,
        items=[
            ItemComida(alimento_id="huevo", cantidad=2, unidad=Unidad.UNIDAD),
            ItemComida(
                receta_id="arroz-con-pollo",
                cantidad=1,
                unidad=Unidad.PORCION,
                etiqueta="almuerzo",
            ),
        ],
    )
    base.update(kw)
    return RegistroDiario(**base)


def test_read_missing_returns_none(vault: Vault):
    assert vault.read_registro(date(2026, 11, 12)) is None


def test_write_read_roundtrip(vault: Vault):
    reg = _reg()
    vault.write_registro(reg)
    assert vault.registro_path(date(2026, 11, 12)).exists()
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.fecha == date(2026, 11, 12)
    assert len(got.items) == 2
    assert got.items[0].alimento_id == "huevo"
    assert got.items[1].receta_id == "arroz-con-pollo"
    assert got.items[1].etiqueta == "almuerzo"


def test_registro_sin_items(vault: Vault):
    reg = RegistroDiario(fecha=date(2026, 11, 12))
    vault.write_registro(reg)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.items == []


def test_registro_con_actividad_y_observaciones(vault: Vault):
    reg = _reg(
        actividad=ActividadHabitual(
            tipo_trabajo="oficina", horas_actividad_laboral=8
        ),
        observaciones="Día con mucho trabajo",
    )
    vault.write_registro(reg)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.observaciones == "Día con mucho trabajo"
    assert got.actividad is not None
    assert got.actividad.tipo_trabajo == "oficina"
    assert got.actividad.horas_actividad_laboral == 8


def test_sobrescribir_hace_backup(vault: Vault, tmp_path: Path):
    vault.write_registro(_reg())
    vault.write_registro(_reg())
    backups = list(
        (tmp_path / "backups").rglob("2026-11-12.md")
    )
    assert len(backups) == 1


def test_list_registros_filtra_por_rango(vault: Vault):
    for d in [date(2026, 11, 10), date(2026, 11, 12), date(2026, 12, 1)]:
        vault.write_registro(RegistroDiario(fecha=d))
    got = vault.list_registros(date(2026, 11, 1), date(2026, 11, 30))
    assert got == [date(2026, 11, 10), date(2026, 11, 12)]
    got2 = vault.list_registros(date(2026, 11, 1), date(2026, 12, 31))
    assert got2 == [date(2026, 11, 10), date(2026, 11, 12), date(2026, 12, 1)]


def test_list_registros_rango_invertido(vault: Vault):
    assert vault.list_registros(date(2026, 11, 30), date(2026, 11, 1)) == []


def test_fecha_incoherente_lanza_error(vault: Vault):
    path = vault.registro_path(date(2026, 11, 12))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        '---\ntipo: registro\nfecha: "2026-11-13"\n---\n# Registro\n',
        encoding="utf-8",
    )
    with pytest.raises(VaultError):
        vault.read_registro(date(2026, 11, 12))


def test_archivo_corrupto_lanza_error(vault: Vault):
    path = vault.registro_path(date(2026, 11, 12))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\ntipo: registro\nfecha: \"2026-11-12\"\n---\n# Registro\n\n## item-1\n\n```yaml\n",
        encoding="utf-8",
    )
    with pytest.raises(VaultError):
        vault.read_registro(date(2026, 11, 12))