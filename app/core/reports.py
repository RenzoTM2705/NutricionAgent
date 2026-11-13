"""Cálculo de reportes diario, semanal y mensual.

Solo lectura de la bóveda y cálculos deterministas. Sin escritura.
La persistencia está en app/storage/vault.py.

Reglas:
- Días sin datos no cuentan como 0.
- Promedios solo sobre días con datos.
- Si falta un nutriente en algún día con datos, el promedio es None.
- Fuente explícita: calculado, parcial, desconocido.
"""

from __future__ import annotations

from calendar import monthrange
from datetime import date, timedelta
from typing import Optional

from app.core.nutrition import calcular_balance, calcular_totales_dia
from app.core.report_models import (
    BalanceResumen,
    Comparacion,
    ItemResumen,
    ReporteDiario,
    ReporteMensual,
    ReporteSemanal,
)
from app.core.results import Fuente, Nutrientes
from app.storage.vault import Vault


def _nutrientes_desde_totales(t) -> Nutrientes:
    return Nutrientes(
        kcal=t.total.kcal,
        proteina_g=t.total.proteina_g,
        grasa_g=t.total.grasa_g,
        carbo_g=t.total.carbo_g,
    )


def _items_resumen(items_calc, registro) -> list[ItemResumen]:
    out: list[ItemResumen] = []
    for idx, (it, orig) in enumerate(zip(items_calc, registro.items), start=1):
        out.append(
            ItemResumen(
                indice=idx,
                ref_tipo=it.ref_tipo,
                ref_id=it.ref_id,
                cantidad=it.cantidad,
                unidad=it.unidad,
                etiqueta=orig.etiqueta,
                kcal=it.nutrientes.kcal,
                proteina_g=it.nutrientes.proteina_g,
                grasa_g=it.nutrientes.grasa_g,
                carbo_g=it.nutrientes.carbo_g,
            )
        )
    return out


def generar_reporte_diario(fecha: date, vault: Vault) -> ReporteDiario:
    """Reporte del día `fecha`. Si no hay registro, devuelve vacío con nota."""
    registro = vault.read_registro(fecha)
    if registro is None or not registro.items:
        return ReporteDiario(
            fecha=fecha,
            items=[],
            totales=Nutrientes(),
            balance=BalanceResumen(fuente=Fuente.PENDIENTE),
            fuente=Fuente.DESCONOCIDO,
            notas=["Sin registro para este día."],
        )

    totales = calcular_totales_dia(registro, vault)
    perfil = vault.read_perfil()
    actividad = vault.read_actividad()
    if perfil is not None:
        balance = calcular_balance(
            registro, perfil, actividad or _vacia_actividad(), vault
        )
        bal_res = BalanceResumen(
            consumo_kcal=balance.consumo_kcal,
            gasto_kcal=balance.gasto_kcal,
            balance_kcal=balance.balance_kcal,
            fuente=balance.fuente,
        )
        fuente = balance.fuente
        notas = list(balance.notas)
    else:
        bal_res = BalanceResumen(fuente=Fuente.PENDIENTE)
        fuente = Fuente.PARCIAL
        notas = ["Sin perfil configurado; no se calcula balance."]

    return ReporteDiario(
        fecha=fecha,
        items=_items_resumen(totales.items, registro),
        totales=_nutrientes_desde_totales(totales),
        balance=bal_res,
        fuente=fuente,
        notas=notas,
    )


def _vacia_actividad():
    from app.models.domain import ActividadHabitual
    return ActividadHabitual()


def _recolectar_dias(
    desde: date, hasta: date, vault: Vault
) -> list[tuple[date, object, object, object]]:
    """Devuelve [(fecha, registro, totales, balance), ...] para días con items."""
    out = []
    perfil = vault.read_perfil()
    actividad = vault.read_actividad() or _vacia_actividad()
    cur = desde
    while cur <= hasta:
        reg = vault.read_registro(cur)
        if reg is not None and reg.items:
            tot = calcular_totales_dia(reg, vault)
            if perfil is not None:
                bal = calcular_balance(reg, perfil, actividad, vault)
            else:
                bal = None
            out.append((cur, reg, tot, bal))
        cur += timedelta(days=1)
    return out


def _promedio(vals: list[Optional[float]]) -> Optional[float]:
    if any(v is None for v in vals) or not vals:
        return None
    return sum(vals) / len(vals)  # type: ignore[arg-type]


def _promedios(dias) -> tuple[Nutrientes, list[str]]:
    notas: list[str] = []
    if not dias:
        return Nutrientes(), ["Sin días con datos."]
    kcal = _promedio([t.total.kcal for _, _, t, _ in dias])
    prot = _promedio([t.total.proteina_g for _, _, t, _ in dias])
    grasa = _promedio([t.total.grasa_g for _, _, t, _ in dias])
    carb = _promedio([t.total.carbo_g for _, _, t, _ in dias])
    if kcal is None and any(t.total.kcal is not None for _, _, t, _ in dias):
        notas.append("Promedio de kcal no calculable: algún día sin dato.")
    return Nutrientes(kcal=kcal, proteina_g=prot, grasa_g=grasa, carbo_g=carb), notas


def _balance_promedio(dias) -> tuple[BalanceResumen, list[str]]:
    notas: list[str] = []
    con_bal = [b for _, _, _, b in dias if b is not None]
    if not con_bal:
        return BalanceResumen(fuente=Fuente.DESCONOCIDO), ["Sin datos de balance."]
    consumos = [b.consumo_kcal for b in con_bal]
    gastos = [b.gasto_kcal for b in con_bal]
    balances = [b.balance_kcal for b in con_bal]
    fuentes = [b.fuente for b in con_bal]
    if any(v is None for v in consumos) or any(v is None for v in gastos) or any(v is None for v in balances):
        # Promedio parcial: solo sobre los días con valores completos
        consumos_ok = [v for v in consumos if v is not None]
        gastos_ok = [v for v in gastos if v is not None]
        balances_ok = [v for v in balances if v is not None]
        c = sum(consumos_ok) / len(consumos_ok) if consumos_ok else None
        g = sum(gastos_ok) / len(gastos_ok) if gastos_ok else None
        b = sum(balances_ok) / len(balances_ok) if balances_ok else None
        notas.append("Balance promedio calculado solo sobre días completos.")
        fuente = Fuente.PARCIAL
    else:
        c = sum(consumos) / len(consumos)  # type: ignore[arg-type]
        g = sum(gastos) / len(gastos)  # type: ignore[arg-type]
        b = sum(balances) / len(balances)  # type: ignore[arg-type]
        fuente = Fuente.CALCULADO if all(f == Fuente.CALCULADO for f in fuentes) else Fuente.PARCIAL
    return BalanceResumen(
        consumo_kcal=c, gasto_kcal=g, balance_kcal=b, fuente=fuente
    ), notas


def _fuente_global(dias) -> Fuente:
    if not dias:
        return Fuente.DESCONOCIDO
    fuentes = [t.fuente for _, _, t, _ in dias]
    if all(f == Fuente.CALCULADO for f in fuentes):
        return Fuente.CALCULADO
    return Fuente.PARCIAL


def generar_reporte_semanal(desde: date, hasta: date, vault: Vault) -> ReporteSemanal:
    """Reporte de [desde, hasta] con comparación a la semana anterior."""
    if hasta < desde:
        desde, hasta = hasta, desde
    dias = _recolectar_dias(desde, hasta, vault)
    total_dias = (hasta - desde).days + 1
    dias_con = len(dias)
    dias_sin = total_dias - dias_con

    promedios, notas_p = _promedios(dias)
    bal, notas_b = _balance_promedio(dias)
    fuente = _fuente_global(dias)

    dias_entrenados = sum(
        1 for _, reg, _, _ in dias
        if reg.actividad_dia and reg.actividad_dia.gimnasio
    )

    # Comparación con la semana anterior
    desde_ant = desde - timedelta(days=7)
    hasta_ant = hasta - timedelta(days=7)
    dias_ant = _recolectar_dias(desde_ant, hasta_ant, vault)
    comparacion_kcal: Optional[Comparacion] = None
    if dias_ant:
        prom_ant, _ = _promedios(dias_ant)
        if promedios.kcal is not None and prom_ant.kcal is not None:
            comparacion_kcal = Comparacion(
                valor_actual=promedios.kcal,
                valor_anterior=prom_ant.kcal,
                diferencia=promedios.kcal - prom_ant.kcal,
            )
        else:
            comparacion_kcal = Comparacion(
                valor_actual=promedios.kcal,
                valor_anterior=prom_ant.kcal,
                diferencia=None,
                notas=["Comparación no calculable por datos faltantes."],
            )
    else:
        comparacion_kcal = Comparacion(
            valor_actual=promedios.kcal,
            notas=["Sin datos de la semana anterior."],
        )

    return ReporteSemanal(
        desde=desde,
        hasta=hasta,
        dias_con_datos=dias_con,
        dias_sin_datos=dias_sin,
        dias_entrenados=dias_entrenados,
        promedios=promedios,
        balance_promedio=bal,
        comparacion_kcal=comparacion_kcal,
        comparacion_peso=None,
        fuente=fuente,
        notas=notas_p + notas_b + ["Sin histórico de peso disponible."],
    )


def generar_reporte_mensual(anio: int, mes: int, vault: Vault) -> ReporteMensual:
    """Reporte del mes natural `anio`-`mes` con comparación al mes anterior."""
    if mes < 1 or mes > 12:
        raise ValueError(f"Mes fuera de rango: {mes}")
    _, dias_mes = monthrange(anio, mes)
    desde = date(anio, mes, 1)
    hasta = date(anio, mes, dias_mes)
    dias = _recolectar_dias(desde, hasta, vault)
    dias_con = len(dias)
    dias_sin = dias_mes - dias_con
    consistencia = round(100.0 * dias_con / dias_mes, 1) if dias_mes else None

    promedios, notas_p = _promedios(dias)
    bal, notas_b = _balance_promedio(dias)
    fuente = _fuente_global(dias)

    dias_entrenados = sum(
        1 for _, reg, _, _ in dias
        if reg.actividad_dia and reg.actividad_dia.gimnasio
    )

    # Mes anterior
    if mes == 1:
        anio_ant, mes_ant = anio - 1, 12
    else:
        anio_ant, mes_ant = anio, mes - 1
    _, dias_mes_ant = monthrange(anio_ant, mes_ant)
    desde_ant = date(anio_ant, mes_ant, 1)
    hasta_ant = date(anio_ant, mes_ant, dias_mes_ant)
    dias_ant = _recolectar_dias(desde_ant, hasta_ant, vault)
    comparacion_kcal: Optional[Comparacion] = None
    if dias_ant:
        prom_ant, _ = _promedios(dias_ant)
        if promedios.kcal is not None and prom_ant.kcal is not None:
            comparacion_kcal = Comparacion(
                valor_actual=promedios.kcal,
                valor_anterior=prom_ant.kcal,
                diferencia=promedios.kcal - prom_ant.kcal,
            )
        else:
            comparacion_kcal = Comparacion(
                valor_actual=promedios.kcal,
                valor_anterior=prom_ant.kcal,
                diferencia=None,
                notas=["Comparación no calculable por datos faltantes."],
            )
    else:
        comparacion_kcal = Comparacion(
            valor_actual=promedios.kcal,
            notas=["Sin datos del mes anterior."],
        )

    return ReporteMensual(
        desde=desde,
        hasta=hasta,
        dias_con_datos=dias_con,
        dias_sin_datos=dias_sin,
        dias_entrenados=dias_entrenados,
        consistencia_pct=consistencia,
        promedios=promedios,
        balance_promedio=bal,
        comparacion_kcal=comparacion_kcal,
        comparacion_peso=None,
        fuente=fuente,
        notas=notas_p + notas_b + ["Sin histórico de peso disponible."],
    )