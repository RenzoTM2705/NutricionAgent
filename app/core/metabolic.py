"""Fórmulas metabólicas: BMR (Mifflin-St Jeor), factor de actividad, TDEE.

Sin IA. Funciones puras sobre datos validados del perfil y la actividad.
"""

from __future__ import annotations

from typing import Optional

from app.core.results import Fuente, TDEEEstimado
from app.models.domain import ActividadDia, ActividadHabitual, Perfil, Sexo

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

def _factor_actividad_dia(act: ActividadDia) -> tuple[Optional[float], list[str]]:
    """Deriva un factor de actividad a partir de los datos del día.

    Reglas conservadoras, en orden. No inventa nivel alto si faltan datos.
    """
    notas: list[str] = []
    gim = bool(act.gimnasio) if act.gimnasio is not None else False
    dur = act.gimnasio_duracion_min
    pasos = act.pasos
    h_trab = act.horas_trabajo
    h_pie = act.horas_de_pie

    if gim and (dur is not None and dur >= 60) and (pasos is not None and pasos >= 10000):
        notas.append(
            f"Factor 1.725: gimnasio {dur} min y {pasos} pasos."
        )
        return 1.725, notas
    if (pasos is not None and pasos >= 10000) or (
        gim and dur is not None and dur >= 45
    ):
        partes: list[str] = []
        if pasos is not None and pasos >= 10000:
            partes.append(f"{pasos} pasos")
        if gim and dur is not None and dur >= 45:
            partes.append(f"gimnasio {dur} min")
        notas.append(f"Factor 1.55: {', '.join(partes)}.")
        return 1.55, notas
    if gim or (pasos is not None and pasos >= 8000):
        partes = []
        if gim:
            partes.append("gimnasio")
        if pasos is not None and pasos >= 8000:
            partes.append(f"{pasos} pasos")
        notas.append(f"Factor 1.375: {', '.join(partes)}.")
        return 1.375, notas
    if h_trab is not None and h_trab >= 6 and h_pie is not None and h_pie >= 4:
        notas.append(f"Factor 1.375: {h_trab} h trabajo y {h_pie} h de pie.")
        return 1.375, notas
    if h_trab is not None and h_trab >= 4 and h_pie is not None and h_pie >= 2:
        notas.append(f"Factor 1.375: {h_trab} h trabajo y {h_pie} h de pie.")
        return 1.375, notas
    if any(
        v is not None
        for v in (act.horas_trabajo, act.horas_de_pie, act.pasos, act.gimnasio)
    ):
        notas.append(
            "Factor 1.2: datos del día insuficientes para un nivel superior. "
            "Se asume sedentario de forma conservadora."
        )
        return 1.2, notas
    return None, ["Sin datos de actividad del día."]


def calcular_tdee_dia(
    perfil: Perfil,
    actividad_habitual: Optional[ActividadHabitual] = None,
    actividad_dia: Optional[ActividadDia] = None,
) -> TDEEEstimado:
    """TDEE usando actividad del día si existe, si no la habitual.

    - Actividad del día -> factor diario, fuente CALCULADO.
    - Sin día pero con habitual -> factor habitual, fuente PARCIAL + nota.
    - Sin ninguna -> fuente DESCONOCIDO.
    - BMR siempre desde perfil; si no se puede, fuente PARCIAL/DESCONOCIDO.
    """
    bmr_res = calcular_bmr(perfil)
    notas = list(bmr_res.notas)

    factor: Optional[float] = None
    fuente_actividad: Optional[Fuente] = None

    if actividad_dia is not None:
        factor, notas_dia = _factor_actividad_dia(actividad_dia)
        notas.extend(notas_dia)
        if factor is not None:
            fuente_actividad = Fuente.CALCULADO
    elif actividad_habitual is not None:
        factor, notas_hab = factor_actividad(actividad_habitual)
        notas.extend(notas_hab)
        if factor is not None:
            notas.append("Usando actividad habitual (no del día).")
            fuente_actividad = Fuente.PARCIAL

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

    # Ambos existen
    if fuente_actividad == Fuente.CALCULADO:
        fuente = Fuente.CALCULADO
    else:
        fuente = Fuente.PARCIAL

    return TDEEEstimado(
        bmr_kcal=bmr_res.bmr_kcal,
        factor_actividad=factor,
        tdee_kcal=bmr_res.bmr_kcal * factor,
        fuente=fuente,
        notas=notas,
    )