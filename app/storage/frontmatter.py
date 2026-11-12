"""Parser y escritor mínimo de frontmatter YAML.

Soporta solo escalares: str, int, float, bool, None.
No soporta listas ni objetos anidados (por diseño, en esta fase).

Formato reconocido:
    ---
    clave: valor
    otra: 123
    ---
    cuerpo...

Si el archivo no empieza por `---`, todo el texto es cuerpo.
"""

from __future__ import annotations

import re
from typing import Any

_FENCE = "---"
_INT_RE = re.compile(r"^-?[0-9]+$")
_FLOAT_RE = re.compile(r"^-?(?:[0-9]+\.[0-9]*|[0-9]*\.[0-9]+)(?:[eE][-+]?[0-9]+)?$")


class FrontmatterError(ValueError):
    """Error de parseo o serialización de frontmatter."""


def _parse_value(raw: str) -> Any:
    s = raw.strip()
    if s == "":
        return ""
    low = s.lower()
    if low in ("null", "~"):
        return None
    if low == "true":
        return True
    if low == "false":
        return False
    if (s.startswith('"') and s.endswith('"') and len(s) >= 2) or (
        s.startswith("'") and s.endswith("'") and len(s) >= 2
    ):
        quote = s[0]
        inner = s[1:-1]
        if quote == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        else:
            inner = inner.replace("''", "'")
        return inner
    if _INT_RE.match(s):
        return int(s)
    if _FLOAT_RE.match(s):
        return float(s)
    return s


def _format_value(v: Any) -> str:
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int) and not isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str):
        needs_quotes = (
            v == ""
            or v.lower() in ("true", "false", "null", "~")
            or _INT_RE.match(v)
            or _FLOAT_RE.match(v)
            or ":" in v
            or v.startswith("#")
            or v != v.strip()
        )
        if needs_quotes:
            escaped = v.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
        return v
    raise FrontmatterError(f"Tipo no soportado en frontmatter: {type(v).__name__}")


def parse(text: str) -> tuple[dict[str, Any], str]:
    """Devuelve (meta, body). Si no hay frontmatter, meta={} y body=text."""
    # Normalizar finales de línea para el parseo, sin alterar el body devuelto.
    if not text.startswith(_FENCE):
        return {}, text

    # Buscar el cierre
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != _FENCE:
        return {}, text

    close_idx: int | None = None
    for i in range(1, len(lines)):
        if lines[i].strip() == _FENCE:
            close_idx = i
            break
    if close_idx is None:
        raise FrontmatterError("Frontmatter sin cierre '---'.")

    meta: dict[str, Any] = {}
    for raw_line in lines[1:close_idx]:
        line = raw_line.rstrip("\r\n")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise FrontmatterError(f"Línea de frontmatter sin ':' -> {line!r}")
        key, _, value = line.partition(":")
        key = key.strip()
        if not key:
            raise FrontmatterError(f"Clave vacía en frontmatter: {line!r}")
        if key in meta:
            raise FrontmatterError(f"Clave duplicada en frontmatter: {key!r}")
        meta[key] = _parse_value(value)

    body = "".join(lines[close_idx + 1 :])
    return meta, body


def dump(meta: dict[str, Any], body: str, *, sort_keys: bool = True) -> str:
    """Serializa meta + body a texto con frontmatter."""
    if not meta:
        return body if body.endswith("\n") else (body + "\n" if body else "")

    keys = sorted(meta.keys()) if sort_keys else list(meta.keys())
    lines: list[str] = [_FENCE]
    for k in keys:
        if not isinstance(k, str) or not k or ":" in k:
            raise FrontmatterError(f"Clave inválida en frontmatter: {k!r}")
        lines.append(f"{k}: {_format_value(meta[k])}")
    lines.append(_FENCE)

    text = "\n".join(lines) + "\n"
    if body:
        text += body
        if not text.endswith("\n"):
            text += "\n"
    return text