"""Pruebas de los tipos base del motor nutricional."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.core.results import (
    BalanceDiario,
    Fuente,
    ItemCalculado,
    Nutrientes,
    RecetaCalculada,
    TDEEEstimado,
    TotalesDia,
)
from app.models.domain import Unidad


def test_nutrientes_vacios_son_none_no_cero():
    n = Nutrientes()
    assert n.kcal is None
    assert n.proteina_g is None
    assert n.grasa_g is None
    assert n.carbo_g is None


def test_nutrientes_rechaza_negativos():
    with pytest.raises(ValidationError):
        Nutrientes(kcal=-1.0)


def test_nutrientes_extra_forbidden():
    with pytest.raises(ValidationError):
        Nutrientes(kcal=100.0, campo_extra=1)


def test_item_calculado_minimo():
    it = ItemCalculado(
        ref_tipo="alimento",
        ref_id="arroz",
        cantidad=150.0,
        unidad=Unidad.G,
        nutrientes=Nutrientes(kcal=195.0),
        fuente=Fuente.CALCULADO,
    )
    assert it.notas == []
    assert it.nutrientes.kcal == 195.0
    assert it.fuente == Fuente.CALCULADO


def test_item_calculado_ref_tipo_invalido():
    with pytest.raises(ValidationError):
        ItemCalculado(
            ref_tipo="otro",
            ref_id="x",
            cantidad=1.0,
            unidad=Unidad.G,
            nutrientes=Nutrientes(),
            fuente=Fuente.DESCONOCIDO,
        )


def test_item_calculado_cantidad_positiva():
    with pytest.raises(ValidationError):
        ItemCalculado(
            ref_tipo="alimento",
            ref_id="x",
            cantidad=0.0,
            unidad=Unidad.G,
            nutrientes=Nutrientes(),
            fuente=Fuente.DESCONOCIDO,
        )


def test_receta_calculada_basica():
    r = RecetaCalculada(
        receta_id="r1",
        rendimiento_porciones=2.0,
        total=Nutrientes(kcal=800.0),
        por_porcion=Nutrientes(kcal=400.0),
        fuente=Fuente.CALCULADO,
    )
    assert r.total.kcal == 800.0
    assert r.por_porcion.kcal == 400.0


def test_receta_calculada_rendimiento_positivo():
    with pytest.raises(ValidationError):
        RecetaCalculada(
            receta_id="r",
            rendimiento_porciones=0.0,
            total=Nutrientes(),
            por_porcion=Nutrientes(),
            fuente=Fuente.PARCIAL,
        )


def test_totales_dia_vacio():
    t = TotalesDia(
        fecha=date(2026, 11, 12),
        total=Nutrientes(),
        fuente=Fuente.DESCONOCIDO,
    )
    assert t.items == []
    assert t.total.kcal is None


def test_tdee_parcial():
    t = TDEEEstimado(
        bmr_kcal=1700.0,
        factor_actividad=None,
        tdee_kcal=None,
        fuente=Fuente.PARCIAL,
        notas=["Falta nivel de actividad"],
    )
    assert t.bmr_kcal == 1700.0
    assert t.tdee_kcal is None
    assert t.factor_actividad is None
    assert "Falta nivel de actividad" in t.notas


def test_balance_pendiente():
    b = BalanceDiario(
        fecha=date(2026, 11, 12),
        consumo_kcal=2000.0,
        gasto_kcal=None,
        balance_kcal=None,
        fuente=Fuente.PENDIENTE,
    )
    assert b.consumo_kcal == 2000.0
    assert b.gasto_kcal is None
    assert b.balance_kcal is None


def test_balance_negativo_permitido():
    # balance = consumo - gasto, puede ser negativo (déficit)
    b = BalanceDiario(
        fecha=date(2026, 11, 12),
        consumo_kcal=1800.0,
        gasto_kcal=2200.0,
        balance_kcal=-400.0,
        fuente=Fuente.CALCULADO,
    )
    assert b.balance_kcal == -400.0