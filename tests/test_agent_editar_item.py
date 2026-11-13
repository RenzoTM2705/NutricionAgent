"""Pruebas de edición de items en el bucle."""

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
        Alimento(id="arroz", nombre="Arroz", kcal_por_100=130.0)
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


def test_editar_cantidad_confirmada(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.side_effect = [
        '{"tipo":"agregar_item","alimento_id":"arroz","cantidad":100,"unidad":"g"}',
        '{"tipo":"editar_item","indice":1,"cantidad":200}',
    ]
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("agrega 100 g", "cambia el 1 a 200", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=True):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg = vault.read_registro(date.today())
    assert reg is not None
    assert reg.items[0].cantidad == 200


def test_editar_cancelada_no_cambia(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.side_effect = [
        '{"tipo":"agregar_item","alimento_id":"arroz","cantidad":100,"unidad":"g"}',
        '{"tipo":"editar_item","indice":1,"cantidad":200}',
    ]
    # Confirmaciones: True para la primera (no hay confirm para agregar),
    # False para la edición. Como no hay confirm para agregar, solo una.
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("agrega 100 g", "cambia el 1 a 200", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=False):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg = vault.read_registro(date.today())
    assert reg is not None
    assert reg.items[0].cantidad == 100  # no cambió


def test_editar_indice_fuera_de_rango(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.side_effect = [
        '{"tipo":"agregar_item","alimento_id":"arroz","cantidad":100,"unidad":"g"}',
        '{"tipo":"editar_item","indice":5,"cantidad":200}',
    ]
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("agrega 100 g", "cambia el 5 a 200", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=True):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg = vault.read_registro(date.today())
    assert reg is not None
    assert reg.items[0].cantidad == 100  # sin cambios