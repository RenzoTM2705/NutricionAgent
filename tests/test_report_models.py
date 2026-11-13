"""Pruebas de los modelos de reporte."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.core.report_models import (
    BalanceResumen,
    Comparacion,
    ItemResumen,
    ReporteDiario,
    ReporteMensual,
    ReporteSemanal,
)
from app.core.results import Fuente, Nutrientes
from app.models.domain import Unidad


def test_item_resumen_minimo():
    it = ItemResumen(
        indice=1,
        ref_tipo="alimento",
        ref_id="arroz",
        cantidad=150.0,
        unidad=Unidad.G,
    )
    assert it.kcal is None
    assert it.etiqueta is None


def test_item_resumen_extra_forbidden():
    with pytest.raises(ValidationError):
        ItemResumen(
            indice=1, ref_tipo="alimento", ref_id="x",
            cantidad=1, unidad=Unidad.G, extra=1,
        )


def test_balance_resumen_pendiente():
    b = BalanceResumen(fuente=Fuente.PENDIENTE)
    assert b.consumo_kcal is None
    assert b.balance_kcal is None


def test_reporte_diario_vacio():
    r = ReporteDiario(
        fecha=date(2026, 11, 12),
        totales=Nutrientes(),
        balance=BalanceResumen(fuente=Fuente.PENDIENTE),
        fuente=Fuente.DESCONOCIDO,
    )
    assert r.items == []
    assert r.totales.kcal is None


def test_comparacion_sin_anterior():
    c = Comparacion(valor_actual=2000.0)
    assert c.valor_anterior is None
    assert c.diferencia is None


def test_reporte_semanal_basico():
    r = ReporteSemanal(
        desde=date(2026, 11, 9),
        hasta=date(2026, 11, 15),
        dias_con_datos=5,
        dias_sin_datos=2,
        dias_entrenados=3,
        promedios=Nutrientes(kcal=2100.0, proteina_g=140.0),
        balance_promedio=BalanceResumen(
            consumo_kcal=2100.0,
            gasto_kcal=2400.0,
            balance_kcal=-300.0,
            fuente=Fuente.CALCULADO,
        ),
        fuente=Fuente.CALCULADO,
    )
    assert r.dias_con_datos == 5
    assert r.dias_sin_datos == 2
    assert r.dias_entrenados == 3
    assert r.promedios.kcal == 2100.0
    assert r.comparacion_kcal is None


def test_reporte_mensual_consistencia():
    r = ReporteMensual(
        desde=date(2026, 11, 1),
        hasta=date(2026, 11, 30),
        dias_con_datos=22,
        dias_sin_datos=8,
        consistencia_pct=73.3,
        promedios=Nutrientes(),
        balance_promedio=BalanceResumen(fuente=Fuente.PARCIAL),
        fuente=Fuente.PARCIAL,
    )
    assert r.consistencia_pct == 73.3


def test_consistencia_fuera_de_rango():
    with pytest.raises(ValidationError):
        ReporteMensual(
            desde=date(2026, 11, 1),
            hasta=date(2026, 11, 30),
            dias_con_datos=22,
            dias_sin_datos=8,
            consistencia_pct=150.0,
            promedios=Nutrientes(),
            balance_promedio=BalanceResumen(fuente=Fuente.PARCIAL),
            fuente=Fuente.PARCIAL,
        )