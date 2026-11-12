# NutricionAgent

Asistente nutricional local impulsado por IA, con memoria en Markdown y cálculos deterministas en Python.

- **IA local** vía Ollama (modelo intercambiable).
- **Memoria** en Markdown (compatible con Obsidian como bóveda independiente).
- **Cálculos** en Python, no en el modelo.
- **Portable**: código y datos separados, sin rutas absolutas en el código.
- **Privado**: los datos del usuario se almacenan localmente y no se suben al repositorio.

## Estado

En desarrollo. Fase 1: entorno y arquitectura portable.

## Requisitos

- Python 3.10+ (probado con 3.12).
- Ollama instalado y con al menos un modelo descargado.
- Windows (inicial). Linux/macOS previstos.

## Estructura

app/ código
config/ configuración técnica
data/ datos del usuario (NO versionado)
docs/ documentación
tests/ pruebas


## Instalación (desarrollo)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env