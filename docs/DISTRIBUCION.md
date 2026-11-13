# Distribución de NutricionAgent

Documento de decisiones para el empaquetado y la distribución en Windows.

## Resumen

- Ejecutable único con PyInstaller.
- Instalador con Inno Setup.
- Publicación en GitHub Releases.
- Ollama es dependencia externa; el instalador solo avisa.
- Los datos del usuario viven fuera del ejecutable, en `%LOCALAPPDATA%\NutricionAgent\`.
- Sin firma de código en esta fase.

## Dentro del ejecutable

- Código Python (`app/`).
- `.env.example` (plantilla, para crear `.env` la primera vez).
- Icono (opcional).
- Metadatos de versión.

## Fuera del ejecutable

- `data/vault/` del usuario: `%LOCALAPPDATA%\NutricionAgent\data\vault\`.
- `data/backups/`: `%LOCALAPPDATA%\NutricionAgent\data\backups\`.
- `.env`: `%LOCALAPPDATA%\NutricionAgent\.env`.
- Ollama: instalación aparte, `https://ollama.com/download/windows`.
- Modelos de IA: gestionados por Ollama (`OLLAMA_MODELS`).

## Rutas en runtime congelado

En `app/config.py`:

- `PROJECT_ROOT` = `sys._MEIPASS` si `getattr(sys, "frozen", False)`, si no, `Path(__file__).resolve().parents[1]`.
- `data_dir`:
  - Si `NUTRICIONAGENT_DATA_DIR` está definida, se usa esa.
  - Si no, `%LOCALAPPDATA%\NutricionAgent\data\vault`.
  - En desarrollo (no congelado, sin variable), `PROJECT_ROOT/data/vault` como hasta ahora.
- `backup_root` = `data_dir.parent / "backups"`.
- `.env`:
  - Si existe `%LOCALAPPDATA%\NutricionAgent\.env`, se carga.
  - Si no, se carga `.env` en `PROJECT_ROOT` (modo desarrollo).
  - Si no existe ninguno, se usan valores por defecto.
  - El instalador crea `%LOCALAPPDATA%\NutricionAgent\.env` a partir de `.env.example`.

## Detección de Ollama

- `OllamaClient` y `app/setup/checks.py` no cambian.
- Si Ollama no responde, el asistente ofrece modo “solo memoria”.
- El instalador incluye un aviso con enlace a la descarga de Ollama y una nota en el README.

## Preservación de datos

- El instalador nunca borra `%LOCALAPPDATA%\NutricionAgent\`.
- Al desinstalar, pregunta si borrar datos. Por defecto, no.
- Las actualizaciones sobrescriben el ejecutable y los recursos, no los datos.

## Herramientas de build

- **PyInstaller** para generar el ejecutable.
- **Inno Setup** para el instalador.
- **GitHub Releases** para publicar.

No entran en `requirements.txt` de runtime. Se documentan en `requirements-dev.txt` (opcional).

## Estructura del instalador

- Nombre: `NutricionAgent-Setup-<version>.exe`.
- Instala en `%LOCALAPPDATA%\Programs\NutricionAgent\` (por usuario, sin admin).
- Crea accesos directos en Menú Inicio y Escritorio (opcional).
- Crea `%LOCALAPPDATA%\NutricionAgent\.env` a partir de `.env.example`.
- Crea `%LOCALAPPDATA%\NutricionAgent\data\vault\` con la estructura mínima.
- Al desinstalar, ofrece borrar datos.

## Versionado

- `0.1.0` en `app/__init__.py`.
- El instalador usa esa versión.
- Cada release actualiza `CHANGELOG.md` y el tag de Git.

## Prueba en máquina limpia

VM o usuario de Windows sin Python ni VS Code:

1. Instalar el Setup.
2. Abrir NutricionAgent desde el Menú Inicio.
3. Completar el asistente (con Ollama activo o en modo solo memoria).
4. Registrar un item.
5. Salir.
6. Reabrir y verificar que los datos persisten.
7. Desinstalar y verificar que los datos no se borran por defecto.

## Pendiente (futuras fases)

- Firma de código con certificado.
- Auto-update.
- Distribución para Linux/macOS.
- Integración adicional con Obsidian (no necesaria: los archivos ya son Markdown).