"""Pruebas de registrar_actividad en el bucle."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from app.agent.loop import run_loop
from app.models.domain import Alimento, Perfil, Sexo
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    v = Vault(data, backups, root_for_backup=tmp_path)
    v.write_perfil(Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO))
    v.add_alimento(Alimento(id="arroz", nombre="Arroz", kcal_por_100=130.0))
    return v


def _console_silenciosa() -> Console:
    return Console(file=io.StringIO(), width=120)


def _lines(*lineas: str):
    it = iter(lineas)

    def _ask(*a, **k):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return _ask


def test_registrar_actividad_primera_vez(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = (
        '{"tipo":"registrar_actividad","pasos":9000,"gimnasio":true,'
        '"gimnasio_duracion_min":60}'
    )
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("hoy anduve 9000 pasos y fui al gimnasio 1 hora", "/salir"),
    ):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg = vault.read_registro(date.today())
    assert reg is not None
    assert reg.actividad_dia is not None
    assert reg.actividad_dia.pasos == 9000
    assert reg.actividad_dia.gimnasio is True
    assert reg.actividad_dia.gimnasio_duracion_min == 60


def test_registrar_actividad_sobrescribe_con_confirmacion(vault: Vault):
    from app.models.domain import ActividadDia

    # Primer registro: actividad simple
    reg = vault.read_registro(date.today())
    if reg is None:
        from app.models.domain import RegistroDiario
        reg = RegistroDiario(fecha=date.today())
    reg = reg.model_copy(update={"actividad_dia": ActividadDia(pasos=5000)})
    vault.write_registro(reg)

    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = (
        '{"tipo":"registrar_actividad","pasos":10000}'
    )
    # Confirm.ask -> True (sobrescribir)
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("anduve 10000 pasos", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=True):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg2 = vault.read_registro(date.today())
    assert reg2 is not None
    assert reg2.actividad_dia is not None
    assert reg2.actividad_dia.pasos == 10000


def test_registrar_actividad_cancelada_no_sobrescribe(vault: Vault):
    from app.models.domain import ActividadDia, RegistroDiario

    reg = RegistroDiario(
        fecha=date.today(), actividad_dia=ActividadDia(pasos=5000)
    )
    vault.write_registro(reg)

    console = _console_silenciosa()
    client = MagicMock()
    client.generate.return_value = '{"tipo":"registrar_actividad","pasos":10000}'
    with patch(
        "app.agent.loop.Prompt.ask",
        side_effect=_lines("anduve 10000 pasos", "/salir"),
    ), patch("app.agent.loop.Confirm.ask", return_value=False):
        rc = run_loop(vault, client, console)
    assert rc == 0
    reg2 = vault.read_registro(date.today())
    assert reg2 is not None
    assert reg2.actividad_dia is not None
    assert reg2.actividad_dia.pasos == 5000  # sin cambios