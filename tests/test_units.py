"""Pruebas de conversión de unidades."""

from __future__ import annotations

import pytest

from app.core.errors import NutritionError, UnidadIncompatible
from app.core.units import convertir_a_gramos, convertir_a_mililitros
from app.models.domain import Alimento, Unidad


def _alimento(
    id_="arroz",
    unidad_base=Unidad.G,
    peso_ref=None,
) -> Alimento:
    return Alimento(
        id=id_,
        nombre="Test",
        unidad_base=unidad_base,
        peso_referencia_g=peso_ref,
        kcal_por_100=100.0,
    )


# --- convertir_a_gramos ---
def test_gramos_a_gramos():
    a = _alimento()
    assert convertir_a_gramos(150, Unidad.G, a) == 150.0


def test_unidad_a_gramos_con_peso_referencia():
    a = _alimento(peso_ref=50.0)
    assert convertir_a_gramos(2, Unidad.UNIDAD, a) == 100.0
    assert convertir_a_gramos(1.5, Unidad.PORCION, a) == 75.0


def test_unidad_a_gramos_sin_peso_referencia_falla():
    a = _alimento(peso_ref=None)
    with pytest.raises(UnidadIncompatible):
        convertir_a_gramos(2, Unidad.UNIDAD, a)


def test_gramos_a_gramos_alimento_base_ml_falla():
    a = _alimento(unidad_base=Unidad.ML)
    with pytest.raises(UnidadIncompatible):
        convertir_a_gramos(150, Unidad.G, a)


def test_ml_a_gramos_falla():
    a = _alimento()
    with pytest.raises(UnidadIncompatible):
        convertir_a_gramos(100, Unidad.ML, a)


def test_cantidad_negativa_falla():
    a = _alimento()
    with pytest.raises(NutritionError):
        convertir_a_gramos(-1, Unidad.G, a)


def test_cantidad_cero_falla():
    a = _alimento()
    with pytest.raises(NutritionError):
        convertir_a_gramos(0, Unidad.G, a)


def test_cantidad_no_finita_falla():
    a = _alimento()
    with pytest.raises(NutritionError):
        convertir_a_gramos(float("inf"), Unidad.G, a)


# --- convertir_a_mililitros ---
def test_ml_a_ml():
    a = _alimento(unidad_base=Unidad.ML)
    assert convertir_a_mililitros(200, Unidad.ML, a) == 200.0


def test_unidad_a_ml_con_referencia():
    a = _alimento(unidad_base=Unidad.ML, peso_ref=250.0)
    assert convertir_a_mililitros(2, Unidad.UNIDAD, a) == 500.0


def test_unidad_a_ml_sin_referencia_falla():
    a = _alimento(unidad_base=Unidad.ML, peso_ref=None)
    with pytest.raises(UnidadIncompatible):
        convertir_a_mililitros(2, Unidad.UNIDAD, a)


def test_ml_a_ml_alimento_base_g_falla():
    a = _alimento(unidad_base=Unidad.G)
    with pytest.raises(UnidadIncompatible):
        convertir_a_mililitros(200, Unidad.ML, a)


def test_g_a_ml_falla():
    a = _alimento(unidad_base=Unidad.ML)
    with pytest.raises(UnidadIncompatible):
        convertir_a_mililitros(100, Unidad.G, a)