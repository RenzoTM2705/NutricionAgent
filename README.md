# NutricionAgent

Asistente nutricional local impulsado por IA, con memoria en Markdown y cálculos deterministas en Python.

- **IA local** vía Ollama (modelo intercambiable).
- **Memoria** en Markdown (compatible con Obsidian como bóveda independiente).
- **Cálculos** en Python, no en el modelo.
- **Portable**: código y datos separados, sin rutas absolutas en el código.
- **Privado**: los datos del usuario se almacenan localmente y no se suben al repositorio.

## Estado

En desarrollo. Fases completadas:

- **Fase 1** — Entorno portable, venv, bóveda inicial, Git.
- **Fase 2** — Cliente Ollama, configuración tipada, errores, pruebas.
- **Fase 3** — Sistema de memoria Markdown: modelos de dominio, almacenamiento atómico, backups, frontmatter, Vault para perfil, objetivos, actividad, alimentos, recetas y registro diario.
- **Fase 4** — Motor nutricional: conversión de unidades, cálculo por item, totales diarios, recetas con ingredientes anidados, BMR (Mifflin-St Jeor), factor de actividad, TDEE y balance energético. Regla estricta: nutrientes desconocidos = `None`, nunca `0`; resultados parciales explícitos.

Próximas fases:

- **Fase 5** — Configuración inicial del usuario.
- **Fase 6** — Registro diario vía agente.
- **Fase 7** — Agente conversacional.
- **Fase 8** — Actividad y gasto energético.
- **Fase 9** — Reportes.
- **Fase 10** — Distribución (PyInstaller, Inno Setup, GitHub Releases).

Próximas fases:

- **Fase 4** — Motor nutricional (cálculos, conversión, recetas, macros).
- **Fase 5** — Configuración inicial del usuario.
- **Fase 6** — Registro diario vía agente.
- **Fase 7** — Agente conversacional.
- **Fase 8** — Actividad y gasto energético.
- **Fase 9** — Reportes.
- **Fase 10** — Distribución (PyInstaller, Inno Setup, GitHub Releases).

## Requisitos

- Python 3.10+ (probado con 3.12).
- Ollama instalado y con al menos un modelo descargado (probado con `qwen3:4b-instruct-2507-q4_K_M`).
- Windows (inicial). Linux/macOS previstos.

## Estructura

app/        código
config/     configuración técnica
data/       datos del usuario (NO versionado)
docs/       documentación
tests/      pruebas

## Instalación (desarrollo)

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env

## Ollama

Se usa la API HTTP de Ollama, no ollama run. El modelo activo y los parámetros (temperature, num_ctx, keep_alive) se configuran en .env.

Si Ollama no está corriendo, la app lo detecta y avisa. No descarga modelos automáticamente.

## Bóveda Markdown

La bóveda por defecto está en data/vault/. Puede abrirse en Obsidian como bóveda independiente. Si el usuario prefiere otra ubicación, se configura con NUTRICIONAGENT_DATA_DIR en .env. La bóveda personal del usuario nunca se toca.

Formatos internos (no requieren edición manual):

Perfil, objetivos y actividad: frontmatter YAML simple.

Alimentos y recetas: secciones Markdown con bloques YAML.

Registro diario: frontmatter + lista plana de items en secciones Markdown.

Todas las escrituras son atómicas. Antes de sobrescribir se guarda un backup en data/backups/<fecha>/....

## Pruebas

python -m pytest tests -v
Actualmente: 92 pruebas en verde, sin red, con tmp_path.

Scripts de humo contra servicios reales:

python -m app._smoke_ollama   # contra Ollama
python -m app._smoke_vault    # contra data/vault


## Privacidad

data/ (bóveda y backups) está excluido de Git.

.env está excluido de Git.

No se envían datos a servicios externos.

## Licencia

Por definir.
