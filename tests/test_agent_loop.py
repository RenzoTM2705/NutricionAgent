"""Pruebas del bucle conversacional con consola y cliente mockeados."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from app.agent.loop import run_loop
from app.models.domain import Alimento, Unidad
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    v = Vault(data, backups, root_for_backup=tmp_path)
    v.add_alimento(
        Alimento(
            id="arroz",
            nombre="Arroz blanco cocido",
            kcal_por_100=130.0,
            proteina_g_por_100=2.7,
            grasa_g_por_100=0.3,
            carbo_g_por_100=28.0,
        )
    )
    return v


def _console_silenciosa() -> Console:
    return Console(file=io.StringIO(), width=120)


def _lines(*lineas: str):
    it = iter(lineas)

    def _ask(*args, **kwargs):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return _ask


def test_run_loop_salir_inmediato(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    with patch("app.agent.loop.Prompt.ask", side_effect=_lines("/salir")):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_not_called()


def test_run_loop_hoy_sin_items(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    with patch("app.agent.loop.Prompt.ask", side_effect=_lines("/hoy", "/salir")):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_not_called()


def test_run_loop_agrega_item_y_persiste(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = (
        '{"tipo":"agregar_item","alimento_id":"arroz","cantidad":150,"unidad":"g"}'
    )
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("agregué 150 g de arroz", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg = vault.read_registro(date.today())
    assert reg is not None
    assert len(reg.items) == 1
    assert reg.items[0].alimento_id == "arroz"


def test_run_loop_consulta_totales_no_persiste(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = '{"tipo":"consultar_totales"}'
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("¿cuántas kcal llevo?", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    assert vault.read_registro(date.today()) is None


def test_run_loop_elimina_item(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.side_effect = [
        '{"tipo":"agregar_item","alimento_id":"arroz","cantidad":150,"unidad":"g"}',
        '{"tipo":"eliminar_item","indice":1}',
    ]
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("agregué 150 g de arroz", "elimina el 1", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg = vault.read_registro(date.today())
    assert reg is not None
    assert len(reg.items) == 0


def test_run_loop_error_referencia_inexistente_no_rompe(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = (
        '{"tipo":"agregar_item","alimento_id":"pizza","cantidad":100,"unidad":"g"}'
    )
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("comí pizza", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    assert vault.read_registro(date.today()) is None

def test_run_loop_comando_desconocido_no_llama_al_modelo(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("/actividada", "/modelos", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_not_called()
    
def test_run_loop_lenguaje_natural_llama_al_modelo(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = '{"tipo":"consultar_totales"}'
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("¿cuántas kcal llevo?", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_called_once()