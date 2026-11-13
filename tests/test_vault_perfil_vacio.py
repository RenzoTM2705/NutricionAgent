"""Perfil vacío con frontmatter -> read_perfil devuelve None, no error."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.vault import Vault, VaultError


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _escribir_perfil_vacio(vault: Vault) -> None:
    vault.perfil_path.parent.mkdir(parents=True, exist_ok=True)
    vault.perfil_path.write_text(
        "---\ntipo: perfil\nversion: 1\n---\n\n# Perfil\n\nPendiente.\n",
        encoding="utf-8",
    )


def test_perfil_vacio_devuelve_none(vault: Vault):
    _escribir_perfil_vacio(vault)
    assert vault.read_perfil() is None


def test_perfil_con_datos_pero_invalidos_lanza(vault: Vault):
    vault.perfil_path.parent.mkdir(parents=True, exist_ok=True)
    vault.perfil_path.write_text(
        "---\ntipo: perfil\nversion: 1\nedad: 0\npeso_kg: 75.0\n"
        "altura_cm: 178.0\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(VaultError):
        vault.read_perfil()


def test_perfil_valido_ignora_tipo_y_version(vault: Vault):
    vault.perfil_path.parent.mkdir(parents=True, exist_ok=True)
    vault.perfil_path.write_text(
        "---\ntipo: perfil\nversion: 1\nedad: 30\npeso_kg: 75.0\n"
        "altura_cm: 178.0\nsexo: masculino\n---\n",
        encoding="utf-8",
    )
    p = vault.read_perfil()
    assert p is not None
    assert p.edad == 30