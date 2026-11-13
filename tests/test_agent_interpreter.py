"""Pruebas del intérprete con cliente mockeado (sin red real)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.agent.interpreter import construir_contexto, interpretar
from app.agent.operations import (
    AgregarItemOp,
    ConsultarAlimentosOp,
    ConsultarTotalesOp,
    ResponderOp,
)
from app.models.domain import (
    Alimento,
    Receta,
    RegistroDiario,
)
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    v = Vault(data, backups, root_for_backup=tmp_path)
    v.add_alimento(
        Alimento(id="arroz", nombre="Arroz blanco cocido", kcal_por_100=130.0)
    )
    v.add_alimento(
        Alimento(id="pollo", nombre="Pechuga de pollo", kcal_por_100=165.0)
    )
    v.add_receta(
        Receta(
            id="arroz-pollo",
            nombre="Arroz con pollo",
            ingredientes=[],
            rendimiento_porciones=1.0,
        )
    )
    return v


def _client_respuesta(raw_json: str) -> MagicMock:
    c = MagicMock()
    c.generate.return_value = raw_json
    return c


def test_contexto_incluye_alimentos_y_recetas(vault: Vault):
    ctx = construir_contexto(vault, hoy=date(2026, 11, 12))
    assert "2026-11-12" in ctx
    assert "arroz" in ctx
    assert "pollo" in ctx
    assert "arroz-pollo" in ctx
    assert "sin registro" in ctx


def test_interpretar_agregar_item(vault: Vault):
    client = _client_respuesta(
        '{"tipo":"agregar_item","alimento_id":"arroz","cantidad":150,"unidad":"g"}'
    )
    op = interpretar("agregué 150 g de arroz", vault=vault, client=client)
    assert isinstance(op, AgregarItemOp)
    assert op.alimento_id == "arroz"
    assert op.cantidad == 150
    client.generate.assert_called_once()


def test_interpretar_consultar_totales(vault: Vault):
    client = _client_respuesta('{"tipo":"consultar_totales"}')
    op = interpretar("¿cuántas kcal llevo hoy?", vault=vault, client=client)
    assert isinstance(op, ConsultarTotalesOp)


def test_interpretar_consultar_alimentos(vault: Vault):
    client = _client_respuesta(
        '{"tipo":"consultar_alimentos","texto":"arroz"}'
    )
    op = interpretar("busca arroz", vault=vault, client=client)
    assert isinstance(op, ConsultarAlimentosOp)


def test_interpretar_json_invalido_reintenta_y_falla(vault: Vault):
    client = MagicMock()
    client.generate.side_effect = ["no json", "tampoco json"]
    op = interpretar("dime algo", vault=vault, client=client)
    assert isinstance(op, ResponderOp)
    assert "No he podido interpretar" in op.mensaje
    assert client.generate.call_count == 2


def test_interpretar_json_invalido_reintenta_y_acierta(vault: Vault):
    client = MagicMock()
    client.generate.side_effect = [
        "no json",
        '{"tipo":"consultar_totales"}',
    ]
    op = interpretar("dime algo", vault=vault, client=client)
    assert isinstance(op, ConsultarTotalesOp)
    assert client.generate.call_count == 2


def test_interpretar_operacion_desconocida_falla(vault: Vault):
    client = MagicMock()
    client.generate.side_effect = [
        '{"tipo":"borrar_todo"}',
        '{"tipo":"borrar_todo"}',
    ]
    op = interpretar("haz algo", vault=vault, client=client)
    assert isinstance(op, ResponderOp)


def test_interpretar_con_registro_en_contexto(vault: Vault):
    from app.agent.tools import agregar_item
    from app.models.domain import Unidad

    reg = agregar_item(
        RegistroDiario(fecha=date(2026, 11, 12)),
        "arroz", 100, Unidad.G, vault=vault,
    )
    client = _client_respuesta('{"tipo":"consultar_totales"}')
    interpretar("total", vault=vault, client=client, registro=reg)
    # El prompt debe mencionar los totales
    prompt_usado = client.generate.call_args.args[0]
    assert "Totales del día" in prompt_usado
    assert "Items registrados hoy: 1" in prompt_usado