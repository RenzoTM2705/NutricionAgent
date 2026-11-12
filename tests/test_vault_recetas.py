"""Pruebas de Vault para recetas."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.domain import IngredienteReceta, Receta, Unidad
from app.storage.vault import DuplicateIdError, Vault, VaultError


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _receta(id_="arroz-con-pollo", **kw) -> Receta:
    base = dict(
        id=id_,
        nombre="Arroz con pollo",
        ingredientes=[
            IngredienteReceta(alimento_id="arroz", cantidad=150.0, unidad=Unidad.G),
            IngredienteReceta(alimento_id="pollo", cantidad=200.0, unidad=Unidad.G),
        ],
        rendimiento_porciones=2.0,
    )
    base.update(kw)
    return Receta(**base)


def test_read_missing_returns_empty(vault: Vault):
    assert vault.read_recetas() == []


def test_add_get_roundtrip(vault: Vault):
    r = _receta()
    vault.add_receta(r)
    assert vault.recetas_path.exists()
    got = vault.get_receta("arroz-con-pollo")
    assert got is not None
    assert got.nombre == "Arroz con pollo"
    assert got.rendimiento_porciones == 2.0
    assert len(got.ingredientes) == 2
    assert got.ingredientes[0].alimento_id == "arroz"
    assert got.ingredientes[0].cantidad == 150.0
    assert got.ingredientes[0].unidad == Unidad.G


def test_add_duplicate_raises(vault: Vault):
    vault.add_receta(_receta())
    with pytest.raises(DuplicateIdError):
        vault.add_receta(_receta())


def test_remove_existente(vault: Vault):
    vault.add_receta(_receta())
    assert vault.remove_receta("arroz-con-pollo") is True
    assert vault.get_receta("arroz-con-pollo") is None


def test_remove_inexistente(vault: Vault):
    assert vault.remove_receta("nope") is False


def test_write_multiples(vault: Vault):
    vault.write_recetas([
        _receta("a", nombre="A", ingredientes=[]),
        _receta("b", nombre="B", ingredientes=[]),
    ])
    ids = [r.id for r in vault.read_recetas()]
    assert ids == ["a", "b"]


def test_roundtrip_sin_ingredientes(vault: Vault):
    r = _receta("vacia", ingredientes=[])
    vault.add_receta(r)
    got = vault.get_receta("vacia")
    assert got is not None
    assert got.ingredientes == []


def test_roundtrip_strings_especiales(vault: Vault):
    r = _receta(
        "raro",
        nombre='Receta "especial" con : dos puntos',
        notas="contiene: leche, huevo",
        ingredientes=[
            IngredienteReceta(
                alimento_id="yogur-griego", cantidad=100.0, unidad=Unidad.G
            ),
        ],
    )
    vault.add_receta(r)
    got = vault.get_receta("raro")
    assert got is not None
    assert got.nombre == 'Receta "especial" con : dos puntos'
    assert got.notas == "contiene: leche, huevo"
    assert got.ingredientes[0].alimento_id == "yogur-griego"


def test_backup_on_overwrite(vault: Vault, tmp_path: Path):
    vault.add_receta(_receta("a", nombre="A", ingredientes=[]))
    vault.add_receta(_receta("b", nombre="B", ingredientes=[]))
    backups = list((tmp_path / "backups").rglob("recetas.md"))
    assert len(backups) == 1


def test_archivo_corrupto_lanza_vault_error(vault: Vault):
    vault.recetas_path.parent.mkdir(parents=True, exist_ok=True)
    vault.recetas_path.write_text(
        "# Recetas\n\n## rota\n\n```yaml\nnombre: sin cierre\n",
        encoding="utf-8",
    )
    with pytest.raises(VaultError):
        vault.read_recetas()