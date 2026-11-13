"""Capa de consola del asistente. Usa Rich para preguntar y mostrar.

No persiste: construye SetupInput y llama a aplicar_setup.
"""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from app.models.domain import (
    Objetivo,
    Sexo,
)
from app.setup.wizard import (
    SetupError,
    SetupInput,
    SetupResult,
    aplicar_setup,
)
from app.storage.vault import Vault


def _ask_text(
    console: Console,
    mensaje: str,
    *,
    default: Optional[str] = None,
    permitir_vacio: bool = True,
) -> Optional[str]:
    if default is not None:
        raw = Prompt.ask(mensaje, default=default, console=console)
    else:
        raw = Prompt.ask(mensaje, console=console)
    raw = (raw or "").strip()
    if raw == "":
        if permitir_vacio:
            return None
        return _ask_text(
            console, mensaje, default=default, permitir_vacio=permitir_vacio
        )
    return raw


def _ask_int(
    console: Console,
    mensaje: str,
    *,
    default: Optional[int] = None,
    minimo: Optional[int] = None,
    maximo: Optional[int] = None,
) -> Optional[int]:
    while True:
        raw = Prompt.ask(
            mensaje,
            default=str(default) if default is not None else None,
            console=console,
        )
        raw = (raw or "").strip()
        if raw == "":
            return None
        try:
            v = int(raw)
        except ValueError:
            console.print("[red]Valor no entero. Inténtalo de nuevo.[/red]")
            continue
        if minimo is not None and v < minimo:
            console.print(f"[red]Debe ser >= {minimo}.[/red]")
            continue
        if maximo is not None and v > maximo:
            console.print(f"[red]Debe ser <= {maximo}.[/red]")
            continue
        return v


def _ask_float(
    console: Console,
    mensaje: str,
    *,
    default: Optional[float] = None,
    minimo: Optional[float] = None,
    maximo: Optional[float] = None,
) -> Optional[float]:
    while True:
        raw = Prompt.ask(
            mensaje,
            default=str(default) if default is not None else None,
            console=console,
        )
        raw = (raw or "").strip().replace(",", ".")
        if raw == "":
            return None
        try:
            v = float(raw)
        except ValueError:
            console.print("[red]Valor no numérico. Inténtalo de nuevo.[/red]")
            continue
        if minimo is not None and v < minimo:
            console.print(f"[red]Debe ser >= {minimo}.[/red]")
            continue
        if maximo is not None and v > maximo:
            console.print(f"[red]Debe ser <= {maximo}.[/red]")
            continue
        return v


def _ask_choice(
    console: Console,
    mensaje: str,
    opciones: list[str],
    *,
    default: Optional[str] = None,
) -> Optional[str]:
    texto = f"{mensaje} ({'/'.join(opciones)})"
    while True:
        raw = Prompt.ask(texto, default=default, console=console)
        raw = (raw or "").strip().lower()
        if raw == "":
            return None
        if raw in opciones:
            return raw
        console.print(f"[red]Opción no válida. Usa una de: {opciones}[/red]")


def preguntar_perfil(console: Console) -> dict:
    console.print("\n[bold]Paso 2 — Perfil[/bold]")
    nombre = _ask_text(console, "Nombre o alias (opcional)")
    edad = _ask_int(console, "Edad (años)", minimo=1, maximo=120)
    peso = _ask_float(console, "Peso (kg)", minimo=1.0, maximo=500.0)
    altura = _ask_float(console, "Altura (cm)", minimo=50.0, maximo=250.0)
    sexo = _ask_choice(
        console,
        "Sexo biológico",
        ["masculino", "femenino", "otro", "no_especificado"],
        default="no_especificado",
    )
    unidad_peso = _ask_choice(console, "Unidad de peso", ["kg", "lb"], default="kg")
    unidad_altura = _ask_choice(console, "Unidad de altura", ["cm", "in"], default="cm")
    objetivo = _ask_choice(
        console,
        "Objetivo",
        ["perdida_grasa", "mantenimiento", "ganancia_muscular", "otro"],
        default="mantenimiento",
    )
    return dict(
        nombre=nombre,
        edad=edad,
        peso_kg=peso,
        altura_cm=altura,
        sexo=sexo,
        unidad_peso=unidad_peso or "kg",
        unidad_altura=unidad_altura or "cm",
        objetivo=objetivo or "mantenimiento",
    )


def preguntar_objetivos(console: Console) -> dict:
    console.print("\n[bold]Paso 3 — Objetivos (opcional, Enter para omitir)[/bold]")
    return dict(
        peso_objetivo_kg=_ask_float(
            console, "Peso objetivo (kg)", minimo=1.0, maximo=500.0
        ),
        kcal_diarias=_ask_float(
            console, "Meta diaria de kcal", minimo=0.0, maximo=20000.0
        ),
        proteina_g=_ask_float(
            console, "Meta diaria de proteínas (g)", minimo=0.0, maximo=1000.0
        ),
        grasa_g=_ask_float(
            console, "Meta diaria de grasas (g)", minimo=0.0, maximo=1000.0
        ),
        carbohidratos_g=_ask_float(
            console, "Meta diaria de carbohidratos (g)", minimo=0.0, maximo=2000.0
        ),
    )


def preguntar_actividad(console: Console) -> dict:
    console.print("\n[bold]Paso 4 — Actividad habitual (opcional)[/bold]")
    return dict(
        tipo_trabajo=_ask_text(console, "Tipo de trabajo"),
        horas_actividad_laboral=_ask_float(
            console, "Horas de actividad laboral al día", minimo=0.0, maximo=24.0
        ),
        tiempo_de_pie_h=_ask_float(
            console, "Horas de pie al día", minimo=0.0, maximo=24.0
        ),
        movimiento_durante_trabajo=_ask_text(console, "Movimiento durante el trabajo"),
        frecuencia_gimnasio_semanal=_ask_int(
            console, "Días de gimnasio por semana", minimo=0, maximo=14
        ),
        tipo_entrenamiento=_ask_text(console, "Tipo de entrenamiento"),
        pasos_diarios_promedio=_ask_int(
            console, "Pasos diarios promedio", minimo=0, maximo=100000
        ),
        otros_deportes=_ask_text(console, "Otros deportes o actividades"),
    )


def preguntar_modelo(
    console: Console, modelos: list[str], *, default: Optional[str] = None
) -> Optional[str]:
    if not modelos:
        return None
    console.print("\n[bold]Paso 1 — Modelo de IA[/bold]")
    for i, m in enumerate(modelos, start=1):
        console.print(f"  {i}. {m}")
    while True:
        raw = Prompt.ask(
            "Elige modelo por número (Enter para el primero)",
            default="1",
            console=console,
        )
        raw = (raw or "").strip()
        if raw == "":
            return modelos[0]
        try:
            idx = int(raw)
        except ValueError:
            console.print("[red]Número no válido.[/red]")
            continue
        if 1 <= idx <= len(modelos):
            return modelos[idx - 1]
        console.print("[red]Fuera de rango.[/red]")


def mostrar_resumen(console: Console, data: SetupInput) -> None:
    table = Table(title="Resumen de configuración", show_lines=True)
    table.add_column("Campo", style="cyan")
    table.add_column("Valor", style="white")

    def v(x) -> str:
        return "(vacío)" if x is None or x == "" else str(x)

    table.add_row("Nombre", v(data.nombre))
    table.add_row("Edad", v(data.edad))
    table.add_row("Peso (kg)", v(data.peso_kg))
    table.add_row("Altura (cm)", v(data.altura_cm))
    table.add_row("Sexo", v(data.sexo))
    table.add_row("Unidad peso", v(data.unidad_peso))
    table.add_row("Unidad altura", v(data.unidad_altura))
    table.add_row("Objetivo", v(data.objetivo))
    table.add_row("—", "—")
    table.add_row("Peso objetivo (kg)", v(data.peso_objetivo_kg))
    table.add_row("Kcal diarias", v(data.kcal_diarias))
    table.add_row("Proteínas (g)", v(data.proteina_g))
    table.add_row("Grasas (g)", v(data.grasa_g))
    table.add_row("Carbohidratos (g)", v(data.carbohidratos_g))
    table.add_row("—", "—")
    table.add_row("Tipo de trabajo", v(data.tipo_trabajo))
    table.add_row("Horas laborales", v(data.horas_actividad_laboral))
    table.add_row("Horas de pie", v(data.tiempo_de_pie_h))
    table.add_row("Movimiento en trabajo", v(data.movimiento_durante_trabajo))
    table.add_row("Gimnasio (días/sem)", v(data.frecuencia_gimnasio_semanal))
    table.add_row("Tipo de entrenamiento", v(data.tipo_entrenamiento))
    table.add_row("Pasos diarios", v(data.pasos_diarios_promedio))
    table.add_row("Otros deportes", v(data.otros_deportes))
    table.add_row("Modelo IA", v(data.modelo))
    console.print(table)


def confirmar_o_editar(console: Console, data: SetupInput) -> tuple[bool, SetupInput]:
    """Devuelve (confirmado, data_final). Bucle hasta confirmar o cancelar."""
    campos = list(SetupInput.model_fields.keys())
    while True:
        mostrar_resumen(console, data)
        if not Confirm.ask("¿Guardar esta configuración?", default=True, console=console):
            return False, data
        if not Confirm.ask(
            "¿Editar algún campo antes de guardar?", default=False, console=console
        ):
            return True, data
        # Edición
        for i, c in enumerate(campos, start=1):
            console.print(f"  {i}. {c}")
        raw = Prompt.ask("Número de campo a editar", console=console)
        try:
            idx = int(raw) - 1
            if idx < 0 or idx >= len(campos):
                raise ValueError
        except (TypeError, ValueError):
            console.print("[red]Número no válido.[/red]")
            continue
        campo = campos[idx]
        nuevo = Prompt.ask(
            f"Nuevo valor para {campo} (Enter para dejar vacío)",
            default="",
            console=console,
        ).strip()
        # Coerción simple según el campo
        valor: object = nuevo if nuevo != "" else None
        if campo in {"edad", "frecuencia_gimnasio_semanal", "pasos_diarios_promedio"}:
            valor = int(nuevo) if nuevo != "" else None
        elif campo in {
            "peso_kg",
            "altura_cm",
            "peso_objetivo_kg",
            "kcal_diarias",
            "proteina_g",
            "grasa_g",
            "carbohidratos_g",
            "horas_actividad_laboral",
            "tiempo_de_pie_h",
        }:
            valor = float(nuevo) if nuevo != "" else None
        data = data.model_copy(update={campo: valor})