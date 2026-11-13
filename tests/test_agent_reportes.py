"""Pruebas de los comandos de reporte en el bucle."""

from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from app.agent.loop import run_loop
from app.models.domain import Alimento, ItemComida, Perfil, RegistroDiario, Sexo, Unidad
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    v = Vault(data, backups, root_for_backup=tmp_path)
    v.write_perfil(Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO))
    v.add_alimento(Alimento(id="arroz", nombre="Arroz", kcal_por_100=100.0))
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


def test_reporte_diario_escribe_archivo(vault: Vault):
    reg = RegistroDiario(
        fecha=date.today(),
        items=[ItemComida(alimento_id="arroz", cantidad=100, unidad=Unidad.G)],
    )
    vault.write_registro(reg)
    console = _console_silenciosa()
    client = MagicMock()
    with patch("app.agent.loop.Prompt.ask", side_effect=_lines("/reporte", "/salir")):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_not_called()
    path = vault.data_dir / "04-Reportes" / "diarios" / f"{date.today().isoformat()}.md"
    assert path.exists()


def test_reporte_semana_escribe_archivo(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    with patch("app.agent.loop.Prompt.ask", side_effect=_lines("/reporte-semana", "/salir")):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_not_called()
    files = list((vault.data_dir / "04-Reportes" / "semanales").glob("*.md"))
    assert len(files) == 1


def test_reporte_mes_escribe_archivo(vault: Vault):
    console = _console_silenciosa()
    client = MagicMock()
    with patch("app.agent.loop.Prompt.ask", side_effect=_lines("/reporte-mes", "/salir")):
        rc = run_loop(vault, client, console)
    assert rc == 0
    client.generate.assert_not_called()
    files = list((vault.data_dir / "04-Reportes" / "mensuales").glob("*.md"))
    assert len(files) == 1