"""Pruebas de las herramientas del agente."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.agent.tools import (
    agregar_item,
    agregar_item_receta,
    buscar_alimentos,
    eliminar_item_por_indice,
    listar_items,
    totales,
)
from app.core.errors import ReferenciaInexistente
from app.models.domain import (
    Alimento,
    ItemComida,
    Receta,
    RegistroDiario,
    Unidad,
)
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _seed(vault: Vault) -> None:
    vault.add_alimento(
        Alimento(
            id="arroz",
            nombre="Arroz blanco cocido",
            kcal_por_100=130.0,
            proteina_g_por_100=2.7,
            grasa_g_por_100=0.3,
            carbo_g_por_100=28.0,
        )
    )
    vault.add_alimento(
        Alimento(
            id="pollo",
            nombre="Pechuga de pollo",
            kcal_por_100=165.0,
            proteina_g_por_100=31.0,
            grasa_g_por_100=3.6,
            carbo_g_por_100=0.0,
        )
    )
    vault.add_receta(
        Receta(
            id="arroz-pollo",
            nombre="Arroz con pollo",
            ingredientes=[],
            rendimiento_porciones=1.0,
        )
    )


def _reg() -> RegistroDiario:
    return RegistroDiario(fecha=date(2026, 11, 12))


def test_agregar_item(vault: Vault):
    _seed(vault)
    reg = agregar_item(_reg(), "arroz", 150, Unidad.G, vault=vault)
    assert len(reg.items) == 1
    assert reg.items[0].alimento_id == "arroz"
    assert reg.items[0].cantidad == 150


def test_agregar_item_con_etiqueta(vault: Vault):
    _seed(vault)
    reg = agregar_item(
        _reg(), "arroz", 150, Unidad.G, etiqueta="almuerzo", vault=vault
    )
    assert reg.items[0].etiqueta == "almuerzo"


def test_agregar_item_no_muta_original(vault: Vault):
    _seed(vault)
    reg0 = _reg()
    reg1 = agregar_item(reg0, "arroz", 150, Unidad.G, vault=vault)
    assert len(reg0.items) == 0
    assert len(reg1.items) == 1


def test_agregar_item_inexistente(vault: Vault):
    _seed(vault)
    with pytest.raises(ReferenciaInexistente):
        agregar_item(_reg(), "pizza", 100, Unidad.G, vault=vault)


def test_agregar_item_receta(vault: Vault):
    _seed(vault)
    reg = agregar_item_receta(_reg(), "arroz-pollo", 1, vault=vault)
    assert reg.items[0].receta_id == "arroz-pollo"


def test_eliminar_item_por_indice(vault: Vault):
    _seed(vault)
    reg = agregar_item(_reg(), "arroz", 100, Unidad.G, vault=vault)
    reg = agregar_item(reg, "pollo", 200, Unidad.G, vault=vault)
    reg = eliminar_item_por_indice(reg, 1)
    assert len(reg.items) == 1
    assert reg.items[0].alimento_id == "pollo"


def test_eliminar_fuera_de_rango(vault: Vault):
    with pytest.raises(IndexError):
        eliminar_item_por_indice(_reg(), 1)


def test_listar_items(vault: Vault):
    _seed(vault)
    reg = agregar_item(_reg(), "arroz", 150, Unidad.G, vault=vault)
    out = listar_items(reg, vault)
    assert len(out) == 1
    assert out[0]["indice"] == 1
    assert out[0]["ref_id"] == "arroz"
    assert out[0]["kcal"] == pytest.approx(195.0)


def test_totales(vault: Vault):
    _seed(vault)
    reg = agregar_item(_reg(), "arroz", 100, Unidad.G, vault=vault)
    reg = agregar_item(reg, "pollo", 100, Unidad.G, vault=vault)
    t = totales(reg, vault)
    assert t.total.kcal == pytest.approx(130.0 + 165.0)


def test_buscar_alimentos(vault: Vault):
    _seed(vault)
    assert [a.id for a in buscar_alimentos(vault, "arroz")] == ["arroz"]
    assert [a.id for a in buscar_alimentos(vault, "po")] == ["pollo"]
    assert buscar_alimentos(vault, "zzz") == []
    assert buscar_alimentos(vault, "") == []