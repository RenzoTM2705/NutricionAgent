"""Pruebas de cálculo de reportes."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.reports import (
    generar_reporte_diario,
    generar_reporte_mensual,
    generar_reporte_semanal,
)
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
    v.write_perfil(Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO))
    v.write_actividad(ActividadHabitual(frecuencia_gimnasio_semanal=3))
    v.add_alimento(
        Alimento(
            id="arroz",
            nombre="Arroz",
            kcal_por_100=100.0,
            proteina_g_por_100=2.0,
            grasa_g_por_100=0.5,
            carbo_g_por_100=20.0,
        )
    )
    return v


def _escribir_dia(vault, d, cantidad=100.0, gimnasio=False):
    reg = RegistroDiario(
        fecha=d,
        items=[ItemComida(alimento_id="arroz", cantidad=cantidad, unidad=Unidad.G)],
        actividad_dia=ActividadDia(gimnasio=gimnasio, pasos=10000 if gimnasio else None),
    )
    vault.write_registro(reg)


def test_diario_sin_registro(vault: Vault):
    r = generar_reporte_diario(date(2026, 11, 12), vault)
    assert r.fuente == Fuente.DESCONOCIDO
    assert r.items == []
    assert r.totales.kcal is None


def test_diario_con_registro(vault: Vault):
    _escribir_dia(vault, date(2026, 11, 12), cantidad=200.0)
    r = generar_reporte_diario(date(2026, 11, 12), vault)
    assert r.fuente == Fuente.CALCULADO
    assert len(r.items) == 1
    assert r.items[0].kcal == 200.0
    assert r.totales.kcal == 200.0
    assert r.balance.consumo_kcal == 200.0
    assert r.balance.fuente == Fuente.CALCULADO


def test_semanal_dias_con_y_sin_datos(vault: Vault):
    _escribir_dia(vault, date(2026, 11, 10))
    _escribir_dia(vault, date(2026, 11, 12))
    r = generar_reporte_semanal(date(2026, 11, 9), date(2026, 11, 15), vault)
    assert r.dias_con_datos == 2
    assert r.dias_sin_datos == 5
    assert r.promedios.kcal == pytest.approx(100.0)
    assert r.fuente == Fuente.CALCULADO


def test_semanal_dias_entrenados(vault: Vault):
    _escribir_dia(vault, date(2026, 11, 10), gimnasio=True)
    _escribir_dia(vault, date(2026, 11, 11), gimnasio=False)
    _escribir_dia(vault, date(2026, 11, 12), gimnasio=True)
    r = generar_reporte_semanal(date(2026, 11, 9), date(2026, 11, 15), vault)
    assert r.dias_entrenados == 2


def test_semanal_promedio_parcial_por_none(vault: Vault):
    # Día 1: nutrientes completos. Día 2: alimento sin macros (solo kcal).
    vault.add_alimento(Alimento(id="solo_kcal", nombre="Solo kcal", kcal_por_100=200.0))
    vault.write_registro(
        RegistroDiario(
            fecha=date(2026, 11, 10),
            items=[ItemComida(alimento_id="arroz", cantidad=100, unidad=Unidad.G)],
        )
    )
    vault.write_registro(
        RegistroDiario(
            fecha=date(2026, 11, 11),
            items=[ItemComida(alimento_id="solo_kcal", cantidad=100, unidad=Unidad.G)],
        )
    )
    r = generar_reporte_semanal(date(2026, 11, 10), date(2026, 11, 11), vault)
    assert r.promedios.kcal == pytest.approx(150.0)  # (100 + 200) / 2
    assert r.promedios.proteina_g is None  # día 2 sin dato
    assert r.fuente == Fuente.PARCIAL


def test_mensual_consistencia(vault: Vault):
    for d in [1, 2, 3]:
        _escribir_dia(vault, date(2026, 11, d))
    r = generar_reporte_mensual(2026, 11, vault)
    assert r.dias_con_datos == 3
    assert r.dias_sin_datos == 27
    assert r.consistencia_pct == pytest.approx(10.0)


def test_mensual_sin_datos(vault: Vault):
    r = generar_reporte_mensual(2026, 11, vault)
    assert r.dias_con_datos == 0
    assert r.fuente == Fuente.DESCONOCIDO
    assert r.promedios.kcal is None


def test_comparacion_semana_anterior(vault: Vault):
    # Semana del 9-15: dos días con 100 kcal -> promedio 100
    _escribir_dia(vault, date(2026, 11, 10))
    _escribir_dia(vault, date(2026, 11, 12))
    # Semana del 2-8: dos días con 200 kcal -> promedio 200
    _escribir_dia(vault, date(2026, 11, 3), cantidad=200)
    _escribir_dia(vault, date(2026, 11, 5), cantidad=200)
    r = generar_reporte_semanal(date(2026, 11, 9), date(2026, 11, 15), vault)
    assert r.comparacion_kcal is not None
    assert r.comparacion_kcal.valor_actual == pytest.approx(100.0)
    assert r.comparacion_kcal.valor_anterior == pytest.approx(200.0)
    assert r.comparacion_kcal.diferencia == pytest.approx(-100.0)