"""Pruebas del alta de alimentos en el bucle."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from app.agent.loop import run_loop
from app.models.domain import Alimento
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


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


def test_alta_alimento_confirmada(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = (
        '{"tipo":"alta_alimento","id":"pavo",'
        '"nombre":"Pechuga de pavo","kcal_por_100":120,'
        '"proteina_g_por_100":22}'
    )
    # Confirm.ask -> True, luego /salir
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("añade pavo", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=True):
        rc = run_loop(vault, client, console)
    assert rc == 0
    a = vault.get_alimento("pavo")
    assert a is not None
    assert a.nombre == "Pechuga de pavo"
    assert a.kcal_por_100 == 120


def test_alta_alimento_cancelada_no_escribe(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = (
        '{"tipo":"alta_alimento","id":"pavo","nombre":"Pavo"}'
    )
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("añade pavo", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=False):
        rc = run_loop(vault, client, console)
    assert rc == 0
    assert vault.get_alimento("pavo") is None