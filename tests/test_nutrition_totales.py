"""Pruebas de totales diarios."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.nutrition import calcular_totales_dia
from app.core.results import Fuente
from app.models.domain import (
    Alimento,
    ItemComida,
    RegistroDiario,
    Unidad,
)
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _alimento(
    id_,
    kcal=None,
    prot=None,
    grasa=None,
    carb=None,
):
    return Alimento(
        id=id_,
        nombre=id_,
        kcal_por_100=kcal,
        proteina_g_por_100=prot,
        grasa_g_por_100=grasa,
        carbo_g_por_100=carb,
    )


def test_totales_sin_items(vault: Vault):
    reg = RegistroDiario(fecha=date(2026, 11, 12))
    out = calcular_totales_dia(reg, vault)
    assert out.items == []
    assert out.fuente == Fuente.DESCONOCIDO
    assert out.total.kcal is None
    assert out.notas and "Sin items" in out.notas[0]


def test_totales_todos_calculados(vault: Vault):
    vault.add_alimento(_alimento("a", kcal=100, prot=10, grasa=5, carb=20))
    vault.add_alimento(_alimento("b", kcal=200, prot=20, grasa=10, carb=40))
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="a", cantidad=100, unidad=Unidad.G),
            ItemComida(alimento_id="b", cantidad=100, unidad=Unidad.G),
        ],
    )
    out = calcular_totales_dia(reg, vault)
    assert out.fuente == Fuente.CALCULADO
    assert out.notas == []
    assert out.total.kcal == pytest.approx(300.0)
    assert out.total.proteina_g == pytest.approx(30.0)
    assert out.total.grasa_g == pytest.approx(15.0)
    assert out.total.carbo_g == pytest.approx(60.0)


def test_totales_parciales(vault: Vault):
    vault.add_alimento(_alimento("a", kcal=100, prot=10, grasa=5, carb=20))
    vault.add_alimento(_alimento("b", kcal=200))  # sin macros
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="a", cantidad=100, unidad=Unidad.G),
            ItemComida(alimento_id="b", cantidad=100, unidad=Unidad.G),
        ],
    )
    out = calcular_totales_dia(reg, vault)
    assert out.fuente == Fuente.PARCIAL
    assert out.total.kcal == pytest.approx(300.0)
    assert out.total.proteina_g is None
    assert any("proteina_g" in n or "proteína" in n for n in out.notas)


def test_totales_desconocidos(vault: Vault):
    vault.add_alimento(_alimento("a"))
    vault.add_alimento(_alimento("b"))
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="a", cantidad=100, unidad=Unidad.G),
            ItemComida(alimento_id="b", cantidad=100, unidad=Unidad.G),
        ],
    )
    out = calcular_totales_dia(reg, vault)
    assert out.fuente == Fuente.DESCONOCIDO
    assert out.total.kcal is None
    assert len(out.notas) >= 4