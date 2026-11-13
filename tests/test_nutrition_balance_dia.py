"""Pruebas de balance con actividad del día."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.nutrition import calcular_balance
from app.core.results import Fuente
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


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    v = Vault(data, backups, root_for_backup=tmp_path)
    v.add_alimento(
        Alimento(
            id="arroz",
            nombre="Arroz",
            kcal_por_100=100.0,
            proteina_g_por_100=2.7,
            grasa_g_por_100=0.3,
            carbo_g_por_100=28.0,
        )
    )
    return v


def _perfil() -> Perfil:
    return Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)


def _reg_con(act_dia=None, items=1) -> RegistroDiario:
    return RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="arroz", cantidad=1000, unidad=Unidad.G)
            for _ in range(items)
        ],
        actividad_dia=act_dia,
    )


def test_balance_calculado_con_dia(vault: Vault):
    # 1000 g de arroz a 100 kcal/100 g -> 1000 kcal consumidas
    # TDEE día = 1717.5 * 1.55 = 2662.125
    reg = _reg_con(ActividadDia(pasos=12000))
    out = calcular_balance(reg, _perfil(), ActividadHabitual(), vault)
    assert out.fuente == Fuente.CALCULADO
    assert out.consumo_kcal == pytest.approx(1000.0)
    assert out.gasto_kcal == pytest.approx(2662.125)
    assert out.balance_kcal == pytest.approx(1000.0 - 2662.125)


def test_balance_parcial_si_usa_habitual(vault: Vault):
    # Sin actividad del día: usa habitual -> PARCIAL.
    reg = _reg_con(act_dia=None)
    out = calcular_balance(
        reg,
        _perfil(),
        ActividadHabitual(frecuencia_gimnasio_semanal=3),
        vault,
    )
    assert out.fuente == Fuente.PARCIAL
    assert out.consumo_kcal == pytest.approx(1000.0)
    assert out.gasto_kcal is not None
    assert out.balance_kcal is not None
    assert any(
        "habitual" in n.lower() or "aproximado" in n.lower() for n in out.notas
    )


def test_balance_pendiente_sin_gasto(vault: Vault):
    reg = _reg_con(act_dia=None)
    out = calcular_balance(reg, _perfil(), ActividadHabitual(), vault)
    assert out.fuente == Fuente.PENDIENTE
    assert out.gasto_kcal is None
    assert out.balance_kcal is None


def test_balance_pendiente_sin_consumo(vault: Vault):
    reg = RegistroDiario(
        fecha=date(2026, 11, 12), actividad_dia=ActividadDia(pasos=12000)
    )
    out = calcular_balance(reg, _perfil(), ActividadHabitual(), vault)
    assert out.fuente == Fuente.PENDIENTE
    assert out.consumo_kcal is None
    assert out.balance_kcal is None


def test_dia_prioritario_sobre_habitual_en_balance(vault: Vault):
    # Día: 12000 pasos -> 1.55. Habitual habría dado 1.725.
    reg = _reg_con(ActividadDia(pasos=12000))
    out = calcular_balance(
        reg,
        _perfil(),
        ActividadHabitual(frecuencia_gimnasio_semanal=5),
        vault,
    )
    assert out.fuente == Fuente.CALCULADO
    assert out.gasto_kcal == pytest.approx(1717.5 * 1.55)