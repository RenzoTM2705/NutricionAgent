"""Pruebas de calcular_tdee_dia."""

from __future__ import annotations

import pytest

from app.core.metabolic import calcular_tdee_dia
from app.core.results import Fuente
from app.models.domain import ActividadDia, ActividadHabitual, Perfil, Sexo


def _perfil(sexo=Sexo.MASCULINO) -> Perfil:
    return Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=sexo)


def test_dia_completo_intenso():
    r = calcular_tdee_dia(
        _perfil(),
        actividad_dia=ActividadDia(
            gimnasio=True, gimnasio_duracion_min=60, pasos=12000
        ),
    )
    assert r.fuente == Fuente.CALCULADO
    assert r.factor_actividad == pytest.approx(1.725)
    assert r.tdee_kcal == pytest.approx(1717.5 * 1.725)


def test_dia_moderado():
    r = calcular_tdee_dia(
        _perfil(),
        actividad_dia=ActividadDia(gimnasio=True, gimnasio_duracion_min=45),
    )
    assert r.fuente == Fuente.CALCULADO
    assert r.factor_actividad == pytest.approx(1.55)


def test_dia_ligero_por_pasos():
    r = calcular_tdee_dia(
        _perfil(), actividad_dia=ActividadDia(pasos=8500)
    )
    assert r.fuente == Fuente.CALCULADO
    assert r.factor_actividad == pytest.approx(1.375)


def test_dia_sedentario():
    r = calcular_tdee_dia(
        _perfil(), actividad_dia=ActividadDia(horas_trabajo=2, horas_de_pie=1)
    )
    assert r.fuente == Fuente.CALCULADO
    assert r.factor_actividad == pytest.approx(1.2)


def test_sin_dia_usa_habitual_parcial():
    r = calcular_tdee_dia(
        _perfil(),
        actividad_habitual=ActividadHabitual(frecuencia_gimnasio_semanal=3),
    )
    assert r.fuente == Fuente.PARCIAL
    assert r.factor_actividad == pytest.approx(1.55)
    assert any("habitual" in n for n in r.notas)


def test_dia_prioritario_sobre_habitual():
    r = calcular_tdee_dia(
        _perfil(),
        actividad_habitual=ActividadHabitual(frecuencia_gimnasio_semanal=5),
        actividad_dia=ActividadDia(pasos=12000),
    )
    # Día: 12000 pasos -> 1.55; habitual habría dado 1.725
    assert r.fuente == Fuente.CALCULADO
    assert r.factor_actividad == pytest.approx(1.55)


def test_sin_dia_ni_habitual_parcial_por_bmr():
    # Sin día ni habitual: BMR existe, factor no. TDEE parcial.
    r = calcular_tdee_dia(_perfil())
    assert r.fuente == Fuente.PARCIAL
    assert r.tdee_kcal is None
    assert r.bmr_kcal is not None


def test_sin_sexo_ni_actividad_desconocido():
    r = calcular_tdee_dia(_perfil(Sexo.NO_ESPECIFICADO))
    assert r.fuente == Fuente.DESCONOCIDO
    assert r.tdee_kcal is None

def test_sin_sexo_pero_con_dia_parcial():
    r = calcular_tdee_dia(
        _perfil(Sexo.NO_ESPECIFICADO),
        actividad_dia=ActividadDia(pasos=10000),
    )
    assert r.fuente == Fuente.PARCIAL
    assert r.tdee_kcal is None
    assert r.factor_actividad == pytest.approx(1.55)