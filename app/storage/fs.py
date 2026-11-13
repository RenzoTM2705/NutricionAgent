"""Utilidades de sistema de archivos con escritura atómica y backups.

Reglas:
- Todas las escrituras son atómicas (tmp + os.replace).
- Los backups se guardan por fecha antes de sobrescribir.
- Todas las rutas se validan contra una raíz para evitar traversal.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable


class StorageError(Exception):
    """Error de almacenamiento."""


class PathOutsideRoot(StorageError):
    """La ruta intenta salir de la raíz permitida."""


def ensure_dir(path: Path) -> Path:
    """Crea el directorio (y padres) si no existe."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_relative_to(path: Path, root: Path) -> Path:
    """Devuelve `path` resuelto si está dentro de `root`; si no, lanza.

    Ambos se resuelven antes de comparar.
    """
    root_r = root.resolve()
    p_r = path.resolve()
    try:
        p_r.relative_to(root_r)
    except ValueError as exc:
        raise PathOutsideRoot(f"{p_r} no está dentro de {root_r}") from exc
    return p_r


def atomic_write_text(path: Path, text: str, encoding: str = "utf-8") -> None:
    """Escribe texto de forma atómica.

    Escribe a un `.tmp` en el mismo directorio y hace `os.replace`.
    Si algo falla a mitad, el archivo original no se toca.
    """
    ensure_dir(path.parent)
    tmp = path.with_name(path.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        raise


def read_text(path: Path, encoding: str = "utf-8") -> str:
    """Lee texto; lanza FileNotFoundError si no existe."""
    if not path.exists():
        raise FileNotFoundError(f"No existe el archivo: {path}")
    return path.read_text(encoding=encoding)


def backup_file(
    path: Path,
    backup_root: Path,
    root: Path,
    *,
    max_days: int = 7,
) -> Path | None:
    """Copia `path` a `backup_root/YYYY-MM-DD/<ruta_relativa_a_root>`.

    - Si `path` no existe, no hace nada y devuelve None.
    - Limpia carpetas de backup con fecha anterior a hoy - max_days.
    - Devuelve la ruta del backup creado o None.
    """
    if not path.exists():
        return None
    rel = safe_relative_to(path, root)
    rel_to_root = rel.relative_to(root.resolve())
    today = datetime.now().strftime("%Y-%m-%d")
    dest = backup_root / today / rel_to_root
    ensure_dir(dest.parent)
    shutil.copy2(path, dest)
    _cleanup_old_backups(backup_root, max_days=max_days)
    return dest


def _cleanup_old_backups(backup_root: Path, *, max_days: int) -> None:
    """Borra carpetas de backup con fecha anterior a hoy - max_days."""
    if not backup_root.exists():
        return
    cutoff = datetime.now().date() - timedelta(days=max_days)
    for child in backup_root.iterdir():
        if not child.is_dir():
            continue
        try:
            d = datetime.strptime(child.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            shutil.rmtree(child, ignore_errors=True)


def list_markdown(root: Path) -> Iterable[Path]:
    """Lista archivos .md recursivos bajo root, ordenados."""
    if not root.exists():
        return []
    return sorted(p for p in root.rglob("*.md") if p.is_file())