"""Pruebas de utilidades de sistema de archivos."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage.fs import (
    PathOutsideRoot,
    atomic_write_text,
    backup_file,
    list_markdown,
    read_text,
    safe_relative_to,
)


def test_atomic_write_and_read(tmp_path: Path):
    p = tmp_path / "sub" / "file.md"
    atomic_write_text(p, "hola ñ 🥗\n")
    assert p.exists()
    assert read_text(p) == "hola ñ 🥗\n"


def test_atomic_write_leaves_no_tmp(tmp_path: Path):
    p = tmp_path / "file.md"
    atomic_write_text(p, "x")
    assert not (tmp_path / "file.md.tmp").exists()


def test_atomic_write_does_not_corrupt_on_failure(tmp_path: Path, monkeypatch):
    p = tmp_path / "file.md"
    atomic_write_text(p, "original")

    def boom(*a, **kw):
        raise OSError("disk full")

    monkeypatch.setattr("os.replace", boom)
    with pytest.raises(OSError):
        atomic_write_text(p, "nuevo")
    # El original sigue intacto
    assert p.read_text(encoding="utf-8") == "original"
    assert not (tmp_path / "file.md.tmp").exists()


def test_read_missing(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        read_text(tmp_path / "nope.md")


def test_safe_relative_to_ok(tmp_path: Path):
    child = tmp_path / "a" / "b.md"
    child.parent.mkdir()
    child.write_text("x", encoding="utf-8")
    assert safe_relative_to(child, tmp_path) == child.resolve()


def test_safe_relative_to_blocks_traversal(tmp_path: Path):
    outside = tmp_path.parent / "outside.md"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(PathOutsideRoot):
        safe_relative_to(outside, tmp_path / "root")


def test_backup_file_creates_copy(tmp_path: Path):
    root = tmp_path / "root"
    f = root / "a" / "b.md"
    f.parent.mkdir(parents=True)
    f.write_text("v1", encoding="utf-8")

    backups = tmp_path / "backups"
    dest = backup_file(f, backups, root)
    assert dest is not None
    assert dest.read_text(encoding="utf-8") == "v1"
    assert dest.parent.parent.name  # tiene fecha


def test_backup_file_missing_returns_none(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    backups = tmp_path / "backups"
    assert backup_file(root / "nope.md", backups, root) is None


def test_backup_cleanup_removes_old(tmp_path: Path):
    root = tmp_path / "root"
    root.mkdir()
    f = root / "a.md"
    f.write_text("x", encoding="utf-8")

    backups = tmp_path / "backups"
    old = backups / "2000-01-01" / "a.md"
    old.parent.mkdir(parents=True)
    old.write_text("viejo", encoding="utf-8")

    backup_file(f, backups, root, max_days=7)
    assert not old.exists()


def test_list_markdown_sorted(tmp_path: Path):
    (tmp_path / "b.md").write_text("b", encoding="utf-8")
    (tmp_path / "a.md").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.md").write_text("c", encoding="utf-8")
    (tmp_path / "no.txt").write_text("x", encoding="utf-8")
    names = [p.name for p in list_markdown(tmp_path)]
    assert names == ["a.md", "b.md", "c.md"]