"""Bucle conversacional mínimo del agente.

Conecta intérprete → herramientas → persistencia → respuesta.
Comandos locales: /hoy, /ayuda, /salir. El resto va al modelo.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from app.agent.interpreter import interpretar
from app.agent.operations import (
    AgregarItemOp,
    AgregarRecetaOp,
    ConsultarAlimentosOp,
    ConsultarTotalesOp,
    EliminarItemOp,
    ListarItemsOp,
    OperacionInvalida,
    ResponderOp,
    parsear_fecha,
)
from app.agent.tools import (
    agregar_item,
    agregar_item_receta,
    buscar_alimentos,
    eliminar_item_por_indice,
    listar_items,
    totales,
)
from app.core.errors import NutritionError, ReferenciaInexistente
from app.ollama_client import OllamaClient, OllamaError
from app.storage.vault import Vault, VaultError


_AYUDA = """\
Comandos:
  /hoy     Ver items y totales del día.
  /ayuda   Mostrar esta ayuda.
  /salir   Salir.

También puedes escribir en lenguaje natural, por ejemplo:
  "agregué 150 g de arroz"
  "elimina el item 2"
  "¿cuántas kcal llevo hoy?"
"""


def _fmt(v: Optional[float]) -> str:
    return "—" if v is None else f"{v:.1f}"


def _mostrar_totales(console: Console, registro, vault: Vault) -> None:
    t = totales(registro, vault)
    table = Table(title=f"Totales del {t.fecha.isoformat()}")
    table.add_column("Nutriente", style="cyan")
    table.add_column("Valor", justify="right")
    table.add_row("Kcal", _fmt(t.total.kcal))
    table.add_row("Proteína (g)", _fmt(t.total.proteina_g))
    table.add_row("Grasa (g)", _fmt(t.total.grasa_g))
    table.add_row("Carbohidratos (g)", _fmt(t.total.carbo_g))
    table.add_row("Fuente", t.fuente.value)
    console.print(table)
    if t.notas:
        for n in t.notas:
            console.print(f"  [dim]{n}[/dim]")


def _mostrar_items(console: Console, registro, vault: Vault) -> None:
    items = listar_items(registro, vault)
    if not items:
        console.print("[dim]Sin items registrados.[/dim]")
        return
    table = Table(title=f"Items del {registro.fecha.isoformat()}")
    table.add_column("#", justify="right")
    table.add_column("Ref")
    table.add_column("Cantidad", justify="right")
    table.add_column("Etiqueta")
    table.add_column("Kcal", justify="right")
    table.add_column("Prot", justify="right")
    table.add_column("Grasa", justify="right")
    table.add_column("Carb", justify="right")
    for it in items:
        table.add_row(
            str(it["indice"]),
            f"{it['ref_tipo']}:{it['ref_id']}",
            f"{it['cantidad']:.0f} {it['unidad']}",
            it["etiqueta"] or "—",
            _fmt(it["kcal"]),
            _fmt(it["proteina_g"]),
            _fmt(it["grasa_g"]),
            _fmt(it["carbo_g"]),
        )
    console.print(table)


def _ejecutar_operacion(
    op,
    registro,
    vault: Vault,
    console: Console,
) -> tuple[object, bool]:
    """Ejecuta la operación. Devuelve (registro_actualizado, cambió).

    - Si la operación es de solo lectura, devuelve (registro, False).
    - Si modifica, devuelve (registro_nuevo, True).
    """
    if isinstance(op, AgregarItemOp):
        fecha = parsear_fecha(op.fecha)
        reg = agregar_item(
            registro if fecha == registro.fecha else _nuevo_registro(fecha, vault),
            op.alimento_id,
            op.cantidad,
            op.unidad,
            etiqueta=op.etiqueta,
            vault=vault,
        )
        calc = listar_items(reg, vault)[-1]
        console.print(
            f"[green]Agregado:[/green] {op.cantidad:.0f} {op.unidad.value} de "
            f"{op.alimento_id} ({_fmt(calc['kcal'])} kcal)"
        )
        return reg, True

    if isinstance(op, AgregarRecetaOp):
        fecha = parsear_fecha(op.fecha)
        reg = agregar_item_receta(
            registro if fecha == registro.fecha else _nuevo_registro(fecha, vault),
            op.receta_id,
            op.cantidad,
            unidad=op.unidad,
            etiqueta=op.etiqueta,
            vault=vault,
        )
        calc = listar_items(reg, vault)[-1]
        console.print(
            f"[green]Agregado:[/green] {op.cantidad:.0f} {op.unidad.value} de "
            f"receta {op.receta_id} ({_fmt(calc['kcal'])} kcal)"
        )
        return reg, True

    if isinstance(op, EliminarItemOp):
        fecha = parsear_fecha(op.fecha)
        reg = eliminar_item_por_indice(
            registro if fecha == registro.fecha else _nuevo_registro(fecha, vault),
            op.indice,
        )
        console.print(f"[green]Eliminado item {op.indice}.[/green]")
        return reg, True

    if isinstance(op, ConsultarTotalesOp):
        fecha = parsear_fecha(op.fecha)
        reg = registro if fecha == registro.fecha else _nuevo_registro(fecha, vault)
        _mostrar_totales(console, reg, vault)
        return registro, False

    if isinstance(op, ListarItemsOp):
        fecha = parsear_fecha(op.fecha)
        reg = registro if fecha == registro.fecha else _nuevo_registro(fecha, vault)
        _mostrar_items(console, reg, vault)
        return registro, False

    if isinstance(op, ConsultarAlimentosOp):
        resultados = buscar_alimentos(vault, op.texto)
        if not resultados:
            console.print(f"[yellow]Sin coincidencias para {op.texto!r}.[/yellow]")
        else:
            table = Table(title=f"Alimentos que coinciden con {op.texto!r}")
            table.add_column("ID")
            table.add_column("Nombre")
            for a in resultados:
                table.add_row(a.id, a.nombre)
            console.print(table)
        return registro, False

    if isinstance(op, ResponderOp):
        console.print(Panel(op.mensaje, border_style="blue"))
        return registro, False

    console.print(f"[red]Operación no manejada: {type(op).__name__}[/red]")
    return registro, False


def _nuevo_registro(fecha: date, vault: Vault):
    from app.models.domain import RegistroDiario

    existente = vault.read_registro(fecha)
    return existente or RegistroDiario(fecha=fecha)


def run_loop(vault: Vault, client: OllamaClient, console: Console) -> int:
    """Bucle conversacional. Devuelve código de salida."""
    console.print(
        Panel.fit(
            "Bienvenido a NutricionAgent.\n"
            "Escribe en lenguaje natural o usa /ayuda para ver comandos.",
            border_style="cyan",
        )
    )

    fecha_actual = date.today()
    registro = _nuevo_registro(fecha_actual, vault)

    while True:
        try:
            linea = Prompt.ask("[bold cyan]tú[/bold cyan]", console=console)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Hasta luego.[/dim]")
            return 0

        linea = (linea or "").strip()
        if not linea:
            continue

        if linea in ("/salir", "/exit", "/quit"):
            console.print("[dim]Hasta luego.[/dim]")
            return 0
        if linea == "/ayuda":
            console.print(Panel(_AYUDA, border_style="cyan"))
            continue
        if linea == "/hoy":
            registro = _nuevo_registro(fecha_actual, vault)
            _mostrar_items(console, registro, vault)
            _mostrar_totales(console, registro, vault)
            continue

        # Lenguaje natural
        try:
            op = interpretar(linea, vault=vault, client=client, registro=registro)
        except OllamaError as exc:
            console.print(
                f"[red]Ollama no responde: {exc}[/red]\n"
                "Comprueba que Ollama esté en ejecución."
            )
            continue

        try:
            nuevo_reg, cambio = _ejecutar_operacion(op, registro, vault, console)
        except (ReferenciaInexistente, IndexError, OperacionInvalida, NutritionError) as exc:
            console.print(f"[red]Error: {exc}[/red]")
            continue

        if cambio:
            try:
                vault.write_registro(nuevo_reg)  # type: ignore[arg-type]
            except VaultError as exc:
                console.print(f"[red]No se pudo guardar el registro: {exc}[/red]")
                continue
        registro = nuevo_reg  # type: ignore[assignment]