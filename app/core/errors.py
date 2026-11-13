"""Errores de dominio del motor nutricional."""

from __future__ import annotations


class NutritionError(Exception):
    """Error de datos o de cálculo nutricional."""


class UnidadIncompatible(NutritionError):
    """No se puede convertir la unidad solicitada a la base del alimento."""


class ReferenciaInexistente(NutritionError):
    """El id de alimento o receta no existe en la bóveda."""