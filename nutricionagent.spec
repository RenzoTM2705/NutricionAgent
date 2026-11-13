# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para NutricionAgent.

Genera una carpeta dist/NutricionAgent/ con NutricionAgent.exe y sus
dependencias. Los datos del usuario NO se incluyen: van a
%LOCALAPPDATA%\\NutricionAgent en runtime (ver app/config.py).

Build:
    pyinstaller nutricionagent.spec --noconfirm
"""

from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Incluye el paquete app completo, para no depender de imports dinámicos.
hiddenimports = collect_submodules("app")

datas = [
    ("app", "app"),  # copia app/ como recurso (por si se lee algún .md)
    (".env.example", "."),  # plantilla para crear .env en %LOCALAPPDATA%
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tkinter",
        "pytest",
        "_pytest",
        "matplotlib",
        "numpy",
        "pandas",
        "IPython",
        "notebook",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="NutricionAgent",
    icon="assets/nutricionagent.ico",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # app de terminal; sin consola no veríamos nada
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="NutricionAgent",
)