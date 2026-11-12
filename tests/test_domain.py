"""Pruebas de los modelos de dominio."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.domain import (
    ActividadHabitual,
    Alimento,
    IngredienteReceta,
    ItemComida,
    Objetivos,
    Objetivo,
    Perfil,
    Receta,
    RegistroDiario,
    Sexo,
    Unidad,
)


def test_perfil_valid():
    p = Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)
    assert p.edad == 30
    assert p.unidad_peso == "kg"
    assert p.objetivo == Objetivo.MANTENIMIENTO


def test_perfil_edad_invalida():
    with pytest.raises(ValidationError):
        Perfil(edad=0, peso_kg=75.0, altura_cm=178.0)


def test_perfil_peso_invalido():
    with pytest.raises(ValidationError):
        Perfil(edad=30, peso_kg=0.5, altura_cm=178.0)


def test_perfil_extra_forbidden():
    with pytest.raises(ValidationError):
        Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, campo_extra="x")


def test_objetivos_todos_opcionales():
    o = Objetivos()
    assert o.kcal_diarias is None
    assert o.peso_objetivo_kg is None


def test_objetivos_kcal_negativas_falla():
    with pytest.raises(ValidationError):
        Objetivos(kcal_diarias=-1)


def test_actividad_defaults():
    a = ActividadHabitual()
    assert a.horas_actividad_laboral is None
    assert a.pasos_diarios_promedio is None


def test_alimento_valid():
    a = Alimento(
        id="arroz-blanco-cocido",
        nombre="Arroz blanco cocido",
        kcal_por_100=130.0,
        proteina_g_por_100=2.7,
        grasa_g_por_100=0.3,
        carbo_g_por_100=28.0,
    )
    assert a.id == "arroz-blanco-cocido"
    assert a.unidad_base == Unidad.G


def test_alimento_id_con_slash_falla():
    with pytest.raises(ValidationError):
        Alimento(id="a/b", nombre="x")


def test_alimento_valores_desconocidos_son_none():
    a = Alimento(id="x", nombre="X")
    assert a.kcal_por_100 is None
    assert a.proteina_g_por_100 is None


def test_receta_con_ingredientes():
    r = Receta(
        id="receta-1",
        nombre="Arroz con pollo",
        ingredientes=[
            IngredienteReceta(alimento_id="arroz", cantidad=150, unidad=Unidad.G),
            IngredienteReceta(alimento_id="pollo", cantidad=200, unidad=Unidad.G),
        ],
        rendimiento_porciones=2,
    )
    assert len(r.ingredientes) == 2
    assert r.rendimiento_porciones == 2


def test_item_comida_exige_exactamente_una_referencia():
    with pytest.raises(ValidationError):
        ItemComida(cantidad=100, unidad=Unidad.G)  # ninguna
    with pytest.raises(ValidationError):
        ItemComida(alimento_id="a", receta_id="r", cantidad=100, unidad=Unidad.G)
    ok = ItemComida(alimento_id="a", cantidad=100, unidad=Unidad.G)
    assert ok.alimento_id == "a"
    assert ok.etiqueta is None


def test_item_comida_con_receta_y_etiqueta():
    it = ItemComida(
        receta_id="arroz-con-pollo",
        cantidad=1.0,
        unidad=Unidad.PORCION,
        etiqueta="almuerzo",
    )
    assert it.receta_id == "arroz-con-pollo"
    assert it.alimento_id is None
    assert it.etiqueta == "almuerzo"


def test_registro_diario_lista_plana():
    r = RegistroDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemComida(alimento_id="huevo", cantidad=2, unidad=Unidad.UNIDAD),
            ItemComida(alimento_id="pan", cantidad=60, unidad=Unidad.G),
            ItemComida(
                receta_id="arroz-con-pollo",
                cantidad=1,
                unidad=Unidad.PORCION,
                etiqueta="almuerzo",
            ),
        ],
    )
    assert r.fecha == date(2026, 11, 12)
    assert len(r.items) == 3
    assert r.items[0].alimento_id == "huevo"
    assert r.items[2].receta_id == "arroz-con-pollo"
    assert r.items[2].etiqueta == "almuerzo"


def test_registro_diario_sin_items():
    r = RegistroDiario(fecha=date(2026, 11, 12))
    assert r.items == []
    assert r.actividad is None
    assert r.observaciones is None