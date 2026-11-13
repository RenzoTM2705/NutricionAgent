## NutricionAgent v0.1.0

Primera versión pública de NutricionAgent: asistente nutricional local con IA, memoria Markdown y cálculos deterministas.

### Cambios

- Asistente de configuración inicial guiado (perfil, objetivos, actividad).
- Agente conversacional local con Ollama (modelo intercambiable).
- Registro diario de comidas con cálculo de kcal y macros.
- Alta de alimentos y edición de items conversacional.
- Actividad del día y balance energético usando actividad real.
- Reportes diarios, semanales y mensuales en Markdown.
- Bóveda Markdown compatible con Obsidian (opcional).
- Ejecutable Windows (PyInstaller) e instalador (Inno Setup).
- Datos del usuario en `%LOCALAPPDATA%\NutricionAgent\`, independientes del ejecutable.

### Instalación

1. Descarga `NutricionAgent-Setup-0.1.0.exe` desde los assets de esta release.
2. Ejecuta el instalador. Por defecto se instala en `%LOCALAPPDATA%\Programs\NutricionAgent\`, pero puedes cambiar la carpeta.
3. Si no tienes Ollama, instálalo: https://ollama.com/download/windows
4. Descarga el modelo recomendado:
5. Abre NutricionAgent desde el Menú Inicio o el escritorio y completa el asistente.

### Dónde están tus datos

- Datos del usuario: `%LOCALAPPDATA%\NutricionAgent\data\vault\` (bóveda Markdown).
- Configuración: `%LOCALAPPDATA%\NutricionAgent\.env`.
- Backups: `%LOCALAPPDATA%\NutricionAgent\data\backups\`.

Al desinstalar, el instalador pregunta si quieres borrar tus datos. Por defecto, no.

### Modo "solo memoria"

Si Ollama no está instalado o no responde, la app ofrece continuar sin IA. Puedes registrar comidas y actividad; los cálculos funcionan igual. Cuando instales Ollama, la IA se habilita.

### SHA256
