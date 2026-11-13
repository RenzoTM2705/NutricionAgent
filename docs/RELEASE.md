
# NutricionAgent v0.1.0

Primera versión pública de **NutricionAgent**, un asistente nutricional local con inteligencia artificial, memoria basada en Markdown y cálculos deterministas.

## Cambios

- Asistente de configuración inicial guiado (perfil, objetivos y actividad).
- Agente conversacional local con Ollama (modelo intercambiable).
- Registro diario de comidas con cálculo de kcal y macronutrientes.
- Alta de alimentos y edición de ítems mediante conversación.
- Registro de actividad diaria y balance energético utilizando actividad real.
- Generación de reportes diarios, semanales y mensuales en Markdown.
- Bóveda Markdown compatible con Obsidian (opcional).
- Ejecutable para Windows mediante PyInstaller e instalador mediante Inno Setup.
- Datos del usuario almacenados en `%LOCALAPPDATA%\NutricionAgent\`, independientes del ejecutable.

## Instalación

1. Descarga `NutricionAgent-Setup-0.1.0.exe` desde los assets de esta release.
2. Ejecuta el instalador.
3. Por defecto, se instala en `%LOCALAPPDATA%\Programs\NutricionAgent\`, aunque puedes cambiar la carpeta.
4. Si no tienes Ollama, instálalo desde: https://ollama.com/download/windows
5. Descarga el modelo recomendado ejecutando el siguiente comando en PowerShell:

   ollama pull qwen3:4b-instruct-2507-q4_K_M

6. Abre NutricionAgent desde el Menú Inicio o el escritorio y completa el asistente de configuración inicial.

## Dónde están tus datos

- **Datos del usuario:** `%LOCALAPPDATA%\NutricionAgent\data\vault\` (bóveda Markdown).
- **Configuración:** `%LOCALAPPDATA%\NutricionAgent\.env`.
- **Backups:** `%LOCALAPPDATA%\NutricionAgent\data\backups\`.

Al desinstalar la aplicación, el instalador preguntará si deseas eliminar también tus datos. Por defecto, se conservan.

## Modo «Solo memoria»

Si Ollama no está instalado o no responde, la aplicación ofrece continuar sin IA.

En este modo puedes:

- Registrar comidas.
- Registrar actividad física.
- Consultar cálculos de calorías y macronutrientes.
- Mantener tus registros y datos locales.

Los cálculos nutricionales y energéticos funcionan independientemente de la IA. Cuando instales Ollama, podrás habilitar nuevamente el agente conversacional.

## Requisitos

- Windows 10/11 (x64).
- Ollama 0.40 o superior.
- Un modelo compatible con Ollama.
- Modelo recomendado: `qwen3:4b-instruct-2507-q4_K_M`.
- 4 GB de VRAM recomendados para el modelo predeterminado.

**Nota:** El modo «Solo memoria» está disponible si Ollama no está instalado o no se encuentra operativo.

## SHA256

Para verificar la integridad del instalador, utiliza el siguiente hash:

`7C0017885C746D2882D2570AC5139DFDA398C9358162748B15466FB42BCA99BC`

## Pendiente para futuras versiones

- Firma de código mediante certificado comercial.
- Sistema de actualización automática (Auto-update).
- Distribución para Linux y macOS.

---

# Flujo completo para publicar la versión 0.1.0

1. **Commit de Fase 10:** confirmar los cambios finales y realizar push de `feat/distribucion`.

2. **Merge a develop y main:** integrar los cambios en ambas ramas y realizar sus respectivos push.

3. **Crear el tag de versión:** crear el tag `v0.1.0` sobre `main` y subirlo al repositorio remoto.

   Comandos:
   
   - `git checkout main`
   - `git pull origin main`
   - `git tag v0.1.0`
   - `git push origin v0.1.0`

4. **Generar el instalador:** si todavía no existe, generar el ejecutable en `dist\NutricionAgent-Setup-0.1.0.exe`.

5. **Calcular el SHA256:** ejecutar en PowerShell:

   `(Get-FileHash "dist\NutricionAgent-Setup-0.1.0.exe" -Algorithm SHA256).Hash`

6. **Actualizar la release:** reemplazar `<hash>` por el SHA256 obtenido.

7. **Preparar la release en GitHub:**
   - Etiqueta: `v0.1.0`.
   - Título: `NutricionAgent v0.1.0`.
   - Descripción: utilizar el contenido de esta documentación.
   - Asset: adjuntar `NutricionAgent-Setup-0.1.0.exe`.

8. **Publicar la release:** verificar que el instalador esté adjunto, que el hash sea correcto y publicar la primera versión pública de NutricionAgent.
