"""Lógica pura del asistente de configuración inicial.

Sin I/O de consola. Recibe respuestas y devuelve modelos validados.
Guarda con Vault solo si todo es válido.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ValidationError

from app.models.domain import (
    ActividadHabitual,
    Objetivos,
    Perfil,
    Sexo,
    Objetivo,
)
from app.storage.vault import Vault, VaultError


class SetupInput(BaseModel):
    """Respuestas del asistente. Todos los campos opcionales salvo los del perfil."""

    model_config = {"extra": "forbid"}

    # Perfil
    nombre: Optional[str] = None
    edad: Optional[int] = None
    peso_kg: Optional[float] = None
    altura_cm: Optional[float] = None
    sexo: Optional[str] = None  # "masculino" | "femenino" | "otro" | "no_especificado"
    unidad_peso: str = "kg"
    unidad_altura: str = "cm"
    objetivo: str = "mantenimiento"

    # Objetivos
    peso_objetivo_kg: Optional[float] = None
    kcal_diarias: Optional[float] = None
    proteina_g: Optional[float] = None
    grasa_g: Optional[float] = None
    carbohidratos_g: Optional[float] = None

    # Actividad
    tipo_trabajo: Optional[str] = None
    horas_actividad_laboral: Optional[float] = None
    tiempo_de_pie_h: Optional[float] = None
    movimiento_durante_trabajo: Optional[str] = None
    frecuencia_gimnasio_semanal: Optional[int] = None
    tipo_entrenamiento: Optional[str] = None
    pasos_diarios_promedio: Optional[int] = None
    otros_deportes: Optional[str] = None

    # Modelo
    modelo: Optional[str] = None


class SetupError(BaseModel):
    model_config = {"extra": "forbid"}

    campo: str
    mensaje: str


class SetupResult(BaseModel):
    model_config = {"extra": "forbid"}

    ok: bool
    errores: list[SetupError] = Field(default_factory=list)
    perfil: Optional[Perfil] = None
    objetivos: Optional[Objetivos] = None
    actividad: Optional[ActividadHabitual] = None
    modelo: Optional[str] = None
    rutas_escritas: list[str] = Field(default_factory=list)


def _sexo_from_str(value: Optional[str]) -> Sexo:
    if value is None:
        return Sexo.NO_ESPECIFICADO
    try:
        return Sexo(value)
    except ValueError:
        return Sexo.NO_ESPECIFICADO


def _objetivo_from_str(value: str) -> Objetivo:
    try:
        return Objetivo(value)
    except ValueError:
        return Objetivo.MANTENIMIENTO


def _validar_perfil(data: SetupInput) -> tuple[Optional[Perfil], list[SetupError]]:
    errores: list[SetupError] = []
    if data.edad is None:
        errores.append(SetupError(campo="edad", mensaje="La edad es obligatoria."))
    if data.peso_kg is None:
        errores.append(SetupError(campo="peso_kg", mensaje="El peso es obligatorio."))
    if data.altura_cm is None:
        errores.append(
            SetupError(campo="altura_cm", mensaje="La altura es obligatoria.")
        )
    if errores:
        return None, errores
    try:
        perfil = Perfil(
            nombre=data.nombre,
            edad=data.edad,  # type: ignore[arg-type]
            peso_kg=data.peso_kg,  # type: ignore[arg-type]
            altura_cm=data.altura_cm,  # type: ignore[arg-type]
            sexo=_sexo_from_str(data.sexo),
            unidad_peso=data.unidad_peso,
            unidad_altura=data.unidad_altura,
            objetivo=_objetivo_from_str(data.objetivo),
        )
        return perfil, []
    except ValidationError as exc:
        for e in exc.errors():
            campo = ".".join(str(x) for x in e["loc"]) or "perfil"
            errores.append(SetupError(campo=campo, mensaje=e["msg"]))
        return None, errores


def _validar_objetivos(data: SetupInput) -> tuple[Optional[Objetivos], list[SetupError]]:
    # Todos los campos son opcionales; solo se construye si hay alguno.
    if not any(
        v is not None
        for v in (
            data.peso_objetivo_kg,
            data.kcal_diarias,
            data.proteina_g,
            data.grasa_g,
            data.carbohidratos_g,
        )
    ):
        return None, []
    try:
        obj = Objetivos(
            peso_objetivo_kg=data.peso_objetivo_kg,
            kcal_diarias=data.kcal_diarias,
            proteina_g=data.proteina_g,
            grasa_g=data.grasa_g,
            carbohidratos_g=data.carbohidratos_g,
        )
        return obj, []
    except ValidationError as exc:
        errores = [
            SetupError(
                campo=".".join(str(x) for x in e["loc"]) or "objetivos",
                mensaje=e["msg"],
            )
            for e in exc.errors()
        ]
        return None, errores


def _validar_actividad(
    data: SetupInput,
) -> tuple[Optional[ActividadHabitual], list[SetupError]]:
    if not any(
        v is not None
        for v in (
            data.tipo_trabajo,
            data.horas_actividad_laboral,
            data.tiempo_de_pie_h,
            data.movimiento_durante_trabajo,
            data.frecuencia_gimnasio_semanal,
            data.tipo_entrenamiento,
            data.pasos_diarios_promedio,
            data.otros_deportes,
        )
    ):
        return None, []
    try:
        act = ActividadHabitual(
            tipo_trabajo=data.tipo_trabajo,
            horas_actividad_laboral=data.horas_actividad_laboral,
            tiempo_de_pie_h=data.tiempo_de_pie_h,
            movimiento_durante_trabajo=data.movimiento_durante_trabajo,
            frecuencia_gimnasio_semanal=data.frecuencia_gimnasio_semanal,
            tipo_entrenamiento=data.tipo_entrenamiento,
            pasos_diarios_promedio=data.pasos_diarios_promedio,
            otros_deportes=data.otros_deportes,
        )
        return act, []
    except ValidationError as exc:
        errores = [
            SetupError(
                campo=".".join(str(x) for x in e["loc"]) or "actividad",
                mensaje=e["msg"],
            )
            for e in exc.errors()
        ]
        return None, errores


def aplicar_setup(
    data: SetupInput,
    vault: Vault,
    *,
    sobrescribir: bool = False,
) -> SetupResult:
    """Valida, construye y guarda perfil, objetivos y actividad.

    - Si hay errores de validación, no escribe nada.
    - Si ya existe un perfil y `sobrescribir=False`, devuelve error.
    - Tras escribir, verifica lectura.
    """
    errores: list[SetupError] = []

    if not sobrescribir and vault.read_perfil() is not None:
        errores.append(
            SetupError(
                campo="perfil",
                mensaje="Ya existe un perfil. Usa sobrescribir=True para reemplazarlo.",
            )
        )
        return SetupResult(ok=False, errores=errores)

    perfil, err_p = _validar_perfil(data)
    errores.extend(err_p)
    objetivos, err_o = _validar_objetivos(data)
    errores.extend(err_o)
    actividad, err_a = _validar_actividad(data)
    errores.extend(err_a)

    if errores:
        return SetupResult(ok=False, errores=errores)

    assert perfil is not None  # garantizado por la validación
    rutas: list[str] = []
    try:
        rutas.append(str(vault.write_perfil(perfil)))
        if objetivos is not None:
            rutas.append(str(vault.write_objetivos(objetivos)))
        if actividad is not None:
            rutas.append(str(vault.write_actividad(actividad)))
    except VaultError as exc:
        errores.append(SetupError(campo="vault", mensaje=str(exc)))
        return SetupResult(
            ok=False,
            errores=errores,
            perfil=perfil,
            objetivos=objetivos,
            actividad=actividad,
            modelo=data.modelo,
            rutas_escritas=rutas,
        )

    # Verificación de lectura
    try:
        p2 = vault.read_perfil()
        if p2 is None or p2.edad != perfil.edad or p2.peso_kg != perfil.peso_kg:
            errores.append(
                SetupError(
                    campo="verificacion",
                    mensaje="La lectura del perfil no coincide con lo escrito.",
                )
            )
        if objetivos is not None:
            o2 = vault.read_objetivos()
            if o2 is None or o2.kcal_diarias != objetivos.kcal_diarias:
                errores.append(
                    SetupError(
                        campo="verificacion",
                        mensaje="La lectura de objetivos no coincide con lo escrito.",
                    )
                )
        if actividad is not None:
            a2 = vault.read_actividad()
            if a2 is None or a2.tipo_trabajo != actividad.tipo_trabajo:
                errores.append(
                    SetupError(
                        campo="verificacion",
                        mensaje="La lectura de actividad no coincide con lo escrito.",
                    )
                )
    except VaultError as exc:
        errores.append(SetupError(campo="verificacion", mensaje=str(exc)))

    return SetupResult(
        ok=not errores,
        errores=errores,
        perfil=perfil,
        objetivos=objetivos,
        actividad=actividad,
        modelo=data.modelo,
        rutas_escritas=rutas,
    )


def perfil_existente(vault: Vault) -> bool:
    """True si ya hay un perfil guardado."""
    return vault.read_perfil() is not None