"""Fórmulas metabólicas: BMR (Mifflin-St Jeor), factor de actividad, TDEE.

Sin IA. Funciones puras sobre datos validados del perfil y la actividad.
"""

from __future__ import annotations

from typing import Optional

from app.core.results import Fuente, TDEEEstimado
from app.models.domain import ActividadHabitual, Perfil, Sexo


def calcular_bmr(perfil: Perfil) -> TDEEEstimado:
    """Mifflin-St Jeor.

    Masculino: 10*peso_kg + 6.25*altura_cm - 5*edad + 5
    Femenino:  10*peso_kg + 6.25*altura_cm - 5*edad - 161
    Otro / No especificado: None (fuente DESCONOCIDO).
    """
    if perfil.sexo == Sexo.MASCULINO:
        bmr = 10 * perfil.peso_kg + 6.25 * perfil.altura_cm - 5 * perfil.edad + 5
        return TDEEEstimado(
            bmr_kcal=float(bmr),
            factor_actividad=None,
            tdee_kcal=None,
            fuente=Fuente.CALCULADO,
            notas=["BMR calculado con Mifflin-St Jeor (masculino)."],
        )
    if perfil.sexo == Sexo.FEMENINO:
        bmr = 10 * perfil.peso_kg + 6.25 * perfil.altura_cm - 5 * perfil.edad - 161
        return TDEEEstimado(
            bmr_kcal=float(bmr),
            factor_actividad=None,
            tdee_kcal=None,
            fuente=Fuente.CALCULADO,
            notas=["BMR calculado con Mifflin-St Jeor (femenino)."],
        )
    return TDEEEstimado(
        bmr_kcal=None,
        factor_actividad=None,
        tdee_kcal=None,
        fuente=Fuente.DESCONOCIDO,
        notas=[
            "BMR no calculable: Mifflin-St Jeor requiere sexo biológico "
            "masculino o femenino. Configure el perfil o use otra fórmula."
        ],
    )


def factor_actividad(
    act: ActividadHabitual,
) -> tuple[Optional[float], list[str]]:
    """Deriva un factor estándar a partir de los datos disponibles.

    Nunca inventa un nivel alto si no hay datos.
    """
    notas: list[str] = []
    gim = act.frecuencia_gimnasio_semanal
    pasos = act.pasos_diarios_promedio
    horas_lab = act.horas_actividad_laboral
    pie = act.tiempo_de_pie_h

    if gim is None and pasos is None and horas_lab is None and pie is None:
        return None, ["Faltan datos de actividad para estimar el factor."]

    if gim is not None and gim >= 5 and pasos is not None and pasos >= 10000:
        notas.append(f"Factor 1.725: {gim} sesiones/semana y {pasos} pasos/día.")
        return 1.725, notas

    if (gim is not None and gim >= 3) or (pasos is not None and pasos >= 10000):
        partes: list[str] = []
        if gim is not None and gim >= 3:
            partes.append(f"{gim} sesiones/semana")
        if pasos is not None and pasos >= 10000:
            partes.append(f"{pasos} pasos/día")
        notas.append(f"Factor 1.55: {', '.join(partes)}.")
        return 1.55, notas

    if (gim is not None and gim >= 1) or (pasos is not None and pasos >= 7000):
        partes = []
        if gim is not None and gim >= 1:
            partes.append(f"{gim} sesiones/semana")
        if pasos is not None and pasos >= 7000:
            partes.append(f"{pasos} pasos/día")
        notas.append(f"Factor 1.375: {', '.join(partes)}.")
        return 1.375, notas

    if horas_lab is not None and horas_lab >= 4 and pie is not None and pie >= 4:
        notas.append(
            f"Factor 1.375: {horas_lab} h de trabajo y {pie} h de pie."
        )
        return 1.375, notas

    notas.append(
        "Factor 1.2: datos de actividad insuficientes para un nivel superior. "
        "Se asume sedentario de forma conservadora."
    )
    return 1.2, notas


def calcular_tdee(perfil: Perfil, act: ActividadHabitual) -> TDEEEstimado:
    """BMR * factor_actividad. Si falta cualquiera, TDEE None con nota."""
    bmr_res = calcular_bmr(perfil)
    factor, notas_f = factor_actividad(act)

    notas = list(bmr_res.notas) + notas_f

    if bmr_res.bmr_kcal is None and factor is None:
        return TDEEEstimado(
            bmr_kcal=None,
            factor_actividad=None,
            tdee_kcal=None,
            fuente=Fuente.DESCONOCIDO,
            notas=notas,
        )
    if bmr_res.bmr_kcal is None:
        return TDEEEstimado(
            bmr_kcal=None,
            factor_actividad=factor,
            tdee_kcal=None,
            fuente=Fuente.PARCIAL,
            notas=notas,
        )
    if factor is None:
        return TDEEEstimado(
            bmr_kcal=bmr_res.bmr_kcal,
            factor_actividad=None,
            tdee_kcal=None,
            fuente=Fuente.PARCIAL,
            notas=notas,
        )
    return TDEEEstimado(
        bmr_kcal=bmr_res.bmr_kcal,
        factor_actividad=factor,
        tdee_kcal=bmr_res.bmr_kcal * factor,
        fuente=Fuente.CALCULADO,
        notas=notas,
    )