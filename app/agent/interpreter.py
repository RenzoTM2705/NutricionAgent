"""Intérprete de lenguaje natural → operación validada.

Habla con Ollama vía OllamaClient. No ejecuta operaciones.
Devuelve una Operacion validada; el bucle la ejecuta.
"""

from __future__ import annotations

import json
from datetime import date
from typing import Optional

from app.agent.operations import (
    Operacion,
    OperacionInvalida,
    ResponderOp,
    validar_operacion,
)
from app.core.nutrition import calcular_totales_dia
from app.core.results import TotalesDia
from app.models.domain import (
    ActividadHabitual,
    Alimento,
    Perfil,
    Receta,
    RegistroDiario,
)
from app.ollama_client import OllamaClient, OllamaError
from app.storage.vault import Vault


_SISTEMA_PROMPT = """Eres el intérprete de NutricionAgent. Tu única tarea es \
convertir el mensaje del usuario en UNA operación JSON válida.

Operaciones disponibles (responde SOLO con un objeto JSON que tenga una de \
estas formas; no añadas texto fuera del JSON):

1. Agregar un alimento existente:
   {"tipo": "agregar_item", "alimento_id": "<id>", "cantidad": <número>, \
"unidad": "g"|"ml"|"unidad"|"porcion", "etiqueta": <string|null>, \
"fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

2. Agregar una receta existente:
   {"tipo": "agregar_receta", "receta_id": "<id>", "cantidad": <número>, \
"unidad": "porcion", "etiqueta": <string|null>, \
"fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

3. Eliminar un item por su índice (1 = primero):
   {"tipo": "eliminar_item", "indice": <entero >= 1>, \
"fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

4. Editar un item existente por su índice (1 = primero). Al menos uno
   de cantidad, unidad o etiqueta debe indicarse:
   {"tipo": "editar_item", "indice": <entero >= 1>,
    "cantidad": <número|null>, "unidad": "g"|"ml"|"unidad"|"porcion"|null,
    "etiqueta": <string|null>, "fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

5. Consultar totales del día:
   {"tipo": "consultar_totales", "fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

6. Listar los items del día:
   {"tipo": "listar_items", "fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

7. Buscar alimentos en la bóveda por texto:
   {"tipo": "consultar_alimentos", "texto": "<subcadena>"}

8. Dar de alta un alimento nuevo (solo si el usuario lo pide explícitamente
   y proporciona al menos nombre y algún valor nutricional o deja claro
   que los desconoce):
   {"tipo": "alta_alimento", "id": "<id-slug-sin-espacios>",
    "nombre": "<nombre>", "marca": <string|null>,
    "unidad_base": "g"|"ml"|"unidad"|"porcion",
    "peso_referencia_g": <número|null>,
    "kcal_por_100": <número|null>, "proteina_g_por_100": <número|null>,
    "grasa_g_por_100": <número|null>, "carbo_g_por_100": <número|null>,
    "fuente": <string|null>, "notas": <string|null>}

9. Registrar la actividad del día:
   {"tipo": "registrar_actividad",
    "horas_trabajo": <número|null>, "horas_de_pie": <número|null>,
    "pasos": <entero|null>, "gimnasio": <true|false|null>,
    "gimnasio_duracion_min": <entero|null>,
    "tipo_entrenamiento": <string|null>, "otros_deportes": <string|null>,
    "notas": <string|null>, "fecha": <"YYYY-MM-DD"|"hoy"|"ayer"|null>}

10. Responder sin ejecutar nada (aclaraciones, errores, saludos):
   {"tipo": "responder", "mensaje": "<texto>"}    


Reglas:
- Usa SOLO los ids de alimentos y recetas que aparecen en el contexto.
- Si el usuario menciona un alimento que NO está en la lista, usa "responder" \
para avisar de que no está en la bóveda y sugiere buscarlo o darlo de alta.
- No inventes alimentos ni cantidades.
- Si la cantidad no está clara, usa "responder" para preguntar.
- Si el usuario menciona "ayer", usa fecha="ayer". Si no menciona fecha, \
usa fecha=null (el sistema usará hoy).
- No devuelvas nada más que el objeto JSON.
- Si el usuario pide añadir un alimento que no existe, propone "alta_alimento"
  con los datos que dé. No inventes valores: deja null los que no dé.
- El id del alimento nuevo debe ser un slug sin espacios (minúsculas, guiones).
- Para borrar la etiqueta de un item, usa "etiqueta": "".
- editar_item no cambia el alimento ni la receta; solo cantidad, unidad o etiqueta.
- Si el usuario describe su actividad del día ("hoy trabajé 8 h", "fui al
  gimnasio 1 h", "anduve 9000 pasos"), usa "registrar_actividad" con los
  datos que dé. No inventes valores: deja null los que no dé.
"""


def _resumen_perfil(perfil: Optional[Perfil]) -> str:
    if perfil is None:
        return "Perfil no configurado."
    return (
        f"Edad: {perfil.edad}; Peso: {perfil.peso_kg} kg; "
        f"Altura: {perfil.altura_cm} cm; Sexo: {perfil.sexo.value}; "
        f"Objetivo: {perfil.objetivo.value}"
    )


def _lista_alimentos(alimentos: list[Alimento], limite: int = 30) -> str:
    if not alimentos:
        return "(sin alimentos en la bóveda)"
    items = [f"{a.id}: {a.nombre}" for a in alimentos[:limite]]
    if len(alimentos) > limite:
        items.append(f"... y {len(alimentos) - limite} más")
    return "; ".join(items)


def _lista_recetas(recetas: list[Receta], limite: int = 20) -> str:
    if not recetas:
        return "(sin recetas en la bóveda)"
    items = [f"{r.id}: {r.nombre}" for r in recetas[:limite]]
    if len(recetas) > limite:
        items.append(f"... y {len(recetas) - limite} más")
    return "; ".join(items)


def _resumen_totales(t: TotalesDia) -> str:
    def v(x: Optional[float]) -> str:
        return "desconocido" if x is None else f"{x:.1f}"

    return (
        f"{v(t.total.kcal)} kcal, {v(t.total.proteina_g)} g prot, "
        f"{v(t.total.grasa_g)} g grasa, {v(t.total.carbo_g)} g carb "
        f"(fuente: {t.fuente.value})"
    )


def construir_contexto(
    vault: Vault,
    *,
    registro: Optional[RegistroDiario] = None,
    hoy: Optional[date] = None,
) -> str:
    """Construye el bloque de contexto que se pasa al modelo."""
    hoy = hoy or date.today()
    perfil = vault.read_perfil()
    alimentos = vault.read_alimentos()
    recetas = vault.read_recetas()

    lineas = [
        f"Fecha actual: {hoy.isoformat()}",
        f"Perfil: {_resumen_perfil(perfil)}",
        f"Alimentos disponibles: {_lista_alimentos(alimentos)}",
        f"Recetas disponibles: {_lista_recetas(recetas)}",
    ]
    if registro is not None:
        totales = calcular_totales_dia(registro, vault)
        lineas.append(f"Totales del día: {_resumen_totales(totales)}")
        lineas.append(f"Items registrados hoy: {len(registro.items)}")
    else:
        lineas.append("Totales del día: (sin registro)")

    return "\n".join(lineas)


def interpretar(
    mensaje: str,
    *,
    vault: Vault,
    client: OllamaClient,
    registro: Optional[RegistroDiario] = None,
    hoy: Optional[date] = None,
    max_reintentos: int = 1,
) -> Operacion:
    """Convierte `mensaje` en una Operacion validada.

    - Envía el mensaje + contexto al modelo con format=json.
    - Valida contra el esquema. Reintenta una vez si falla.
    - Si tras los reintentos sigue fallando, devuelve ResponderOp con error.
    - Lanza OllamaNotRunning si el servicio no responde.
    """
    contexto = construir_contexto(vault, registro=registro, hoy=hoy)
    prompt_base = (
        f"{_SISTEMA_PROMPT}\n\n"
        f"--- CONTEXTO ---\n{contexto}\n--- FIN CONTEXTO ---\n\n"
        f"Mensaje del usuario: {mensaje}"
    )
    opciones = {"temperature": 0.0, "num_ctx": 4096, "num_predict": 256}

    ultimo_error: Optional[str] = None
    for intento in range(max_reintentos + 1):
        if intento == 0:
            prompt = prompt_base
        else:
            prompt = (
                f"{_SISTEMA_PROMPT}\n\n"
                f"--- CONTEXTO ---\n{contexto}\n--- FIN CONTEXTO ---\n\n"
                f"Mensaje del usuario: {mensaje}\n\n"
                f"Tu respuesta anterior no fue válida: {ultimo_error}\n"
                f"Responde SOLO con un objeto JSON que tenga uno de los campos "
                f"'tipo' permitidos: agregar_item, agregar_receta, "
                f"eliminar_item, consultar_totales, listar_items, "
                f"consultar_alimentos, responder. No añadas texto fuera del JSON."
            )
        try:
            raw = client.generate(
                prompt,
                format_json=True,
                options=opciones,
            )
        except OllamaError:
            raise

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            ultimo_error = f"JSON no parseable: {exc}"
            continue

        try:
            return validar_operacion(data)
        except OperacionInvalida as exc:
            ultimo_error = str(exc)
            continue

    return ResponderOp(
        tipo="responder",
        mensaje=(
            "No he podido interpretar la petición como una operación válida. "
            f"Detalle: {ultimo_error}. Reformúlalo, por favor."
        ),
    )