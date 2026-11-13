"""Conversión de unidades a la base del alimento.

Reglas:
- Solo se convierte al mismo tipo de base: g↔g, ml↔ml.
- unidad/porcion → g requieren peso_referencia_g.
- No se inventan densidades: g↔ml lanza UnidadIncompatible.
- Sin redondeo. Sin valores por defecto.
"""

from __future__ import annotations

import math

from app.core.errors import NutritionError, UnidadIncompatible
from app.models.domain import Alimento, Unidad


def _check_cantidad(cantidad: float) -> None:
    if not isinstance(cantidad, (int, float)) or isinstance(cantidad, bool):
        raise NutritionError(f"Cantidad no numérica: {cantidad!r}")
    if not math.isfinite(cantidad):
        raise NutritionError(f"Cantidad no finita: {cantidad!r}")
    if cantidad <= 0:
        raise NutritionError(f"Cantidad debe ser > 0, recibido {cantidad!r}")


def convertir_a_gramos(
    cantidad: float,
    unidad: Unidad,
    alimento: Alimento,
) -> float:
    """Convierte `cantidad` en `unidad` a gramos según el alimento.

    - g → g
    - unidad/porcion → g (requiere peso_referencia_g)
    - ml → g: UnidadIncompatible (no inventamos densidad)
    - Si el alimento es base ml y se pide gramos: UnidadIncompatible.
    """
    _check_cantidad(cantidad)

    if alimento.unidad_base == Unidad.ML:
        raise UnidadIncompatible(
            f"El alimento {alimento.id!r} tiene base ml; no se puede convertir "
            f"a gramos sin densidad explícita."
        )

    if unidad == Unidad.G:
        return float(cantidad)

    if unidad in (Unidad.UNIDAD, Unidad.PORCION):
        if alimento.peso_referencia_g is None:
            raise UnidadIncompatible(
                f"El alimento {alimento.id!r} no tiene peso_referencia_g; "
                f"no se puede convertir {unidad.value} a gramos."
            )
        return float(cantidad) * float(alimento.peso_referencia_g)

    if unidad == Unidad.ML:
        raise UnidadIncompatible(
            f"No se convierte ml a gramos sin densidad explícita "
            f"(alimento {alimento.id!r})."
        )

    raise UnidadIncompatible(f"Unidad no soportada: {unidad!r}")


def convertir_a_mililitros(
    cantidad: float,
    unidad: Unidad,
    alimento: Alimento,
) -> float:
    """Análoga para alimentos con base ml.

    - ml → ml
    - unidad/porcion → ml (requiere peso_referencia_g, interpretado como ml
      de referencia; solo si el alimento lo declara así)
    - g → ml: UnidadIncompatible.
    """
    _check_cantidad(cantidad)

    if alimento.unidad_base == Unidad.G:
        raise UnidadIncompatible(
            f"El alimento {alimento.id!r} tiene base g; no se puede convertir "
            f"a mililitros sin densidad explícita."
        )

    if unidad == Unidad.ML:
        return float(cantidad)

    if unidad in (Unidad.UNIDAD, Unidad.PORCION):
        if alimento.peso_referencia_g is None:
            raise UnidadIncompatible(
                f"El alimento {alimento.id!r} no tiene peso_referencia_g; "
                f"no se puede convertir {unidad.value} a mililitros."
            )
        # peso_referencia_g en un alimento base ml se interpreta como ml de referencia.
        return float(cantidad) * float(alimento.peso_referencia_g)

    if unidad == Unidad.G:
        raise UnidadIncompatible(
            f"No se convierte g a mililitros sin densidad explícita "
            f"(alimento {alimento.id!r})."
        )

    raise UnidadIncompatible(f"Unidad no soportada: {unidad!r}")