"""Modelos de reporte (diario, semanal, mensual).

Solo estructura y validación. El cálculo vive en app/core/reports.py.
El almacenamiento (Markdown) vive en app/storage/vault.py.

Reglas:
- Nutrientes desconocidos: None, nunca 0.
- Promedios sobre días con datos; días sin datos no cuentan como 0.
- Fuente explícita: calculado, parcial, desconocido, pendiente.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.core.results import Fuente, Nutrientes
from app.models.domain import Unidad


class ItemResumen(BaseModel):
    """Resumen de un item en el reporte diario."""

    model_config = {"extra": "forbid"}

    indice: int = Field(ge=1)
    ref_tipo: Literal["alimento", "receta"]
    ref_id: str
    cantidad: float = Field(gt=0.0)
    unidad: Unidad
    etiqueta: Optional[str] = None
    kcal: Optional[float] = Field(default=None, ge=0.0)
    proteina_g: Optional[float] = Field(default=None, ge=0.0)
    grasa_g: Optional[float] = Field(default=None, ge=0.0)
    carbo_g: Optional[float] = Field(default=None, ge=0.0)


class BalanceResumen(BaseModel):
    model_config = {"extra": "forbid"}

    consumo_kcal: Optional[float] = Field(default=None, ge=0.0)
    gasto_kcal: Optional[float] = Field(default=None, ge=0.0)
    balance_kcal: Optional[float] = None
    fuente: Fuente


class ReporteDiario(BaseModel):
    model_config = {"extra": "forbid"}

    fecha: date
    items: list[ItemResumen] = Field(default_factory=list)
    totales: Nutrientes
    balance: BalanceResumen
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)


class Comparacion(BaseModel):
    """Comparación de un valor con el periodo anterior."""

    model_config = {"extra": "forbid"}

    valor_actual: Optional[float] = None
    valor_anterior: Optional[float] = None
    diferencia: Optional[float] = None
    notas: list[str] = Field(default_factory=list)


class ReporteSemanal(BaseModel):
    model_config = {"extra": "forbid"}

    desde: date
    hasta: date
    dias_con_datos: int = Field(ge=0)
    dias_sin_datos: int = Field(ge=0)
    dias_entrenados: int = Field(default=0, ge=0)
    promedios: Nutrientes
    balance_promedio: BalanceResumen
    comparacion_kcal: Optional[Comparacion] = None
    comparacion_peso: Optional[Comparacion] = None
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)


class ReporteMensual(BaseModel):
    model_config = {"extra": "forbid"}

    desde: date
    hasta: date
    dias_con_datos: int = Field(ge=0)
    dias_sin_datos: int = Field(ge=0)
    dias_entrenados: int = Field(default=0, ge=0)
    consistencia_pct: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    promedios: Nutrientes
    balance_promedio: BalanceResumen
    comparacion_kcal: Optional[Comparacion] = None
    comparacion_peso: Optional[Comparacion] = None
    fuente: Fuente
    notas: list[str] = Field(default_factory=list)