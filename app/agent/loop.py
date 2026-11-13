"""Bucle conversacional mínimo del agente.

Conecta intérprete → herramientas → persistencia → respuesta.
Comandos locales: /hoy, /ayuda, /salir. El resto va al modelo.
"""

from __future__ import annotations

from datetime import date
from typing import Optional
from rich.prompt import Confirm, Prompt

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from app.agent.operations import AltaAlimentoOp, EditarItemOp
from app.models.domain import Alimento, ItemComida

from app.core.reports import (
    generar_reporte_diario,
    generar_reporte_mensual,
    generar_reporte_semanal,
)

from app.setup.console import (
    confirmar_o_editar,
    preguntar_actividad,
    preguntar_modelo,
    preguntar_objetivos,
    preguntar_perfil,
)
from app.setup.wizard import SetupInput, aplicar_setup, perfil_existente
from app.models.domain import (
    ActividadHabitual,
    Alimento,
    Objetivos,
    Perfil,
    Receta,
    RegistroDiario,
    ActividadDia,
)

from app.agent.interpreter import interpretar
from app.agent.operations import (
    AgregarItemOp,
    AgregarRecetaOp,
    AltaAlimentoOp,
    ConsultarAlimentosOp,
    ConsultarTotalesOp,
    EditarItemOp,
    EliminarItemOp,
    ListarItemsOp,
    OperacionInvalida,
    ResponderOp,
    parsear_fecha,
    RegistrarActividadOp,
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
  /hoy              Ver items y totales del día.
  /reporte          Generar reporte diario de hoy (Markdown).
  /reporte-semana   Generar reporte de los últimos 7 días.
  /reporte-mes      Generar reporte del mes actual.
  /perfil           Mostrar el perfil actual.
  /objetivos        Mostrar los objetivos.
  /actividad        Mostrar la actividad habitual.
  /alimentos        Listar alimentos de la bóveda.
  /recetas          Listar recetas de la bóveda.
  /modelo           Ver o cambiar el modelo activo (solo sesión).
  /configurar       Reabrir el asistente de configuración.
  /ayuda            Mostrar esta ayuda.
  /salir            Salir.

Los comandos empiezan por "/" y deben escribirse exactamente.
Si escribes algo que empieza por "/" y no es un comando, se avisa sin
llamar al modelo.

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

def _confirmar_alta_alimento(console: Console, op: AltaAlimentoOp) -> bool:
    table = Table(title="Nuevo alimento propuesto")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    table.add_row("ID", op.id)
    table.add_row("Nombre", op.nombre)
    table.add_row("Marca", op.marca or "—")
    table.add_row("Unidad base", op.unidad_base.value)
    table.add_row("Peso ref. (g)", "—" if op.peso_referencia_g is None else str(op.peso_referencia_g))
    table.add_row("Kcal/100", "—" if op.kcal_por_100 is None else str(op.kcal_por_100))
    table.add_row("Prot/100", "—" if op.proteina_g_por_100 is None else str(op.proteina_g_por_100))
    table.add_row("Grasa/100", "—" if op.grasa_g_por_100 is None else str(op.grasa_g_por_100))
    table.add_row("Carb/100", "—" if op.carbo_g_por_100 is None else str(op.carbo_g_por_100))
    table.add_row("Fuente", op.fuente or "—")
    table.add_row("Notas", op.notas or "—")
    console.print(table)
    return Confirm.ask(
        f"¿Confirmas el alta de {op.id!r}?", default=False, console=console
    )

def _confirmar_editar_item(
    console: Console, item_actual: ItemComida, op: EditarItemOp
) -> bool:
    table = Table(title="Edición de item")
    table.add_column("Campo", style="cyan")
    table.add_column("Actual")
    table.add_column("Nuevo", style="green")

    def v(x) -> str:
        return "—" if x is None else str(x)

    if op.cantidad is not None:
        table.add_row(
            "Cantidad", f"{item_actual.cantidad:g}", f"{op.cantidad:g}"
        )
    if op.unidad is not None:
        table.add_row("Unidad", item_actual.unidad.value, op.unidad.value)
    if op.etiqueta is not None:
        nuevo_etiqueta = op.etiqueta if op.etiqueta != "" else "—"
        table.add_row(
            "Etiqueta", v(item_actual.etiqueta), nuevo_etiqueta
        )
    console.print(table)
    return Confirm.ask("¿Confirmas la edición?", default=False, console=console)

def _confirmar_registrar_actividad(console: Console, op: RegistrarActividadOp) -> bool:
    table = Table(title="Actividad del día")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    for k, v in op.model_dump(exclude_none=True).items():
        if k == "tipo":
            continue
        table.add_row(k, str(v))
    console.print(table)
    return Confirm.ask(
        "Ya hay actividad registrada hoy. ¿Sobrescribir?",
        default=False,
        console=console,
    )

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

    if isinstance(op, EditarItemOp):
        fecha = parsear_fecha(op.fecha)
        reg = registro if fecha == registro.fecha else _nuevo_registro(fecha, vault)
        if op.indice < 1 or op.indice > len(reg.items):
            console.print(
                f"[red]Índice fuera de rango: {op.indice}. "
                f"Hay {len(reg.items)} item(s).[/red]"
            )
            return registro, False
        item_actual = reg.items[op.indice - 1]
        if not _confirmar_editar_item(console, item_actual, op):
            console.print("[dim]Edición cancelada.[/dim]")
            return registro, False
        update: dict = {}
        if op.cantidad is not None:
            update["cantidad"] = op.cantidad
        if op.unidad is not None:
            update["unidad"] = op.unidad
        if op.etiqueta is not None:
            update["etiqueta"] = op.etiqueta if op.etiqueta != "" else None
        item_nuevo = item_actual.model_copy(update=update)
        nuevos = list(reg.items)
        nuevos[op.indice - 1] = item_nuevo
        reg_nuevo = reg.model_copy(update={"items": nuevos})
        console.print(f"[green]Item {op.indice} actualizado.[/green]")
        return reg_nuevo, True

    if isinstance(op, AltaAlimentoOp):
        if not _confirmar_alta_alimento(console, op):
            console.print("[dim]Alta cancelada.[/dim]")
            return registro, False
        try:
            alimento = Alimento(
                id=op.id,
                nombre=op.nombre,
                marca=op.marca,
                unidad_base=op.unidad_base,
                peso_referencia_g=op.peso_referencia_g,
                kcal_por_100=op.kcal_por_100,
                proteina_g_por_100=op.proteina_g_por_100,
                grasa_g_por_100=op.grasa_g_por_100,
                carbo_g_por_100=op.carbo_g_por_100,
                fuente=op.fuente,
                notas=op.notas,
            )
            vault.add_alimento(alimento)
        except Exception as exc:
            console.print(f"[red]No se pudo dar de alta el alimento: {exc}[/red]")
            return registro, False
        console.print(f"[green]Alimento agregado: {op.id}[/green]")
        return registro, False
    
    if isinstance(op, RegistrarActividadOp):
        fecha = parsear_fecha(op.fecha)
        reg = registro if fecha == registro.fecha else _nuevo_registro(fecha, vault)
        if reg.actividad_dia is not None:
            if not _confirmar_registrar_actividad(console, op):
                console.print("[dim]Registro cancelado.[/dim]")
                return registro, False
        act = ActividadDia(
            horas_trabajo=op.horas_trabajo,
            horas_de_pie=op.horas_de_pie,
            pasos=op.pasos,
            gimnasio=op.gimnasio,
            gimnasio_duracion_min=op.gimnasio_duracion_min,
            tipo_entrenamiento=op.tipo_entrenamiento,
            otros_deportes=op.otros_deportes,
            notas=op.notas,
        )
        reg_nuevo = reg.model_copy(update={"actividad_dia": act})
        console.print("[green]Actividad del día registrada.[/green]")
        try:
            perfil = vault.read_perfil()
            hab = vault.read_actividad()
            if perfil is not None:
                from app.core.nutrition import calcular_balance
                bal = calcular_balance(
                    reg_nuevo, perfil, hab or ActividadHabitual(), vault
                )
                if bal.balance_kcal is not None:
                    console.print(
                        f"TDEE estimado: {bal.gasto_kcal:.1f} kcal; "
                        f"consumo: {bal.consumo_kcal:.1f} kcal; "
                        f"balance: {bal.balance_kcal:+.1f} kcal "
                        f"({bal.fuente.value})"
                    )
                else:
                    console.print(
                        f"[dim]Balance no calculable ({bal.fuente.value}).[/dim]"
                    )
        except Exception as exc:
            console.print(f"[dim]No se pudo calcular el balance: {exc}[/dim]")
        return reg_nuevo, True

    
    if isinstance(op, ResponderOp):
        console.print(Panel(op.mensaje, border_style="blue"))
        return registro, False

    console.print(f"[red]Operación no manejada: {type(op).__name__}[/red]")
    return registro, False


def _nuevo_registro(fecha: date, vault: Vault):
    from app.models.domain import RegistroDiario

    existente = vault.read_registro(fecha)
    return existente or RegistroDiario(fecha=fecha)

def _mostrar_perfil(console: Console, perfil: Perfil) -> None:
    table = Table(title="Perfil")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    table.add_row("Nombre", perfil.nombre or "—")
    table.add_row("Edad", str(perfil.edad))
    table.add_row("Peso (kg)", f"{perfil.peso_kg:.1f}")
    table.add_row("Altura (cm)", f"{perfil.altura_cm:.1f}")
    table.add_row("Sexo", perfil.sexo.value)
    table.add_row("Objetivo", perfil.objetivo.value)
    table.add_row("Unidad peso", perfil.unidad_peso)
    table.add_row("Unidad altura", perfil.unidad_altura)
    console.print(table)


def _mostrar_objetivos(console: Console, obj: Objetivos | None) -> None:
    if obj is None:
        console.print("[dim]Sin objetivos configurados.[/dim]")
        return
    table = Table(title="Objetivos")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    for k, v in obj.model_dump().items():
        table.add_row(k, "—" if v is None else str(v))
    console.print(table)


def _mostrar_actividad(console: Console, act: ActividadHabitual | None) -> None:
    if act is None:
        console.print("[dim]Sin actividad habitual configurada.[/dim]")
        return
    table = Table(title="Actividad habitual")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    for k, v in act.model_dump().items():
        table.add_row(k, "—" if v is None else str(v))
    console.print(table)


def _mostrar_alimentos(console: Console, alimentos: list[Alimento]) -> None:
    if not alimentos:
        console.print("[dim]Sin alimentos en la bóveda.[/dim]")
        return
    table = Table(title=f"Alimentos ({len(alimentos)})")
    table.add_column("ID")
    table.add_column("Nombre")
    table.add_column("Marca")
    table.add_column("Kcal/100", justify="right")
    table.add_column("Prot", justify="right")
    table.add_column("Grasa", justify="right")
    table.add_column("Carb", justify="right")
    for a in alimentos:
        table.add_row(
            a.id, a.nombre, a.marca or "—",
            "—" if a.kcal_por_100 is None else f"{a.kcal_por_100:.1f}",
            "—" if a.proteina_g_por_100 is None else f"{a.proteina_g_por_100:.1f}",
            "—" if a.grasa_g_por_100 is None else f"{a.grasa_g_por_100:.1f}",
            "—" if a.carbo_g_por_100 is None else f"{a.carbo_g_por_100:.1f}",
        )
    console.print(table)


def _mostrar_recetas(console: Console, recetas: list[Receta]) -> None:
    if not recetas:
        console.print("[dim]Sin recetas en la bóveda.[/dim]")
        return
    table = Table(title=f"Recetas ({len(recetas)})")
    table.add_column("ID")
    table.add_column("Nombre")
    table.add_column("Ingredientes", justify="right")
    table.add_column("Rendimiento", justify="right")
    for r in recetas:
        table.add_row(
            r.id, r.nombre, str(len(r.ingredientes)),
            f"{r.rendimiento_porciones:.1f}",
        )
    console.print(table)


def _manejar_configurar(vault: Vault, console: Console, client: OllamaClient) -> None:
    if perfil_existente(vault):
        if not Prompt.ask(
            "Ya hay un perfil. ¿Sobrescribir? (s/N)",
            default="N",
            console=console,
        ).lower().startswith("s"):
            console.print("[dim]Cancelado.[/dim]")
            return
    # Reutiliza el flujo del asistente
    perfil_data = preguntar_perfil(console)
    objetivos_data = preguntar_objetivos(console)
    actividad_data = preguntar_actividad(console)
    data = SetupInput(**perfil_data, **objetivos_data, **actividad_data)
    confirmado, data_final = confirmar_o_editar(console, data)
    if not confirmado:
        console.print("[dim]Cancelado.[/dim]")
        return
    result = aplicar_setup(data_final, vault, sobrescribir=True)
    if not result.ok:
        for e in result.errores:
            console.print(f"[red]{e.campo}: {e.mensaje}[/red]")
        return
    console.print("[green]Configuración actualizada.[/green]")


def _manejar_modelo(
    console: Console, client: OllamaClient
) -> OllamaClient:
    """Muestra el modelo activo, permite cambiarlo en memoria.

    Devuelve el cliente que debe usar el bucle:
    - Si no se cambia, el mismo `client`.
    - Si se cambia, un cliente nuevo con el modelo elegido.
    El cliente viejo se cierra si se reemplaza.
    """
    try:
        modelos = [m.name for m in client.list_models()]
    except OllamaError as exc:
        console.print(f"[red]No se pudo listar modelos: {exc}[/red]")
        return client

    if not modelos:
        console.print("[yellow]No hay modelos instalados.[/yellow]")
        return client

    actual = client.model
    console.print(f"Modelo activo: [bold]{actual}[/bold]")

    nuevo = preguntar_modelo(console, modelos, default=actual)
    if nuevo is None or nuevo == actual:
        console.print("[dim]Sin cambios.[/dim]")
        return client

    console.print(f"Cambiando a [bold]{nuevo}[/bold]...")
    nuevo_client = client.with_model(nuevo)
    client.close()
    console.print(
        f"[green]Modelo activo: {nuevo}[/green] "
        "(solo en esta sesión; .env no se modifica)"
    )
    return nuevo_client

def _mostrar_resumen_reporte_diario(console: Console, r) -> None:
    table = Table(title=f"Reporte diario {r.fecha.isoformat()}")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    table.add_row("Items", str(len(r.items)))
    for k, v in r.totales.model_dump().items():
        table.add_row(k, "—" if v is None else f"{v:.1f}")
    table.add_row("Balance (kcal)", "—" if r.balance.balance_kcal is None else f"{r.balance.balance_kcal:+.1f}")
    table.add_row("Fuente", r.fuente.value)
    console.print(table)


def _mostrar_resumen_reporte_semanal(console: Console, r) -> None:
    table = Table(title=f"Reporte semanal {r.desde.isoformat()} → {r.hasta.isoformat()}")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    table.add_row("Días con datos", str(r.dias_con_datos))
    table.add_row("Días sin datos", str(r.dias_sin_datos))
    table.add_row("Días entrenados", str(r.dias_entrenados))
    for k, v in r.promedios.model_dump().items():
        table.add_row(f"Prom. {k}", "—" if v is None else f"{v:.1f}")
    table.add_row(
        "Balance prom. (kcal)",
        "—" if r.balance_promedio.balance_kcal is None else f"{r.balance_promedio.balance_kcal:+.1f}",
    )
    table.add_row("Fuente", r.fuente.value)
    console.print(table)


def _mostrar_resumen_reporte_mensual(console: Console, r) -> None:
    table = Table(title=f"Reporte mensual {r.desde.isoformat()} → {r.hasta.isoformat()}")
    table.add_column("Campo", style="cyan")
    table.add_column("Valor")
    table.add_row("Días con datos", str(r.dias_con_datos))
    table.add_row("Días sin datos", str(r.dias_sin_datos))
    table.add_row("Días entrenados", str(r.dias_entrenados))
    table.add_row(
        "Consistencia", "—" if r.consistencia_pct is None else f"{r.consistencia_pct:.1f}%"
    )
    for k, v in r.promedios.model_dump().items():
        table.add_row(f"Prom. {k}", "—" if v is None else f"{v:.1f}")
    table.add_row(
        "Balance prom. (kcal)",
        "—" if r.balance_promedio.balance_kcal is None else f"{r.balance_promedio.balance_kcal:+.1f}",
    )
    table.add_row("Fuente", r.fuente.value)
    console.print(table)


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

        if linea == "/reporte":
            from datetime import date as _d
            hoy = _d.today()
            r = generar_reporte_diario(hoy, vault)
            path = vault.write_reporte_diario(r)
            rel = path.relative_to(vault.data_dir)
            _mostrar_resumen_reporte_diario(console, r)
            console.print(f"[dim]Guardado en {rel}[/dim]")
            continue

        if linea == "/reporte-semana":
            from datetime import date as _d, timedelta as _td
            hoy = _d.today()
            desde = hoy - _td(days=6)
            r = generar_reporte_semanal(desde, hoy, vault)
            path = vault.write_reporte_semanal(r)
            rel = path.relative_to(vault.data_dir)
            _mostrar_resumen_reporte_semanal(console, r)
            console.print(f"[dim]Guardado en {rel}[/dim]")
            continue

        if linea == "/reporte-mes":
            from datetime import date as _d
            hoy = _d.today()
            r = generar_reporte_mensual(hoy.year, hoy.month, vault)
            path = vault.write_reporte_mensual(r)
            rel = path.relative_to(vault.data_dir)
            _mostrar_resumen_reporte_mensual(console, r)
            console.print(f"[dim]Guardado en {rel}[/dim]")
            continue

        if linea == "/perfil":
            p = vault.read_perfil()
            if p is None:
                console.print("[dim]Sin perfil configurado.[/dim]")
            else:
                _mostrar_perfil(console, p)
            continue
        if linea == "/objetivos":
            _mostrar_objetivos(console, vault.read_objetivos())
            continue
        if linea == "/actividad":
            _mostrar_actividad(console, vault.read_actividad())
            continue
        if linea == "/alimentos":
            _mostrar_alimentos(console, vault.read_alimentos())
            continue
        if linea == "/recetas":
            _mostrar_recetas(console, vault.read_recetas())
            continue
        if linea == "/configurar":
            _manejar_configurar(vault, console, client)
            continue
        if linea == "/modelo":
            client = _manejar_modelo(console, client)
            continue

        # Cualquier línea que empiece por "/" y no sea un comando conocido
        # se rechaza sin llamar al modelo.
        if linea.startswith("/"):
            console.print(
                f"[yellow]Comando no reconocido: {linea}[/yellow]\n"
                "Usa /ayuda para ver los comandos disponibles."
            )
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