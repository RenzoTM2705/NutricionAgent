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

### Completado

- **5.1** — `app/setup/wizard.py`: lógica pura del asistente (`SetupInput`, `SetupResult`, `SetupError`, `aplicar_setup`, `perfil_existente`). 13 tests.
- `docs/ESTADO.md` actualizado tras cada subtarea.

## Fase 5 — Completada

### Completado

- **5.1** — `app/setup/wizard.py`: lógica pura del asistente (`SetupInput`, `SetupResult`, `SetupError`, `aplicar_setup`, `perfil_existente`). 13 tests.
- **5.2** — `app/setup/console.py`: capa Rich, sin tests automáticos; verificada vía 5.4 y 5.6.
- **5.3** — `app/setup/checks.py`: estado de Ollama, prueba de modelo, mensajes al usuario. 10 tests.
- **5.4** — `app/main.py`: detecta perfil, lanza asistente si no hay, mensaje breve si hay. Probado con bóveda temporal.
- **5.5** — Omitida (tests de consola con mocks considerados frágiles; cobertura vía 5.6).
- **5.6** — `app/_smoke_setup.py`: flujo completo con Ollama real y bóveda temporal. Exit 0.

### Pendiente de Fase 5

Nada. Fase cerrada.

## Fase 6 — Pendiente

- Registro diario vía agente.

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

## Pendiente

- Fase 6: registro diario vía agente.
- Fase 7: agente conversacional.
- Fase 8: actividad y gasto.
- Fase 9: reportes.
- Fase 10: distribución.