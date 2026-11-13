"""Pruebas de fórmulas metabólicas."""

from __future__ import annotations

import pytest

from app.core.metabolic import calcular_bmr, calcular_tdee, factor_actividad
from app.core.results import Fuente
from app.models.domain import ActividadHabitual, Perfil, Sexo


def _perfil(sexo=Sexo.MASCULINO) -> Perfil:
    return Perfil(
        edad=30,
        peso_kg=75.0,
        altura_cm=178.0,
        sexo=sexo,
    )


def _act(**kw) -> ActividadHabitual:
    return ActividadHabitual(**kw)


# --- BMR ---
def test_bmr_masculino():
    r = calcular_bmr(_perfil(Sexo.MASCULINO))
    # 10*75 + 6.25*178 - 5*30 + 5 = 750 + 1112.5 - 150 + 5 = 1717.5
    assert r.bmr_kcal == pytest.approx(1717.5)
    assert r.fuente == Fuente.CALCULADO


def test_bmr_femenino():
    r = calcular_bmr(_perfil(Sexo.FEMENINO))
    # 750 + 1112.5 - 150 - 161 = 1551.5
    assert r.bmr_kcal == pytest.approx(1551.5)
    assert r.fuente == Fuente.CALCULADO


def test_bmr_no_especificado_desconocido():
    r = calcular_bmr(_perfil(Sexo.NO_ESPECIFICADO))
    assert r.bmr_kcal is None
    assert r.fuente == Fuente.DESCONOCIDO
    assert any("sexo" in n.lower() for n in r.notas)


# --- factor de actividad ---
def test_factor_sin_datos():
    f, notas = factor_actividad(_act())
    assert f is None
    assert any("Faltan datos" in n for n in notas)


def test_factor_intenso():
    f, notas = factor_actividad(
        _act(frecuencia_gimnasio_semanal=5, pasos_diarios_promedio=12000)
    )
    assert f == 1.725
    assert any("1.725" in n for n in notas)


def test_factor_moderado_por_gimnasio():
    f, _ = factor_actividad(_act(frecuencia_gimnasio_semanal=3))
    assert f == 1.55


def test_factor_moderado_por_pasos():
    f, _ = factor_actividad(_act(pasos_diarios_promedio=10000))
    assert f == 1.55


def test_factor_ligero_por_gimnasio():
    f, _ = factor_actividad(_act(frecuencia_gimnasio_semanal=1))
    assert f == 1.375


def test_factor_ligero_por_pasos():
    f, _ = factor_actividad(_act(pasos_diarios_promedio=7000))
    assert f == 1.375


def test_factor_ligero_por_trabajo_activo():
    f, _ = factor_actividad(
        _act(horas_actividad_laboral=5, tiempo_de_pie_h=5)
    )
    assert f == 1.375


def test_factor_sedentario_por_datos_insuficientes():
    f, notas = factor_actividad(
        _act(horas_actividad_laboral=2, tiempo_de_pie_h=1)
    )
    assert f == 1.2
    assert any("conservador" in n for n in notas)


# --- TDEE ---
def test_tdee_calculado():
    r = calcular_tdee(
        _perfil(Sexo.MASCULINO),
        _act(frecuencia_gimnasio_semanal=3),
    )
    # BMR 1717.5 * 1.55 = 2662.125
    assert r.bmr_kcal == pytest.approx(1717.5)
    assert r.factor_actividad == pytest.approx(1.55)
    assert r.tdee_kcal == pytest.approx(2662.125)
    assert r.fuente == Fuente.CALCULADO


def test_tdee_parcial_sin_actividad():
    r = calcular_tdee(_perfil(Sexo.MASCULINO), _act())
    assert r.bmr_kcal == pytest.approx(1717.5)
    assert r.factor_actividad is None
    assert r.tdee_kcal is None
    assert r.fuente == Fuente.PARCIAL


def test_tdee_desconocido_sin_sexo_ni_actividad():
    r = calcular_tdee(_perfil(Sexo.NO_ESPECIFICADO), _act())
    assert r.bmr_kcal is None
    assert r.tdee_kcal is None
    assert r.fuente == Fuente.DESCONOCIDO