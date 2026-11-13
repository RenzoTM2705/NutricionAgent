"""Pruebas del esquema de operaciones."""

from __future__ import annotations

from datetime import date

import pytest

from app.agent.operations import (
    AgregarItemOp,
    AgregarRecetaOp,
    ConsultarAlimentosOp,
    ConsultarTotalesOp,
    EliminarItemOp,
    ListarItemsOp,
    OperacionInvalida,
    ResponderOp,
    parsear_fecha,
    validar_operacion,
)
from app.models.domain import Unidad


def test_validar_agregar_item():
    op = validar_operacion(
        {
            "tipo": "agregar_item",
            "alimento_id": "arroz",
            "cantidad": 150,
            "unidad": "g",
        }
    )
    assert isinstance(op, AgregarItemOp)
    assert op.alimento_id == "arroz"
    assert op.cantidad == 150
    assert op.unidad == Unidad.G
    assert op.etiqueta is None
    assert op.fecha is None


def test_validar_agregar_receta():
    op = validar_operacion(
        {
            "tipo": "agregar_receta",
            "receta_id": "arroz-pollo",
            "cantidad": 1,
        }
    )
    assert isinstance(op, AgregarRecetaOp)
    assert op.unidad == Unidad.PORCION


def test_validar_eliminar_item():
    op = validar_operacion({"tipo": "eliminar_item", "indice": 2})
    assert isinstance(op, EliminarItemOp)
    assert op.indice == 2


def test_validar_eliminar_indice_cero_falla():
    with pytest.raises(OperacionInvalida):
        validar_operacion({"tipo": "eliminar_item", "indice": 0})


def test_validar_consultar_totales():
    op = validar_operacion({"tipo": "consultar_totales"})
    assert isinstance(op, ConsultarTotalesOp)


def test_validar_listar_items():
    op = validar_operacion({"tipo": "listar_items"})
    assert isinstance(op, ListarItemsOp)


def test_validar_consultar_alimentos():
    op = validar_operacion({"tipo": "consultar_alimentos", "texto": "arroz"})
    assert isinstance(op, ConsultarAlimentosOp)


def test_validar_responder():
    op = validar_operacion({"tipo": "responder", "mensaje": "no tengo pizza"})
    assert isinstance(op, ResponderOp)


def test_operacion_desconocida_falla():
    with pytest.raises(OperacionInvalida):
        validar_operacion({"tipo": "borrar_todo"})


def test_operacion_sin_tipo_falla():
    with pytest.raises(OperacionInvalida):
        validar_operacion({"alimento_id": "arroz"})


def test_operacion_extra_forbidden():
    with pytest.raises(OperacionInvalida):
        validar_operacion(
            {
                "tipo": "agregar_item",
                "alimento_id": "arroz",
                "cantidad": 100,
                "campo_extra": 1,
            }
        )


def test_agregar_item_sin_alimento_id_falla():
    with pytest.raises(OperacionInvalida):
        validar_operacion({"tipo": "agregar_item", "cantidad": 100})


def test_agregar_item_cantidad_negativa_falla():
    with pytest.raises(OperacionInvalida):
        validar_operacion(
            {"tipo": "agregar_item", "alimento_id": "arroz", "cantidad": -1}
        )


# --- parsear_fecha ---
def test_parsear_fecha_none_es_hoy():
    hoy = date(2026, 11, 12)
    assert parsear_fecha(None, hoy=hoy) == hoy
    assert parsear_fecha("", hoy=hoy) == hoy


def test_parsear_fecha_hoy_y_ayer():
    hoy = date(2026, 11, 12)
    assert parsear_fecha("hoy", hoy=hoy) == hoy
    assert parsear_fecha("ayer", hoy=hoy) == date(2026, 11, 11)


def test_parsear_fecha_iso():
    hoy = date(2026, 11, 12)
    assert parsear_fecha("2026-11-10", hoy=hoy) == date(2026, 11, 10)


def test_parsear_fecha_iso_invalida():
    with pytest.raises(OperacionInvalida):
        parsear_fecha("10/11/2026")


def test_parsear_fecha_futura_falla():
    hoy = date(2026, 11, 12)
    with pytest.raises(OperacionInvalida):
        parsear_fecha("2026-11-20", hoy=hoy)


def test_parsear_fecha_demasiado_antigua_falla():
    hoy = date(2026, 11, 12)
    with pytest.raises(OperacionInvalida):
        parsear_fecha("1999-12-31", hoy=hoy)

def test_validar_alta_alimento():
    from app.agent.operations import AltaAlimentoOp
    op = validar_operacion(
        {
            "tipo": "alta_alimento",
            "id": "pechuga-de-pavo",
            "nombre": "Pechuga de pavo",
            "kcal_por_100": 120.0,
            "proteina_g_por_100": 22.0,
        }
    )
    assert isinstance(op, AltaAlimentoOp)
    assert op.id == "pechuga-de-pavo"
    assert op.unidad_base == Unidad.G
    assert op.grasa_g_por_100 is None


def test_validar_alta_alimento_sin_nombre_falla():
    from app.agent.operations import OperacionInvalida
    with pytest.raises(OperacionInvalida):
        validar_operacion(
            {"tipo": "alta_alimento", "id": "x"}
        )

def test_validar_editar_item_cantidad():
    from app.agent.operations import EditarItemOp
    op = validar_operacion(
        {"tipo": "editar_item", "indice": 1, "cantidad": 200}
    )
    assert isinstance(op, EditarItemOp)
    assert op.cantidad == 200
    assert op.unidad is None
    assert op.etiqueta is None


def test_validar_editar_item_sin_cambios_falla():
    from app.agent.operations import OperacionInvalida
    with pytest.raises(OperacionInvalida):
        validar_operacion({"tipo": "editar_item", "indice": 1})


def test_validar_editar_item_indice_cero_falla():
    from app.agent.operations import OperacionInvalida
    with pytest.raises(OperacionInvalida):
        validar_operacion(
            {"tipo": "editar_item", "indice": 0, "cantidad": 100}
        )