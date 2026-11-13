"""Tipos de resultado del motor nutricional.

Reglas:
- Los nutrientes desconocidos son None, nunca 0.
- `fuente` indica la procedencia del resultado.
- `notas` explica por qué un resultado es parcial o desconocido.
- Todos los modelos son estrictos (extra="forbid").
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.models.domain import Unidad


class Fuente(str, Enum):
    CALCULADO = "calculado"
    ESTIMADO = "estimado"
    PARCIAL = "parcial"
    DESCONOCIDO = "desconocido"
    PENDIENTE = "pendiente"


class Nutrientes(BaseModel):
    model_config = {"extra": "forbid"}

    kcal: Optional[float] = Field(default=None, ge=0.0)
    proteina_g: Optional[float] = Field(default=None, ge=0.0)
    grasa_g: Optional[float] = Field(default=None, ge=0.0)
    carbo_g: Optional[float] = Field(default=None, ge=0.0)


class ItemCalculado(BaseModel):
    """Resultado del cálculo de un ItemComida o de un IngredienteReceta."""

    model_config = {"extra": "forbid"}

    ref_tipo: Literal["alimento", "receta"]
    ref_id: str
    cantidad: float = Field(gt=0.0)
    unidad: Unidad
    nutrientes: Nutrientes
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)


class RecetaCalculada(BaseModel):
    model_config = {"extra": "forbid"}

    receta_id: str
    rendimiento_porciones: float = Field(gt=0.0)
    total: Nutrientes
    por_porcion: Nutrientes
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)


class TotalesDia(BaseModel):
    model_config = {"extra": "forbid"}

    fecha: date
    items: list[ItemCalculado] = Field(default_factory=list)
    total: Nutrientes
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)


class TDEEEstimado(BaseModel):
    model_config = {"extra": "forbid"}

    bmr_kcal: Optional[float] = Field(default=None, ge=0.0)
    factor_actividad: Optional[float] = Field(default=None, gt=0.0)
    tdee_kcal: Optional[float] = Field(default=None, ge=0.0)
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)


class BalanceDiario(BaseModel):
    model_config = {"extra": "forbid"}

    fecha: date
    consumo_kcal: Optional[float] = Field(default=None, ge=0.0)
    gasto_kcal: Optional[float] = Field(default=None, ge=0.0)
    balance_kcal: Optional[float] = None
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)