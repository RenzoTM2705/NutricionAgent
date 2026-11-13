# Estado de NutricionAgent

Última actualización: Fase 4 completada.

## Entorno

- Proyecto: E:\Proyectos\NutricionAgent
- Bóveda: E:\Proyectos\NutricionAgent\data\vault
- Backups: E:\Proyectos\NutricionAgent\data\backups
- Modelos Ollama: E:\Ollama\models (variable OLLAMA_MODELS)
- Modelo activo: qwen3:4b-instruct-2507-q4_K_M (2.5 GB, Q4_K_M)
- Python: 3.12.10 en .venv
- Ollama: 0.40.16

## Fases completadas

- Fase 1: estructura portable, venv, .env, .gitignore, bóveda inicial, Git.
- Fase 2: app/ollama_client.py, app/config.py, app/errors.py. 20 tests.
- Fase 3: app/models/domain.py, app/storage/{fs,frontmatter,vault}.py. 92 tests.
- Fase 4: app/core/{results,errors,units,nutrition,metabolic}.py. 157 tests.
- Fase 5 — En curso

## Fase 5 — Completada

### Completado

- **5.1** — `app/setup/wizard.py`: lógica pura del asistente (`SetupInput`, `SetupResult`, `SetupError`, `aplicar_setup`, `perfil_existente`). 13 tests.
- **5.2** — `app/setup/console.py`: capa Rich, sin tests automáticos; verificada vía 5.4 y 5.6.
- **5.3** — `app/setup/checks.py`: estado de Ollama, prueba de modelo, mensajes al usuario. 10 tests.
- **5.4** — `app/main.py`: detecta perfil, lanza asistente si no hay, mensaje breve si hay. Probado con bóveda temporal.
- **5.5** — Omitida (tests de consola con mocks considerados frágiles; cobertura vía 5.6).
- **5.6** — `app/_smoke_setup.py`: flujo completo con Ollama real y bóveda temporal. Exit 0.

## Fase 6 — Completada

### Completado

- **6.1** — `app/agent/tools.py`: herramientas puras de dominio
  (`agregar_item`, `agregar_item_receta`, `eliminar_item_por_indice`,
  `listar_items`, `totales`, `buscar_alimentos`). 10 tests.
- **6.2** — `app/agent/operations.py`: 7 tipos de operación validados con
  Pydantic (`agregar_item`, `agregar_receta`, `eliminar_item`,
  `consultar_totales`, `listar_items`, `consultar_alimentos`,
  `responder`), `parsear_fecha`. 20 tests.
- **6.3** — `app/agent/interpreter.py`: lenguaje natural → operación
  validada. `_SISTEMA_PROMPT` con esquema, contexto dinámico (fecha,
  perfil, alimentos, recetas, totales), reintento único, escape a
  `responder`. 8 tests.
- **6.4** — `app/agent/loop.py`: bucle conversacional con Rich,
  `/hoy`, `/ayuda`, `/salir`, persistencia condicional, manejo de
  errores. 6 tests.
- **6.7** — `app/_smoke_agent.py`: humo real contra Ollama y bóveda
  temporal. Exit 0.

### Incidencia corregida

`interpretar` no incluía `_SISTEMA_PROMPT` en el prompt enviado al
modelo, solo el contexto. El modelo devolvía JSON reflejando el
contexto en lugar de la operación. Corregido anteponiendo el esquema
y envolviendo el contexto entre marcadores.

### Reglas fijadas

- Sin búsqueda externa. Todo vive en la bóveda.
- Si el alimento no existe, el agente responde con `responder` y
  sugiere darlo de alta (Fase 7).
- El modelo nunca decide la fecha “porque sí”: si la incluye, es
  porque el usuario la mencionó; el bucle la valida con `parsear_fecha`.

## Fase 7 — Completada

### Completado

- **7.1** — `main.py` entra al bucle si hay perfil; si no, asistente y luego bucle.
- **7.2** — Comandos locales en el bucle: `/hoy`, `/perfil`, `/objetivos`,
  `/actividad`, `/alimentos`, `/recetas`, `/modelo`, `/configurar`, `/ayuda`,
  `/salir`. Comandos desconocidos (`/...`) se rechazan sin llamar al modelo.
- **7.3** — Alta de alimentos conversacional (`AltaAlimentoOp`) con confirmación.
- **7.4** — Edición de items (`EditarItemOp`: cantidad, unidad, etiqueta)
  con confirmación.
- **7.6** — `app/_smoke_fase7.py`: humo real completo. Exit 0.

### Incidencia corregida

`main.py` usaba `root_for_backup = project_root / "data"` fijo, lo que rompía
`backup_file` cuando `NUTRICIONAGENT_DATA_DIR` apuntaba fuera del proyecto.
Corregido a `root_for_backup = data_dir.parent`, coherente con la bóveda
temporal y con la posibilidad de mover los datos a otro disco.

### Notas

- `/modelo` cambia el modelo solo en memoria; `.env` no se modifica.
- `/configurar` reabre el asistente con `sobrescribir=True` y confirmación.
- Las altas y ediciones piden confirmación antes de escribir.

## Siguiente

- Fase 8 — Actividad diaria y gasto energético.
- Fase 9 — Reportes.
- Fase 10 — Distribución.

## Reglas fijadas

- Nutrientes desconocidos: None, nunca 0.
- Fuente explícita: calculado, estimado, parcial, desconocido, pendiente.
- Recetas: si un ingrediente no aporta un nutriente, el total de ese nutriente es None y la fuente es PARCIAL.
- No se inventan densidades g↔ml; requiere que el alimento lo declare.
- El motor no escribe en la bóveda; solo lee y calcula.
- El motor no redondea; devuelve floats.
- Registro diario: lista plana de items (sin desayuno/almuerzo/cena).
- BMR: Mifflin-St Jeor. Factores de actividad estándar 1.2/1.375/1.55/1.725/1.9.
- .env y data/ excluidos de Git. Nunca commitear datos personales.

## Git

- Ramas: main, develop, feat/configuracion-ollama, feat/configuracion-contexto-md
- Commits: Fase 1, Fase 2, Fase 3, Fase 4.
- Remoto: origin (GitHub) con main y develop. Las ramas feat aún no se han subido.


- Fase 8: actividad y gasto.
- Fase 9: reportes.
- Fase 10: distribución.
- 
## Limpieza previa a perfil real

Tras cerrar la Fase 5, se han eliminado los datos de ejemplo generados por
los scripts de humo (`_smoke_ollama`, `_smoke_vault`, `_smoke_setup`):

- Registros de ejemplo en `data/vault/03-Registros/`.
- Alimentos, recetas y perfil de ejemplo en `data/vault/01-Perfil/` y
  `data/vault/02-Alimentos/` (restaurados a su contenido mínimo original).
- Logs y backups en `data/backups/`.

La bóveda queda lista para que el usuario configure su perfil real con
`python -m app.main`. No se ha tocado Git: `data/` sigue fuera del repo.

## Incidente: perfil vacío rompía el arranque

- **Síntoma:** `python -m app.main` fallaba con `VaultError` al leer
  `data/vault/01-Perfil/perfil.md` cuando el archivo existía pero solo
  tenía frontmatter (`tipo: perfil`, `version: 1`) sin datos.
- **Causa:** `Vault.read_perfil()` construía `Perfil(**meta)` sin filtrar
  las claves de frontmatter ajenas al modelo, y `Perfil` exige `edad`,
  `peso_kg`, `altura_cm` y prohíbe extras.
- **Fix:**
  - `Vault._read_typed` filtra `tipo` y `version` antes de construir.
  - `Vault.read_perfil` devuelve `None` si faltan `edad`, `peso_kg` o
    `altura_cm` (perfil no configurado), y lanza `VaultError` si los tres
    están pero son inválidos.
- **Tests:** `tests/test_vault_perfil_vacio.py` (3 nuevos). Se ajustó
  `test_read_corrupt_file_raises_vault_error` para usar un perfil
  completo pero inválido.

## Estado tras Fase 5

- Perfil real configurado por el usuario con `python -m app.main`.
- Actividad habitual guardada como referencia inicial.
- La actividad diaria real se añadirá en Fase 8 (el balance usará la
  actividad del día cuando exista, y solo caerá a la referencia si no).
