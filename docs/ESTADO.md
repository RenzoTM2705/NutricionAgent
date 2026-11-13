# Estado de NutricionAgent

Última actualización: Fase 10 en curso (10.1–10.3 completadas).

## Entorno

- Proyecto: E:\Proyectos\NutricionAgent
- Bóveda desarrollo: E:\Proyectos\NutricionAgent\data\vault
- Bóveda ejecutable: %LOCALAPPDATA%\NutricionAgent\data\vault
- Backups: <data_dir>.parent\backups
- Modelos Ollama: E:\Ollama\models (variable OLLAMA_MODELS)
- Modelo activo: qwen3:4b-instruct-2507-q4_K_M (2.5 GB, Q4_K_M)
- Python: 3.12.10 en .venv
- Ollama: 0.40.16
- PyInstaller: 6.x
- Inno Setup: 6.x (pendiente de confirmar instalación)

## Fases completadas

### Fase 1 — Estructura portable
Estructura de carpetas, venv, .env, .env.example, .gitignore,
bóveda inicial, Git. Sin tests.

### Fase 2 — Cliente Ollama (20 tests)
`app/ollama_client.py`, `app/config.py`, `app/errors.py`.
Conexión, ping, versión, listado de modelos, selección, prueba de
respuesta y JSON estructurado.

### Fase 3 — Sistema de memoria (92 tests)
`app/models/domain.py`, `app/storage/{fs,frontmatter,vault}.py`.
Modelos Pydantic, escritura atómica, backups con retención,
parser de frontmatter, Vault para perfil, objetivos, actividad,
alimentos, recetas y registro diario.

### Fase 4 — Motor nutricional (157 tests)
`app/core/{results,errors,units,nutrition,metabolic}.py`.
Conversión de unidades, cálculo por item, totales diarios, recetas,
BMR (Mifflin-St Jeor), factor de actividad, TDEE y balance.
Regla estricta: nutrientes desconocidos = None, nunca 0.

### Fase 5 — Asistente de configuración inicial
- `app/setup/wizard.py`: lógica pura. 13 tests.
- `app/setup/console.py`: capa Rich.
- `app/setup/checks.py`: estado de Ollama y mensajes. 10 tests.
- `app/main.py`: detecta perfil y lanza asistente o bucle.
- `app/_smoke_setup.py`: humo real. Exit 0.

### Fase 6 — Agente conversacional
- `app/agent/tools.py`: herramientas puras. 10 tests.
- `app/agent/operations.py`: operaciones validadas con Pydantic. 20 tests.
- `app/agent/interpreter.py`: lenguaje natural → operación. 8 tests.
- `app/agent/loop.py`: bucle conversacional. 6 tests.
- `app/_smoke_agent.py`: humo real. Exit 0.

**Incidencia corregida:** `interpretar` no incluía `_SISTEMA_PROMPT`;
el modelo devolvía JSON reflejando el contexto. Corregido.

### Fase 7 — Comandos, edición e integración con main
- `main.py` entra al bucle si hay perfil.
- Comandos: `/hoy`, `/perfil`, `/objetivos`, `/actividad`,
  `/alimentos`, `/recetas`, `/modelo`, `/configurar`, `/ayuda`, `/salir`.
- Comandos desconocidos (`/...`) se rechazan sin llamar al modelo.
- Alta de alimentos (`AltaAlimentoOp`) con confirmación.
- Edición de items (`EditarItemOp`) con confirmación.
- `app/_smoke_fase7.py`: humo real. Exit 0.

**Incidencia corregida:** `main.py` usaba `root_for_backup = project_root / "data"`
fijo. Cambiado a `data_dir.parent` para soportar bóvedas fuera del proyecto.

### Fase 8 — Actividad del día y balance real
- `ActividadDia` en `domain.py` y `RegistroDiario.actividad_dia`. 8 tests.
- Serialización `dia_<campo>` en `Vault`. 6 tests.
- `calcular_tdee_dia` en `metabolic.py`. 9 tests.
- `calcular_balance` usa `calcular_tdee_dia`. 10 tests.
- Operación `registrar_actividad` en el agente, con confirmación
  solo al sobrescribir.
- `app/_smoke_fase8.py`: humo real. Exit 0.

### Fase 9 — Reportes
- `app/core/report_models.py`: modelos de reporte. 9 tests.
- `app/core/reports.py`: generación diaria, semanal, mensual. 8 tests.
- `Vault`: `write_reporte_*` / `read_reporte_*`. 8 tests.
- Comandos `/reporte`, `/reporte-semana`, `/reporte-mes`. 3 tests.
- `app/_smoke_fase9.py`: humo real. Exit 0.

## Fase 10 — Distribución (en curso)

### Completado

- **10.1** — `docs/DISTRIBUCION.md`: diseño del empaquetado.
  `requirements-dev.txt` con PyInstaller.
- **10.2** — `app/config.py` adaptado a modo congelado:
  - Detecta `sys.frozen` y `sys._MEIPASS`.
  - `data_dir`: `%LOCALAPPDATA%\NutricionAgent\data\vault` por defecto
    en modo congelado. `NUTRICIONAGENT_DATA_DIR` sigue teniendo prioridad.
  - `.env`: `%LOCALAPPDATA%\NutricionAgent\.env`, creado desde
    `.env.example` la primera vez.
  - `backup_root = data_dir.parent / "backups"`.
- **10.3** — PyInstaller:
  - `nutricionagent.spec` (onedir, console=True, sin UPX).
  - `run.py` como entry point.
  - Ejecutable generado en `dist/NutricionAgent/`.
  - Probado en local: arranca, asistente, perfil guardado en
    `%LOCALAPPDATA%\NutricionAgent\data\vault\01-Perfil\perfil.md`,
    `.env` creado a partir de `.env.example`.

### Pendiente

- **10.4** — Inno Setup: `installer.iss`, instalador por usuario,
  accesos directos, aviso de Ollama, preservación de datos.
- **10.5** — GitHub Releases: plantilla de release, checksum,
  workflow opcional.
- **10.6** — Prueba en máquina limpia.
- **10.7** — Commit de Fase 10 y cierre de `docs/ESTADO.md`.

## Reglas fijadas (todas las fases)

- Nutrientes desconocidos: `None`, nunca `0`.
- Fuente explícita: calculado, estimado, parcial, desconocido, pendiente.
- Recetas: si un ingrediente no aporta un nutriente, el total de ese
  nutriente es `None` y la fuente es `PARCIAL`.
- No se inventan densidades g↔ml; requiere que el alimento lo declare.
- El motor no escribe en la bóveda; solo lee y calcula.
- El motor no redondea; devuelve floats.
- Registro diario: lista plana de items (sin desayuno/almuerzo/cena).
- BMR: Mifflin-St Jeor. Factores de actividad 1.2 / 1.375 / 1.55 / 1.725.
- Actividad del día > actividad habitual > nada. Si se usa la habitual,
  el balance es `PARCIAL` y se nota.
- Sin búsqueda externa. Todo vive en la bóveda.
- El modelo nunca decide la fecha “porque sí”: si la incluye, es porque
  el usuario la mencionó; el bucle la valida con `parsear_fecha`.
- `.env` y `data/` excluidos de Git. Nunca commitear datos personales.
- Días sin datos no cuentan como 0 en promedios de reportes.
- Si falta un nutriente en algún día con datos, el promedio es `None`.
- Comparación con periodo anterior solo si hay datos del anterior.
- Peso histórico: no disponible. Los reportes lo indican.

## Git

- Ramas: `main`, `develop`, `feat/configuracion-ollama`,
  `feat/configuracion-contexto-md`, `feat/configuracion-inicial`,
  `feat/validar-logica`.
- Commits: Fases 1–9 cerradas, cada una con su commit.
- Remoto: `origin` (GitHub) con `main` y `develop`. Las ramas `feat/*`
  aún no se han subido.
- Pendiente: commit de Fase 10 cuando el instalador esté probado.

## Incidencias corregidas (histórico)

- **Perfil vacío rompía el arranque.** `Vault.read_perfil` construía
  `Perfil(**meta)` sin filtrar `tipo`/`version` y sin datos mínimos.
  Fix: filtra claves y devuelve `None` si faltan `edad`, `peso_kg`,
  `altura_cm`. Tests en `tests/test_vault_perfil_vacio.py`.
- **`main` usaba `root_for_backup` fijo.** Rompía bóvedas fuera del
  proyecto. Fix: `data_dir.parent`.
- **`interpretar` no enviaba el esquema al modelo.** El modelo reflejaba
  el contexto. Fix: anteponer `_SISTEMA_PROMPT` y envolver contexto.
- **Rama `RegistrarActividadOp` mal colocada** dentro de
  `_confirmar_registrar_actividad` (después del `return`). Movida a
  `_ejecutar_operacion`.
- **`write_registro` perdió el bloque `actividad`** al añadir
  `actividad_dia`. Restaurado. Ambos coexisten en el frontmatter.
- **`test_balance_calculado` y `test_flujo_completo`** esperaban
  `CALCULADO` con actividad habitual. Actualizados a `PARCIAL`.

## Próximos pasos tras Fase 10

- Firma de código (code signing) con certificado comercial.
- Auto-update.
- Distribución Linux/macOS.
- Integración opcional con Obsidian (no necesaria: los archivos ya son
  Markdown).

## Limpieza y datos de ejemplo

- Los datos de ejemplo de los scripts de humo se eliminaron tras Fase 5.
- `data/` real del proyecto contiene el perfil del usuario y los datos
  que haya generado. No se versiona.
- `%LOCALAPPDATA%\NutricionAgent\` contiene los datos del ejecutable.
  No se versiona.