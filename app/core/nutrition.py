"""Motor nutricional: cálculo por item, totales diarios, recetas y balance.

Sin IA. Solo funciones puras sobre datos validados.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.core.metabolic import calcular_tdee_dia

from app.core.errors import ReferenciaInexistente, UnidadIncompatible
from app.core.results import (
    BalanceDiario,
    Fuente,
    ItemCalculado,
    Nutrientes,
    RecetaCalculada,
    TDEEEstimado,
    TotalesDia,
)
from app.core.units import convertir_a_gramos, convertir_a_mililitros
from app.models.domain import (
    Alimento,
    IngredienteReceta,
    ItemComida,
    Receta,
    RegistroDiario,
    Unidad,
)
from app.storage.vault import Vault


# ---------------------------------------------------------------------------
# Helpers internos
# ---------------------------------------------------------------------------
def _nutriente_escalado(
    valor_por_100: Optional[float],
    factor: float,
) -> Optional[float]:
    if valor_por_100 is None:
        return None
    return valor_por_100 * factor


def _resumen_fuente(valores: list[Optional[float]]) -> Fuente:
    """Calcula la fuente a partir de los nutrientes obtenidos.

    - Todos None -> DESCONOCIDO
    - Alguno None -> PARCIAL
    - Todos no None -> CALCULADO
    """
    n_none = sum(1 for v in valores if v is None)
    if n_none == len(valores):
        return Fuente.DESCONOCIDO
    if n_none > 0:
        return Fuente.PARCIAL
    return Fuente.CALCULADO


def _calcular_desde_alimento(
    cantidad: float,
    unidad: Unidad,
    alimento: Alimento,
) -> ItemCalculado:
    notas: list[str] = []

    if alimento.unidad_base == Unidad.G:
        base = convertir_a_gramos(cantidad, unidad, alimento)
    elif alimento.unidad_base == Unidad.ML:
        base = convertir_a_mililitros(cantidad, unidad, alimento)
    else:
        raise UnidadIncompatible(
            f"Unidad base no soportada en {alimento.id!r}: {alimento.unidad_base!r}"
        )

    factor = base / 100.0

    kcal = _nutriente_escalado(alimento.kcal_por_100, factor)
    prot = _nutriente_escalado(alimento.proteina_g_por_100, factor)
    grasa = _nutriente_escalado(alimento.grasa_g_por_100, factor)
    carb = _nutriente_escalado(alimento.carbo_g_por_100, factor)

    valores = [kcal, prot, grasa, carb]
    fuente = _resumen_fuente(valores)

    if kcal is None:
        notas.append(f"kcal desconocidas en alimento {alimento.id!r}")
    if prot is None:
        notas.append(f"proteína desconocida en alimento {alimento.id!r}")
    if grasa is None:
        notas.append(f"grasa desconocida en alimento {alimento.id!r}")
    if carb is None:
        notas.append(f"carbohidratos desconocidos en alimento {alimento.id!r}")

    return ItemCalculado(
        ref_tipo="alimento",
        ref_id=alimento.id,
        cantidad=cantidad,
        unidad=unidad,
        nutrientes=Nutrientes(kcal=kcal, proteina_g=prot, grasa_g=grasa, carbo_g=carb),
        fuente=fuente,
        notas=notas,
    )


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def calcular_item(item: ItemComida, vault: Vault) -> ItemCalculado:
    """Calcula los nutrientes de un ItemComida contra el Vault.

    - Si item.alimento_id: se calcula desde el alimento.
    - Si item.receta_id: se calcula la receta y se toma la porción
      correspondiente. Solo se soporta unidad PORCION en esta fase.
    """
    if item.alimento_id is not None:
        alimento = vault.get_alimento(item.alimento_id)
        if alimento is None:
            raise ReferenciaInexistente(
                f"No existe el alimento {item.alimento_id!r} en la bóveda."
            )
        return _calcular_desde_alimento(item.cantidad, item.unidad, alimento)

    # item.receta_id no es None (garantizado por el modelo)
    receta = vault.get_receta(item.receta_id or "")
    if receta is None:
        raise ReferenciaInexistente(
            f"No existe la receta {item.receta_id!r} en la bóveda."
        )

    if item.unidad != Unidad.PORCION:
        raise UnidadIncompatible(
            f"Para recetas, usa unidad PORCION en esta fase "
            f"(recibido {item.unidad.value!r})."
        )

    receta_calc = calcular_receta(receta, vault)
    factor = item.cantidad
    porcion = receta_calc.por_porcion

    kcal = None if porcion.kcal is None else porcion.kcal * factor
    prot = None if porcion.proteina_g is None else porcion.proteina_g * factor
    grasa = None if porcion.grasa_g is None else porcion.grasa_g * factor
    carb = None if porcion.carbo_g is None else porcion.carbo_g * factor

    notas = list(receta_calc.notas)
    fuente = receta_calc.fuente
    if fuente == Fuente.CALCULADO:
        # Recalcular porción explícita no cambia la fuente
        pass

    return ItemCalculado(
        ref_tipo="receta",
        ref_id=receta.id,
        cantidad=item.cantidad,
        unidad=item.unidad,
        nutrientes=Nutrientes(kcal=kcal, proteina_g=prot, grasa_g=grasa, carbo_g=carb),
        fuente=fuente,
        notas=notas,
    )


def calcular_ingrediente(
    ing: IngredienteReceta,
    vault: Vault,
) -> ItemCalculado:
    """Calcula los nutrientes de un IngredienteReceta."""
    alimento = vault.get_alimento(ing.alimento_id)
    if alimento is None:
        raise ReferenciaInexistente(
            f"No existe el alimento {ing.alimento_id!r} en la bóveda."
        )
    return _calcular_desde_alimento(ing.cantidad, ing.unidad, alimento)


def calcular_totales_dia(registro: RegistroDiario, vault: Vault) -> TotalesDia:
    """Suma los nutrientes de todos los items del registro.

    - Cada nutriente se suma solo si TODOS los items aportan valor.
    - Si alguno no aporta, el nutriente total queda None y la fuente es PARCIAL.
    - Si ninguno aporta, la fuente es DESCONOCIDO.
    - Sin items: fuente DESCONOCIDO con nota.
    """
    items_calc: list[ItemCalculado] = [calcular_item(it, vault) for it in registro.items]

    notas: list[str] = []
    if not items_calc:
        return TotalesDia(
            fecha=registro.fecha,
            items=[],
            total=Nutrientes(),
            fuente=Fuente.DESCONOCIDO,
            notas=["Sin items en el registro."],
        )

    def _sumar(campo: str) -> Optional[float]:
        valores = [getattr(it.nutrientes, campo) for it in items_calc]
        if any(v is None for v in valores):
            faltan = sum(1 for v in valores if v is None)
            if faltan == len(valores):
                notas.append(f"Sin datos de {campo} en ningún item.")
            else:
                notas.append(f"{faltan} item(s) sin dato de {campo}.")
            return None
        return float(sum(valores))

    kcal = _sumar("kcal")
    prot = _sumar("proteina_g")
    grasa = _sumar("grasa_g")
    carb = _sumar("carbo_g")

    valores = [kcal, prot, grasa, carb]
    fuente = _resumen_fuente(valores)

    return TotalesDia(
        fecha=registro.fecha,
        items=items_calc,
        total=Nutrientes(kcal=kcal, proteina_g=prot, grasa_g=grasa, carbo_g=carb),
        fuente=fuente,
        notas=notas,
    )

def calcular_balance(
    registro: RegistroDiario,
    perfil: Perfil,
    actividad: ActividadHabitual,
    vault: Vault,
) -> BalanceDiario:
    """Consumo (totales del día) - gasto (TDEE con actividad del día si existe).

    - Si falta consumo o gasto -> balance None, fuente PENDIENTE.
    - Si ambos existen y el TDEE es CALCULADO -> fuente CALCULADO.
    - Si ambos existen pero el TDEE es PARCIAL -> fuente PARCIAL.
    """
    totales = calcular_totales_dia(registro, vault)
    tdee = calcular_tdee_dia(perfil, actividad, registro.actividad_dia)

    notas: list[str] = []

    consumo = totales.total.kcal
    gasto = tdee.tdee_kcal

    if consumo is None:
        notas.append("Consumo no calculable: faltan datos en los items.")
        notas.extend(totales.notas)
    if gasto is None:
        notas.append("Gasto no calculable: faltan datos de perfil o actividad.")
        notas.extend(tdee.notas)

    if consumo is None or gasto is None:
        return BalanceDiario(
            fecha=registro.fecha,
            consumo_kcal=consumo,
            gasto_kcal=gasto,
            balance_kcal=None,
            fuente=Fuente.PENDIENTE,
            notas=notas,
        )

    # Determinar fuente del balance a partir del TDEE.
    if tdee.fuente == Fuente.CALCULADO:
        fuente = Fuente.CALCULADO
    else:
        # TDEE parcial (usó actividad habitual o le faltaba algo)
        fuente = Fuente.PARCIAL
        notas.append(
            f"Gasto estimado con fuente {tdee.fuente.value}; "
            f"el balance es aproximado."
        )

    return BalanceDiario(
        fecha=registro.fecha,
        consumo_kcal=consumo,
        gasto_kcal=gasto,
        balance_kcal=consumo - gasto,
        fuente=fuente,
        notas=notas,
    )

def calcular_receta(receta: Receta, vault: Vault) -> RecetaCalculada:
    """Suma los nutrientes de los ingredientes resueltos contra Vault.

    Regla estricta:
    - Si un ingrediente no existe -> ReferenciaInexistente.
    - Si un ingrediente existe pero le falta un nutriente -> ese nutriente
      total queda None y la fuente es PARCIAL, con nota del alimento_id.
    - Si no hay ingredientes -> DESCONOCIDO con nota.
    - por_porcion = total / rendimiento_porciones.
    """
    notas: list[str] = []

    if not receta.ingredientes:
        return RecetaCalculada(
            receta_id=receta.id,
            rendimiento_porciones=receta.rendimiento_porciones,
            total=Nutrientes(),
            por_porcion=Nutrientes(),
            fuente=Fuente.DESCONOCIDO,
            notas=["Receta sin ingredientes."],
        )

    items_calc: list[ItemCalculado] = [
        calcular_ingrediente(ing, vault) for ing in receta.ingredientes
    ]

    def _sumar(campo: str, etiqueta: str) -> Optional[float]:
        total = 0.0
        for it in items_calc:
            v = getattr(it.nutrientes, campo)
            if v is None:
                notas.append(
                    f"Ingrediente {it.ref_id!r} sin dato de {etiqueta}; "
                    f"total de {etiqueta} marcado como desconocido."
                )
                return None
            total += v
        return float(total)

    kcal = _sumar("kcal", "kcal")
    prot = _sumar("proteina_g", "proteína")
    grasa = _sumar("grasa_g", "grasa")
    carb = _sumar("carbo_g", "carbohidratos")

    valores = [kcal, prot, grasa, carb]
    fuente = _resumen_fuente(valores)

    total = Nutrientes(kcal=kcal, proteina_g=prot, grasa_g=grasa, carbo_g=carb)

    def _por_porcion(v: Optional[float]) -> Optional[float]:
        return None if v is None else v / receta.rendimiento_porciones

    porcion = Nutrientes(
        kcal=_por_porcion(kcal),
        proteina_g=_por_porcion(prot),
        grasa_g=_por_porcion(grasa),
        carbo_g=_por_porcion(carb),
    )

    return RecetaCalculada(
        receta_id=receta.id,
        rendimiento_porciones=receta.rendimiento_porciones,
        total=total,
        por_porcion=porcion,
        fuente=fuente,
        notas=notas,
    )