"""Pruebas del modelo ActividadDia y su integración en RegistroDiario."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.models.domain import ActividadDia, RegistroDiario


def test_actividad_dia_vacia():
    a = ActividadDia()
    assert a.horas_trabajo is None
    assert a.pasos is None
    assert a.gimnasio is None


def test_actividad_dia_completa():
    a = ActividadDia(
        horas_trabajo=8.0,
        horas_de_pie=4.0,
        pasos=9000,
        gimnasio=True,
        gimnasio_duracion_min=60,
        tipo_entrenamiento="fuerza",
        otros_deportes="caminata",
        notas="buen día",
    )
    assert a.pasos == 9000
    assert a.gimnasio is True
    assert a.gimnasio_duracion_min == 60


def test_actividad_dia_horas_fuera_de_rango():
    with pytest.raises(ValidationError):
        ActividadDia(horas_trabajo=30.0)


def test_actividad_dia_pasos_negativos():
    with pytest.raises(ValidationError):
        ActividadDia(pasos=-1)


def test_actividad_dia_extra_forbidden():
    with pytest.raises(ValidationError):
        ActividadDia(campo_extra=1)


def test_registro_diario_sin_actividad_dia():
    r = RegistroDiario(fecha=date(2026, 11, 12))
    assert r.actividad_dia is None


def test_registro_diario_con_actividad_dia():
    r = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(pasos=8000, gimnasio=True),
    )
    assert r.actividad_dia is not None
    assert r.actividad_dia.pasos == 8000
    assert r.actividad_dia.gimnasio is True


def test_registro_diario_json_roundtrip():
    r = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(pasos=8000, gimnasio=True, gimnasio_duracion_min=45),
    )
    data = r.model_dump(mode="json")
    r2 = RegistroDiario(**data)
    assert r2.actividad_dia is not None
    assert r2.actividad_dia.pasos == 8000
    assert r2.actividad_dia.gimnasio_duracion_min == 45