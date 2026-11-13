# Changelog

Todas las versiones notables de NutricionAgent.

## [0.1.0] - 2026-11-13

### Añadido

- Asistente de configuración inicial guiado (perfil, objetivos, actividad).
- Agente conversacional local con Ollama (modelo intercambiable).
- Registro diario de comidas con cálculo de kcal y macros.
- Alta de alimentos y edición de items conversacional.
- Actividad del día y balance energético usando actividad real.
- Reportes diarios, semanales y mensuales en Markdown.
- Bóveda Markdown compatible con Obsidian (opcional).
- Ejecutable Windows (PyInstaller) e instalador (Inno Setup).
- Datos del usuario en `%LOCALAPPDATA%\NutricionAgent\`, independientes del ejecutable.

### Notas

- Ollama es una dependencia externa. Instalación: https://ollama.com/download/windows
- Modelo recomendado: `qwen3:4b-instruct-2507-q4_K_M`.
- Sin firma de código en esta versión.