"""Pruebas de Vault (perfil, objetivos, actividad) con tmp_path."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.domain import ActividadHabitual, Objetivos, Perfil, Sexo
from app.storage.vault import Vault, VaultError


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def test_read_missing_returns_none(vault: Vault):
    assert vault.read_perfil() is None
    assert vault.read_objetivos() is None
    assert vault.read_actividad() is None


def test_perfil_roundtrip(vault: Vault):
    p = Perfil(edad=30, peso_kg=75.0, altura_cm=178.0, sexo=Sexo.MASCULINO)
    vault.write_perfil(p)
    assert vault.perfil_path.exists()
    p2 = vault.read_perfil()
    assert p2 is not None
    assert p2.edad == 30
    assert p2.sexo == Sexo.MASCULINO


def test_objetivos_roundtrip(vault: Vault):
    o = Objetivos(kcal_diarias=2200, proteina_g=150)
    vault.write_objetivos(o)
    o2 = vault.read_objetivos()
    assert o2 is not None
    assert o2.kcal_diarias == 2200
    assert o2.proteina_g == 150


def test_actividad_roundtrip(vault: Vault):
    a = ActividadHabitual(tipo_trabajo="oficina", horas_actividad_laboral=8)
    vault.write_actividad(a)
    a2 = vault.read_actividad()
    assert a2 is not None
    assert a2.tipo_trabajo == "oficina"
    assert a2.horas_actividad_laboral == 8


def test_backup_created_on_overwrite(vault: Vault, tmp_path: Path):
    p = Perfil(edad=30, peso_kg=75.0, altura_cm=178.0)
    vault.write_perfil(p)
    vault.write_perfil(p)  # sobrescribe
    backups = list((tmp_path / "backups").rglob("perfil.md"))
    assert len(backups) == 1


def test_read_corrupt_file_raises_vault_error(vault: Vault):
    # Perfil completo pero con un dato inválido (edad 0) -> VaultError.
    vault.perfil_path.parent.mkdir(parents=True, exist_ok=True)
    vault.perfil_path.write_text(
        "---\nedad: 0\npeso_kg: 75.0\naltura_cm: 178.0\n---\n",
        encoding="utf-8",
    )
    with pytest.raises(VaultError):
        vault.read_perfil()