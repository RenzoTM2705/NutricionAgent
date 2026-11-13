"""Pruebas de balance energético diario."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.nutrition import calcular_balance
from app.core.results import Fuente
from app.models.domain import (
    ActividadHabitual,
    Alimento,
    ItemComida,
    Perfil,
    RegistroDiario,
    Sexo,
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


def _perfil(sexo=Sexo.MASCULINO) -> Perfil:
    return Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=sexo)


def _act() -> ActividadHabitual:
    return ActividadHabitual(frecuencia_gimnasio_semanal=3)


def _alimento(id_="arroz", kcal=130.0):
    return Alimento(
        id=id_,
        nombre=id_,
        kcal_por_100=kcal,
        proteina_g_por_100=2.7,
        grasa_g_por_100=0.3,
        carbo_g_por_100=28.0,
    )


def test_balance_parcial_con_actividad_habitual(vault: Vault):
    # Sin actividad del día: TDEE usa la habitual -> balance PARCIAL.
    vault.add_alimento(_alimento(kcal=100.0))
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[ItemComida(alimento_id="arroz", cantidad=2000, unidad=Unidad.G)],
    )
    out = calcular_balance(reg, _perfil(), _act(), vault)
    assert out.fuente == Fuente.PARCIAL
    assert out.consumo_kcal == pytest.approx(2000.0)
    assert out.gasto_kcal == pytest.approx(2662.125)
    assert out.balance_kcal == pytest.approx(2000.0 - 2662.125)
    assert any(
        "habitual" in n.lower() or "aproximado" in n.lower() for n in out.notas
    )


def test_balance_consumo_desconocido(vault: Vault):
    vault.add_alimento(Alimento(id="misterio", nombre="Misterio"))
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[ItemComida(alimento_id="misterio", cantidad=100, unidad=Unidad.G)],
    )
    out = calcular_balance(reg, _perfil(), _act(), vault)
    assert out.fuente == Fuente.PENDIENTE
    assert out.consumo_kcal is None
    assert out.gasto_kcal is not None
    assert out.balance_kcal is None


def test_balance_gasto_desconocido(vault: Vault):
    vault.add_alimento(_alimento())
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[ItemComida(alimento_id="arroz", cantidad=100, unidad=Unidad.G)],
    )
    out = calcular_balance(
        reg, _perfil(Sexo.NO_ESPECIFICADO), _act(), vault
    )
    assert out.fuente == Fuente.PENDIENTE
    assert out.gasto_kcal is None
    assert out.consumo_kcal is not None
    assert out.balance_kcal is None


def test_balance_sin_items(vault: Vault):
    reg = RegistroDiario(fecha=date(2026, 11, 12))
    out = calcular_balance(reg, _perfil(), _act(), vault)
    assert out.fuente == Fuente.PENDIENTE
    assert out.consumo_kcal is None
    assert out.gasto_kcal is not None
    assert out.balance_kcal is None


def test_balance_sin_actividad(vault: Vault):
    vault.add_alimento(_alimento())
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[ItemComida(alimento_id="arroz", cantidad=100, unidad=Unidad.G)],
    )
    out = calcular_balance(reg, _perfil(), ActividadHabitual(), vault)
    assert out.fuente == Fuente.PENDIENTE
    assert out.gasto_kcal is None
    assert out.consumo_kcal is not None