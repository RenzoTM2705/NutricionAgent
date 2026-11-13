"""Pruebas de cálculo por item (alimento y receta)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.errors import ReferenciaInexistente, UnidadIncompatible
from app.core.nutrition import calcular_ingrediente, calcular_item
from app.core.results import Fuente
from app.models.domain import (
    Alimento,
    IngredienteReceta,
    ItemComida,
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


def _alimento_full(id_="arroz") -> Alimento:
    return Alimento(
        id=id_,
        nombre="Arroz",
        kcal_por_100=130.0,
        proteina_g_por_100=2.7,
        grasa_g_por_100=0.3,
        carbo_g_por_100=28.0,
    )


def _alimento_parcial(id_="misterio") -> Alimento:
    return Alimento(id=id_, nombre="Misterio", kcal_por_100=200.0)


def _alimento_vacio(id_="nada") -> Alimento:
    return Alimento(id=id_, nombre="Nada")


# --- alimento ---
def test_alimento_calculado(vault: Vault):
    vault.add_alimento(_alimento_full())
    item = ItemComida(alimento_id="arroz", cantidad=150, unidad=Unidad.G)
    out = calcular_item(item, vault)
    assert out.fuente == Fuente.CALCULADO
    assert out.notas == []
    assert out.nutrientes.kcal == pytest.approx(195.0)
    assert out.nutrientes.proteina_g == pytest.approx(4.05)
    assert out.nutrientes.grasa_g == pytest.approx(0.45)
    assert out.nutrientes.carbo_g == pytest.approx(42.0)


def test_alimento_parcial(vault: Vault):
    vault.add_alimento(_alimento_parcial())
    item = ItemComida(alimento_id="misterio", cantidad=100, unidad=Unidad.G)
    out = calcular_item(item, vault)
    assert out.fuente == Fuente.PARCIAL
    assert out.nutrientes.kcal == pytest.approx(200.0)
    assert out.nutrientes.proteina_g is None
    assert any("proteína" in n for n in out.notas)


def test_alimento_desconocido(vault: Vault):
    vault.add_alimento(_alimento_vacio())
    item = ItemComida(alimento_id="nada", cantidad=100, unidad=Unidad.G)
    out = calcular_item(item, vault)
    assert out.fuente == Fuente.DESCONOCIDO
    assert out.nutrientes.kcal is None
    assert len(out.notas) == 4


def test_alimento_inexistente(vault: Vault):
    item = ItemComida(alimento_id="fantasma", cantidad=100, unidad=Unidad.G)
    with pytest.raises(ReferenciaInexistente):
        calcular_item(item, vault)


def test_unidad_sin_peso_referencia_falla(vault: Vault):
    vault.add_alimento(_alimento_full())
    item = ItemComida(alimento_id="arroz", cantidad=2, unidad=Unidad.UNIDAD)
    with pytest.raises(UnidadIncompatible):
        calcular_item(item, vault)


# --- ingrediente ---
def test_ingrediente_calculado(vault: Vault):
    vault.add_alimento(_alimento_full())
    ing = IngredienteReceta(alimento_id="arroz", cantidad=50, unidad=Unidad.G)
    out = calcular_ingrediente(ing, vault)
    assert out.fuente == Fuente.CALCULADO
    assert out.nutrientes.kcal == pytest.approx(65.0)


# --- receta como item ---
def test_receta_como_item_sin_ingredientes(vault: Vault):
    """Una receta sin ingredientes produce item DESCONOCIDO con nota."""
    vault.add_receta(
        Receta(
            id="r1",
            nombre="Test",
            ingredientes=[],
            rendimiento_porciones=1.0,
        )
    )
    item = ItemComida(receta_id="r1", cantidad=1.0, unidad=Unidad.PORCION)
    out = calcular_item(item, vault)
    assert out.fuente == Fuente.DESCONOCIDO
    assert out.nutrientes.kcal is None
    assert any("sin ingredientes" in n.lower() for n in out.notas)


def test_receta_inexistente(vault: Vault):
    item = ItemComida(receta_id="fantasma", cantidad=1.0, unidad=Unidad.PORCION)
    with pytest.raises(ReferenciaInexistente):
        calcular_item(item, vault)


def test_receta_unidad_no_porcion_falla(vault: Vault):
    vault.add_receta(
        Receta(
            id="r1",
            nombre="Test",
            ingredientes=[],
            rendimiento_porciones=1.0,
        )
    )
    item = ItemComida(receta_id="r1", cantidad=100, unidad=Unidad.G)
    with pytest.raises(UnidadIncompatible):
        calcular_item(item, vault)