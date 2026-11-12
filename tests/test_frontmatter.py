"""Pruebas del parser/escritor de frontmatter."""

from __future__ import annotations

import pytest

from app.storage.frontmatter import (
    FrontmatterError,
    dump,
    parse,
)


def test_parse_no_frontmatter():
    meta, body = parse("solo texto\n")
    assert meta == {}
    assert body == "solo texto\n"


def test_parse_basic():
    text = "---\ntipo: perfil\nversion: 1\nactivo: true\npeso: 72.5\nnota: null\n---\nCuerpo\n"
    meta, body = parse(text)
    assert meta == {
        "tipo": "perfil",
        "version": 1,
        "activo": True,
        "peso": 72.5,
        "nota": None,
    }
    assert body == "Cuerpo\n"


def test_parse_quoted_strings():
    text = '---\nnombre: "Juan: Pérez"\notro: \'dicho con "comillas"\'\n---\n'
    meta, _ = parse(text)
    assert meta["nombre"] == "Juan: Pérez"
    assert meta["otro"] == 'dicho con "comillas"'


def test_parse_empty_body():
    meta, body = parse("---\na: 1\n---\n")
    assert meta == {"a": 1}
    assert body == ""


def test_parse_unclosed_raises():
    with pytest.raises(FrontmatterError):
        parse("---\na: 1\n")


def test_parse_line_without_colon_raises():
    with pytest.raises(FrontmatterError):
        parse("---\na 1\n---\n")


def test_parse_duplicate_key_raises():
    with pytest.raises(FrontmatterError):
        parse("---\na: 1\na: 2\n---\n")


def test_parse_ignores_comments_and_blank_lines():
    meta, _ = parse("---\n# comentario\na: 1\n\n---\n")
    assert meta == {"a": 1}


def test_dump_roundtrip():
    meta = {"tipo": "perfil", "version": 1, "peso": 72.5, "activo": True, "nota": None}
    body = "Cuerpo\n"
    text = dump(meta, body)
    meta2, body2 = parse(text)
    assert meta2 == meta
    assert body2 == body


def test_dump_quotes_tricky_strings():
    meta = {"a": "con: dos puntos", "b": "true", "c": "  espacios  "}
    text = dump(meta, "")
    meta2, _ = parse(text)
    assert meta2 == meta


def test_dump_rejects_unsupported_type():
    with pytest.raises(FrontmatterError):
        dump({"a": [1, 2]}, "")


def test_dump_empty_meta_returns_body():
    assert dump({}, "hola\n") == "hola\n"