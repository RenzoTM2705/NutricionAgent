# Cómo publicar una release

Pasos manuales para publicar una nueva versión de NutricionAgent en GitHub Releases.

## Requisitos

- PyInstaller instalado (`pip install -r requirements-dev.txt`).
- Inno Setup 7 instalado (ruta: `E:\InnoSetup\Inno Setup 7\ISCC.exe` en esta máquina).
- Acceso al repositorio en GitHub.

## Pasos

### 1. Actualizar versión

- Edita `app/__init__.py`: `__version__ = "X.Y.Z"`.
- Edita `installer.iss`: `#define MyAppVersion "X.Y.Z"`.
- Añade entrada en `CHANGELOG.md`.

### 2. Generar el ejecutable

```powershell
Set-Location "E:\Proyectos\NutricionAgent"
.\.venv\Scripts\Activate.ps1
pyinstaller nutricionagent.spec --noconfirm