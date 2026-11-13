"""Esquema de operaciones que el modelo puede proponer.

Validación estricta con Pydantic. No ejecuta: solo valida forma.
La ejecución la hace el bucle conversacional en app/agent/loop.py.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from app.models.domain import Unidad


class _BaseOp(BaseModel):
    model_config = {"extra": "forbid"}


class AgregarItemOp(_BaseOp):
    tipo: Literal["agregar_item"]
    alimento_id: str = Field(min_length=1)
    cantidad: float = Field(gt=0.0, le=10000.0)
    unidad: Unidad = Unidad.G
    etiqueta: Optional[str] = Field(default=None, max_length=40)
    fecha: Optional[str] = None


class AgregarRecetaOp(_BaseOp):
    tipo: Literal["agregar_receta"]
    receta_id: str = Field(min_length=1)
    cantidad: float = Field(gt=0.0, le=1000.0)
    unidad: Unidad = Unidad.PORCION
    etiqueta: Optional[str] = Field(default=None, max_length=40)
    fecha: Optional[str] = None


class EliminarItemOp(_BaseOp):
    tipo: Literal["eliminar_item"]
    indice: int = Field(ge=1, le=1000)
    fecha: Optional[str] = None


class ConsultarTotalesOp(_BaseOp):
    tipo: Literal["consultar_totales"]
    fecha: Optional[str] = None


class ListarItemsOp(_BaseOp):
    tipo: Literal["listar_items"]
    fecha: Optional[str] = None


class ConsultarAlimentosOp(_BaseOp):
    tipo: Literal["consultar_alimentos"]
    texto: str = Field(min_length=1, max_length=80)


class ResponderOp(_BaseOp):
    tipo: Literal["responder"]
    mensaje: str = Field(min_length=1, max_length=2000)


Operacion = Annotated[
    Union[
        AgregarItemOp,
        AgregarRecetaOp,
        EliminarItemOp,
        ConsultarTotalesOp,
        ListarItemsOp,
        ConsultarAlimentosOp,
        ResponderOp,
    ],
    Field(discriminator="tipo"),
]

_OPERACION_ADAPTER = TypeAdapter(Operacion)


class OperacionInvalida(ValueError):
    """El JSON no encaja con ninguna operación soportada."""


def validar_operacion(raw: dict) -> Operacion:
    """Valida un dict contra el esquema de operaciones.

    Lanza OperacionInvalida con el detalle de Pydantic si no encaja.
    """
    if not isinstance(raw, dict):
        raise OperacionInvalida(f"Se esperaba un objeto, recibido {type(raw).__name__}.")
    try:
        return _OPERACION_ADAPTER.validate_python(raw)
    except ValidationError as exc:
        raise OperacionInvalida(str(exc)) from exc


def parsear_fecha(valor: Optional[str], *, hoy: Optional[date] = None) -> date:
    """Resuelve el campo `fecha` de una operación.

    - None -> hoy (o `hoy` si se pasa para tests).
    - "ayer", "hoy", "hoy -1d", "YYYY-MM-DD" -> fecha resultante.
    - Valida rango: 2000-01-01 <= fecha <= hoy + 1 día.
    - Lanza OperacionInvalida si no es parseable o está fuera de rango.
    """
    base = hoy or date.today()
    if valor is None or valor == "":
        return base
    v = valor.strip().lower()
    if v == "hoy":
        f = base
    elif v == "ayer":
        from datetime import timedelta
        f = base - timedelta(days=1)
    else:
        try:
            f = date.fromisoformat(v)
        except ValueError as exc:
            raise OperacionInvalida(
                f"Fecha no parseable: {valor!r}. Usa YYYY-MM-DD, 'hoy' o 'ayer'."
            ) from exc
    from datetime import timedelta
    if f < date(2000, 1, 1):
        raise OperacionInvalida(f"Fecha demasiado antigua: {f.isoformat()}")
    if f > base + timedelta(days=1):
        raise OperacionInvalida(f"Fecha futura no permitida: {f.isoformat()}")
    return f