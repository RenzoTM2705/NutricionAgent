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

class EditarItemOp(_BaseOp):
    tipo: Literal["editar_item"]
    indice: int = Field(ge=1, le=1000)
    cantidad: Optional[float] = Field(default=None, gt=0.0, le=10000.0)
    unidad: Optional[Unidad] = None
    etiqueta: Optional[str] = Field(default=None, max_length=40)
    fecha: Optional[str] = None

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if self.cantidad is None and self.unidad is None and self.etiqueta is None:
            raise ValueError(
                "editar_item requiere al menos uno de: cantidad, unidad, etiqueta."
            )
        


class ConsultarTotalesOp(_BaseOp):
    tipo: Literal["consultar_totales"]
    fecha: Optional[str] = None


class ListarItemsOp(_BaseOp):
    tipo: Literal["listar_items"]
    fecha: Optional[str] = None


class ConsultarAlimentosOp(_BaseOp):
    tipo: Literal["consultar_alimentos"]
    texto: str = Field(min_length=1, max_length=80)

class AltaAlimentoOp(_BaseOp):
    tipo: Literal["alta_alimento"]
    id: str = Field(min_length=1, max_length=80)
    nombre: str = Field(min_length=1, max_length=120)
    marca: Optional[str] = Field(default=None, max_length=120)
    unidad_base: Unidad = Unidad.G
    peso_referencia_g: Optional[float] = Field(default=None, gt=0.0, le=5000.0)
    kcal_por_100: Optional[float] = Field(default=None, ge=0.0, le=2000.0)
    proteina_g_por_100: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    grasa_g_por_100: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    carbo_g_por_100: Optional[float] = Field(default=None, ge=0.0, le=200.0)
    fuente: Optional[str] = Field(default=None, max_length=200)
    notas: Optional[str] = Field(default=None, max_length=1000)

class RegistrarActividadOp(_BaseOp):
    tipo: Literal["registrar_actividad"]
    horas_trabajo: Optional[float] = Field(default=None, ge=0.0, le=24.0)
    horas_de_pie: Optional[float] = Field(default=None, ge=0.0, le=24.0)
    pasos: Optional[int] = Field(default=None, ge=0, le=100000)
    gimnasio: Optional[bool] = None
    gimnasio_duracion_min: Optional[int] = Field(default=None, ge=0, le=600)
    tipo_entrenamiento: Optional[str] = Field(default=None, max_length=120)
    otros_deportes: Optional[str] = Field(default=None, max_length=200)
    notas: Optional[str] = Field(default=None, max_length=1000)
    fecha: Optional[str] = None

    def model_post_init(self, __context) -> None:  # type: ignore[override]
        if not any(
            v is not None
            for v in (
                self.horas_trabajo,
                self.horas_de_pie,
                self.pasos,
                self.gimnasio,
                self.gimnasio_duracion_min,
                self.tipo_entrenamiento,
                self.otros_deportes,
                self.notas,
            )
        ):
            raise ValueError(
                "registrar_actividad requiere al menos un campo de actividad."
            )

class ResponderOp(_BaseOp):
    tipo: Literal["responder"]
    mensaje: str = Field(min_length=1, max_length=2000)


Operacion = Annotated[
    Union[
        AgregarItemOp,
        AgregarRecetaOp,
        EliminarItemOp,
        EditarItemOp,
        ConsultarTotalesOp,
        ListarItemsOp,
        ConsultarAlimentosOp,
        AltaAlimentoOp,
        RegistrarActividadOp,
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