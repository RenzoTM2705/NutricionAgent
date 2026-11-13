"""Pruebas de cálculo de recetas completas."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ReferenciaInexistente
from app.core.nutrition import calcular_receta
from app.core.results import Fuente
from app.models.domain import (
    Alimento,
    IngredienteReceta,
    Receta,
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


def _alimento(id_, kcal=None, prot=None, grasa=None, carb=None):
    return Alimento(
        id=id_,
        nombre=id_,
        kcal_por_100=kcal,
        proteina_g_por_100=prot,
        grasa_g_por_100=grasa,
        carbo_g_por_100=carb,
    )


def test_receta_calculada_completa(vault: Vault):
    vault.add_alimento(_alimento("arroz", 130, 2.7, 0.3, 28))
    vault.add_alimento(_alimento("pollo", 165, 31, 3.6, 0))
    r = Receta(
        id="arroz-pollo",
        nombre="Arroz con pollo",
        ingredientes=[
            IngredienteReceta(alimento_id="arroz", cantidad=150, unidad=Unidad.G),
            IngredienteReceta(alimento_id="pollo", cantidad=200, unidad=Unidad.G),
        ],
        rendimiento_porciones=2.0,
    )
    out = calcular_receta(r, vault)
    assert out.fuente == Fuente.CALCULADO
    assert out.notas == []
    # kcal: 130*1.5 + 165*2.0 = 195 + 330 = 525
    assert out.total.kcal == pytest.approx(525.0)
    assert out.total.proteina_g == pytest.approx(2.7 * 1.5 + 31 * 2.0)
    assert out.por_porcion.kcal == pytest.approx(262.5)


def test_receta_sin_ingredientes(vault: Vault):
    r = Receta(
        id="vacia",
        nombre="Vacía",
        ingredientes=[],
        rendimiento_porciones=1.0,
    )
    out = calcular_receta(r, vault)
    assert out.fuente == Fuente.DESCONOCIDO
    assert out.total.kcal is None
    assert any("sin ingredientes" in n.lower() for n in out.notas)


def test_receta_con_ingrediente_parcial(vault: Vault):
    vault.add_alimento(_alimento("arroz", 130, 2.7, 0.3, 28))
    vault.add_alimento(_alimento("misterio", kcal=200))  # sin macros
    r = Receta(
        id="mixta",
        nombre="Mixta",
        ingredientes=[
            IngredienteReceta(alimento_id="arroz", cantidad=100, unidad=Unidad.G),
            IngredienteReceta(alimento_id="misterio", cantidad=100, unidad=Unidad.G),
        ],
        rendimiento_porciones=1.0,
    )
    out = calcular_receta(r, vault)
    assert out.fuente == Fuente.PARCIAL
    assert out.total.kcal == pytest.approx(330.0)
    assert out.total.proteina_g is None
    assert any("proteína" in n for n in out.notas)


def test_receta_ingrediente_inexistente_falla(vault: Vault):
    r = Receta(
        id="fantasma",
        nombre="Fantasma",
        ingredientes=[
            IngredienteReceta(alimento_id="no-existe", cantidad=100, unidad=Unidad.G),
        ],
        rendimiento_porciones=1.0,
    )
    with pytest.raises(ReferenciaInexistente):
        calcular_receta(r, vault)


def test_receta_por_porcion_con_rendimiento_mayor(vault: Vault):
    vault.add_alimento(_alimento("arroz", 100, 10, 5, 20))
    r = Receta(
        id="r",
        nombre="R",
        ingredientes=[
            IngredienteReceta(alimento_id="arroz", cantidad=400, unidad=Unidad.G),
        ],
        rendimiento_porciones=4.0,
    )
    out = calcular_receta(r, vault)
    assert out.total.kcal == pytest.approx(400.0)
    assert out.por_porcion.kcal == pytest.approx(100.0)
    assert out.por_porcion.proteina_g == pytest.approx(10.0)