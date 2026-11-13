"""Punto de entrada de NutricionAgent.

Uso:
    python -m app.main

Si no hay perfil, lanza el asistente de configuración inicial.
Si hay perfil, muestra un mensaje y termina (la app conversacional llega en Fase 7).

Códigos de salida:
    0  éxito
    1  error de configuración o escritura
    2  cancelado por el usuario
"""

from __future__ import annotations

import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from app.config import get_settings
from app.ollama_client import OllamaClient
from app.setup.checks import (
    estado_ollama,
    mensaje_modelo_no_disponible,
    mensaje_si_no_disponible,
    mensaje_si_sin_modelos,
    probar_modelo,
)
from app.setup.console import (
    confirmar_o_editar,
    preguntar_actividad,
    preguntar_modelo,
    preguntar_objetivos,
    preguntar_perfil,
)
from app.setup.wizard import SetupInput, aplicar_setup, perfil_existente
from app.storage.vault import Vault, VaultError


def _banner(console: Console) -> None:
    console.print(
        Panel.fit(
            "[bold cyan]NutricionAgent[/bold cyan]\n"
            "Asistente nutricional local. Configuración inicial.",
            border_style="cyan",
        )
    )


def _flujo_ollama(console: Console, client: OllamaClient, modelo_config: str) -> tuple[bool, str | None]:
    """Devuelve (continuar, modelo_elegido).

    - Si Ollama no está: ofrece modo solo memoria.
    - Si no hay modelos: ofrece modo solo memoria.
    - Si hay modelos: pregunta cuál usar y lo prueba.
    """
    console.print("\n[bold]Paso 1 — Comprobando Ollama[/bold]")
    estado = estado_ollama(client, modelo_configurado=modelo_config)
    if not estado.disponible:
        console.print(f"[yellow]{mensaje_si_no_disponible(estado)}[/yellow]")
        if Confirm.ask(
            "¿Continuar en modo solo memoria (sin IA)?",
            default=True,
            console=console,
        ):
            return True, None
        return False, None

    console.print(f"Ollama {estado.version} activo. Modelos: {len(estado.modelos)}")
    if not estado.modelos:
        console.print(f"[yellow]{mensaje_si_sin_modelos(estado)}[/yellow]")
        if Confirm.ask(
            "¿Continuar en modo solo memoria (sin IA)?",
            default=True,
            console=console,
        ):
            return True, None
        return False, None

    if estado.modelo_configurado and not estado.modelo_disponible:
        console.print(
            f"[yellow]{mensaje_modelo_no_disponible(estado)}[/yellow]"
        )

    elegido = preguntar_modelo(
        console,
        estado.modelos,
        default=estado.modelo_configurado if estado.modelo_disponible else None,
    )
    if elegido is None:
        return True, None

    console.print(f"Probando modelo [bold]{elegido}[/bold]...")
    res = probar_modelo(client, elegido)
    if not res.ok:
        console.print(
            f"[red]El modelo no respondió correctamente: {res.error}[/red]"
        )
        if Confirm.ask(
            "¿Continuar sin IA (solo memoria)?", default=True, console=console
        ):
            return True, None
        return False, None

    console.print(
        f"[green]Modelo OK[/green] ({res.tiempo_s:.1f}s)" if res.tiempo_s else "[green]Modelo OK[/green]"
    )
    return True, elegido


def run() -> int:
    console = Console()
    _banner(console)

    settings = get_settings()
    backup_root = settings.project_root / "data" / "backups"
    vault = Vault(
        data_dir=settings.data_dir,
        backup_root=backup_root,
        root_for_backup=settings.project_root / "data",
    )

    if perfil_existente(vault):
        console.print(
            Panel.fit(
                f"Perfil encontrado en {vault.perfil_path}.\n"
                "La app conversacional llegará en una fase posterior.",
                border_style="green",
            )
        )
        return 0

    console.print("No hay perfil configurado. Iniciando asistente.\n")

    client = OllamaClient(settings.ollama)
    try:
        continuar, modelo = _flujo_ollama(console, client, settings.ollama.model)
        if not continuar:
            console.print("[yellow]Configuración cancelada.[/yellow]")
            return 2

        console.print("\n[bold]Datos del perfil[/bold]")
        perfil_data = preguntar_perfil(console)

        console.print("\n[bold]Objetivos (opcional)[/bold]")
        objetivos_data = preguntar_objetivos(console)

        console.print("\n[bold]Actividad habitual (opcional)[/bold]")
        actividad_data = preguntar_actividad(console)

        data = SetupInput(
            **perfil_data,
            **objetivos_data,
            **actividad_data,
            modelo=modelo,
        )

        confirmado, data_final = confirmar_o_editar(console, data)
        if not confirmado:
            console.print("[yellow]Configuración cancelada.[/yellow]")
            return 2

        result = aplicar_setup(data_final, vault)
        if not result.ok:
            console.print("[red]No se pudo guardar la configuración:[/red]")
            for e in result.errores:
                console.print(f"  - {e.campo}: {e.mensaje}")
            return 1

        console.print("\n[green]Configuración guardada.[/green]")
        for r in result.rutas_escritas:
            console.print(f"  - {r}")
        if result.modelo:
            console.print(f"Modelo IA: {result.modelo}")
        else:
            console.print("Modo: solo memoria (sin IA).")
        console.print("\n[bold cyan]¡Bienvenido a NutricionAgent![/bold cyan]")
        return 0
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrumpido por el usuario.[/yellow]")
        return 2
    except VaultError as exc:
        console.print(f"[red]Error de almacenamiento: {exc}[/red]")
        return 1
    finally:
        client.close()


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()