"""Pruebas de Vault para alimentos."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.domain import Alimento, Unidad
from app.storage.vault import DuplicateIdError, Vault, VaultError


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _alimento(id_="arroz", **kw) -> Alimento:
    base = dict(
        id=id_,
        nombre="Arroz blanco cocido",
        kcal_por_100=130.0,
        proteina_g_por_100=2.7,
        grasa_g_por_100=0.3,
        carbo_g_por_100=28.0,
        fuente="USDA",
    )
    base.update(kw)
    return Alimento(**base)


def test_read_missing_returns_empty(vault: Vault):
    assert vault.read_alimentos() == []


def test_add_get_roundtrip(vault: Vault):
    a = _alimento()
    vault.add_alimento(a)
    assert vault.alimentos_path.exists()

    got = vault.get_alimento("arroz")
    assert got is not None
    assert got.nombre == "Arroz blanco cocido"
    assert got.kcal_por_100 == 130.0
    assert got.unidad_base == Unidad.G


def test_add_duplicate_raises(vault: Vault):
    vault.add_alimento(_alimento())
    with pytest.raises(DuplicateIdError):
        vault.add_alimento(_alimento())


def test_remove_existente_devuelve_true(vault: Vault):
    vault.add_alimento(_alimento())
    assert vault.remove_alimento("arroz") is True
    assert vault.get_alimento("arroz") is None


def test_remove_inexistente_devuelve_false(vault: Vault):
    assert vault.remove_alimento("nope") is False


def test_write_multiples(vault: Vault):
    vault.write_alimentos([
        _alimento("a", nombre="A"),
        _alimento("b", nombre="B"),
        _alimento("c", nombre="C"),
    ])
    ids = [a.id for a in vault.read_alimentos()]
    assert ids == ["a", "b", "c"]


def test_roundtrip_valores_desconocidos(vault: Vault):
    # Sin kcal ni macros: None en el modelo, null en el archivo
    a = Alimento(id="agua", nombre="Agua")
    vault.add_alimento(a)
    got = vault.get_alimento("agua")
    assert got is not None
    assert got.kcal_por_100 is None
    assert got.proteina_g_por_100 is None


def test_roundtrip_strings_con_caracteres_especiales(vault: Vault):
    a = _alimento(
        id="yogur-griego",
        nombre='Yogur "griego" natural',
        marca="Marca: Ñandú",
        notas="contiene: leche, fermentos",
    )
    vault.add_alimento(a)
    got = vault.get_alimento("yogur-griego")
    assert got is not None
    assert got.nombre == 'Yogur "griego" natural'
    assert got.marca == "Marca: Ñandú"
    assert got.notas == "contiene: leche, fermentos"


def test_backup_on_overwrite(vault: Vault, tmp_path: Path):
    vault.add_alimento(_alimento())
    vault.add_alimento(_alimento("huevo", nombre="Huevo"))
    backups = list((tmp_path / "backups").rglob("alimentos-habituales.md"))
    assert len(backups) == 1


def test_bloque_corrupto_lanza_vault_error(vault: Vault):
    vault.alimentos_path.parent.mkdir(parents=True, exist_ok=True)
    vault.alimentos_path.write_text(
        "# Alimentos habituales\n\n## roto\n\n```yaml\nkcal_por_100: no-es-numero\n```\n",
        encoding="utf-8",
    )
    with pytest.raises(VaultError):
        vault.read_alimentos()