"""Herramientas de dominio para el agente.

Funciones puras sobre RegistroDiario + Vault. No escriben en disco.
El bucle conversacional decide cuándo persistir con vault.write_registro.
"""

from __future__ import annotations

from typing import Optional

from app.core.errors import ReferenciaInexistente
from app.core.nutrition import calcular_item, calcular_totales_dia
from app.core.results import ItemCalculado, TotalesDia
from app.models.domain import (
    Alimento,
    ItemComida,
    RegistroDiario,
    Unidad,
)
from app.storage.vault import Vault


def agregar_item(
    registro: RegistroDiario,
    alimento_id: str,
    cantidad: float,
    unidad: Unidad,
    *,
    etiqueta: Optional[str] = None,
    vault: Vault,
) -> RegistroDiario:
    """Devuelve un nuevo RegistroDiario con el item añadido.

    Valida que el alimento exista en la bóveda.
    """
    if vault.get_alimento(alimento_id) is None:
        raise ReferenciaInexistente(
            f"No existe el alimento {alimento_id!r} en la bóveda."
        )
    item = ItemComida(
        alimento_id=alimento_id,
        cantidad=cantidad,
        unidad=unidad,
        etiqueta=etiqueta,
    )
    return registro.model_copy(
        update={"items": [*registro.items, item]}
    )


def agregar_item_receta(
    registro: RegistroDiario,
    receta_id: str,
    cantidad: float,
    *,
    unidad: Unidad = Unidad.PORCION,
    etiqueta: Optional[str] = None,
    vault: Vault,
) -> RegistroDiario:
    """Devuelve un nuevo RegistroDiario con el item de receta añadido."""
    if vault.get_receta(receta_id) is None:
        raise ReferenciaInexistente(
            f"No existe la receta {receta_id!r} en la bóveda."
        )
    item = ItemComida(
        receta_id=receta_id,
        cantidad=cantidad,
        unidad=unidad,
        etiqueta=etiqueta,
    )
    return registro.model_copy(
        update={"items": [*registro.items, item]}
    )


def eliminar_item_por_indice(
    registro: RegistroDiario, indice_1based: int
) -> RegistroDiario:
    """Elimina el item en la posición `indice_1based` (1 = primero)."""
    if indice_1based < 1 or indice_1based > len(registro.items):
        raise IndexError(
            f"Índice fuera de rango: {indice_1based}. "
            f"Hay {len(registro.items)} item(s)."
        )
    idx = indice_1based - 1
    nuevos = [it for i, it in enumerate(registro.items) if i != idx]
    return registro.model_copy(update={"items": nuevos})


def listar_items(
    registro: RegistroDiario, vault: Vault
) -> list[dict]:
    """Lista los items con sus nutrientes calculados, para mostrar al usuario."""
    out: list[dict] = []
    for i, it in enumerate(registro.items, start=1):
        calc: ItemCalculado = calcular_item(it, vault)
        out.append(
            {
                "indice": i,
                "ref_tipo": calc.ref_tipo,
                "ref_id": calc.ref_id,
                "cantidad": calc.cantidad,
                "unidad": calc.unidad.value,
                "etiqueta": it.etiqueta,
                "kcal": calc.nutrientes.kcal,
                "proteina_g": calc.nutrientes.proteina_g,
                "grasa_g": calc.nutrientes.grasa_g,
                "carbo_g": calc.nutrientes.carbo_g,
                "fuente": calc.fuente.value,
            }
        )
    return out


def totales(registro: RegistroDiario, vault: Vault) -> TotalesDia:
    """Totales del día. Alias de calcular_totales_dia para el agente."""
    return calcular_totales_dia(registro, vault)


def buscar_alimentos(
    vault: Vault, texto: str, *, limite: int = 10
) -> list[Alimento]:
    """Busca alimentos por subcadena en id o nombre (case-insensitive)."""
    q = texto.strip().lower()
    if not q:
        return []
    out: list[Alimento] = []
    for a in vault.read_alimentos():
        if q in a.id.lower() or q in a.nombre.lower():
            out.append(a)
            if len(out) >= limite:
                break
    return out