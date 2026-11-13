"""Pruebas de integración del motor nutricional con Vault real."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.metabolic import calcular_tdee
from app.core.nutrition import (
    calcular_balance,
    calcular_item,
    calcular_receta,
    calcular_totales_dia,
)
from app.core.results import Fuente
from app.models.domain import (
    ActividadHabitual,
    Alimento,
    IngredienteReceta,
    ItemComida,
    Perfil,
    Receta,
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


def _seed(vault: Vault) -> None:
    vault.write_perfil(
        Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)
    )
    vault.write_actividad(
        ActividadHabitual(frecuencia_gimnasio_semanal=3, pasos_diarios_promedio=8000)
    )
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
    vault.write_recetas([
        Receta(
            id="arroz-pollo",
            nombre="Arroz con pollo",
            ingredientes=[
                IngredienteReceta(alimento_id="arroz", cantidad=150.0, unidad=Unidad.G),
                IngredienteReceta(alimento_id="pollo", cantidad=200.0, unidad=Unidad.G),
            ],
            rendimiento_porciones=2.0,
        )
    ])


def test_flujo_completo(vault: Vault):
    _seed(vault)

    perfil = vault.read_perfil()
    actividad = vault.read_actividad()
    assert perfil is not None and actividad is not None

    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="arroz", cantidad=150.0, unidad=Unidad.G),
            ItemComida(
                receta_id="arroz-pollo", cantidad=1.0, unidad=Unidad.PORCION
            ),
        ],
    )

    # Item alimento
    it_arroz = calcular_item(reg.items[0], vault)
    assert it_arroz.fuente == Fuente.CALCULADO
    assert it_arroz.nutrientes.kcal == pytest.approx(195.0)

    # Item receta
    it_rec = calcular_item(reg.items[1], vault)
    assert it_rec.fuente == Fuente.CALCULADO
    # receta total kcal = 195 + 330 = 525, por porción = 262.5, por 1 porción = 262.5
    assert it_rec.nutrientes.kcal == pytest.approx(262.5)

    # Totales
    totales = calcular_totales_dia(reg, vault)
    assert totales.fuente == Fuente.CALCULADO
    assert totales.total.kcal == pytest.approx(195.0 + 262.5)

    # TDEE
    tdee = calcular_tdee(perfil, actividad)
    assert tdee.fuente == Fuente.CALCULADO
    assert tdee.tdee_kcal is not None

    # Balance
    balance = calcular_balance(reg, perfil, actividad, vault)
    assert balance.fuente == Fuente.PARCIAL
    assert balance.consumo_kcal == pytest.approx(457.5)
    assert balance.gasto_kcal == pytest.approx(tdee.tdee_kcal)
    assert balance.balance_kcal == pytest.approx(457.5 - tdee.tdee_kcal)
    assert any(
            "habitual" in n.lower() or "aproximado" in n.lower()
            for n in balance.notas
        )


def test_receta_calculada_desde_vault(vault: Vault):
    _seed(vault)
    receta = vault.get_receta("arroz-pollo")
    assert receta is not None
    out = calcular_receta(receta, vault)
    assert out.fuente == Fuente.CALCULADO
    assert out.total.kcal == pytest.approx(525.0)
    assert out.por_porcion.kcal == pytest.approx(262.5)


def test_registro_parcial_por_alimento_sin_datos(vault: Vault):
    vault.add_alimento(Alimento(id="misterio", nombre="Misterio"))
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="misterio", cantidad=100.0, unidad=Unidad.G)
        ],
    )
    totales = calcular_totales_dia(reg, vault)
    assert totales.fuente == Fuente.DESCONOCIDO
    assert totales.total.kcal is None


def test_persistencia_registro_tras_calculo(vault: Vault):
    """El cálculo no debe escribir en la bóveda."""
    _seed(vault)
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="arroz", cantidad=100.0, unidad=Unidad.G)
        ],
    )
    # Antes de calcular, no hay registro guardado
    assert vault.read_registro(date(2026, 11, 12)) is None
    calcular_totales_dia(reg, vault)
    # Tras calcular, sigue sin haberlo
    assert vault.read_registro(date(2026, 11, 12)) is None