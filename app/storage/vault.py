"""Capa de almacenamiento sobre la bóveda Markdown.

Alcance actual: perfil, objetivos, actividad habitual, alimentos,
recetas y registro diario.

Reglas:
- Vault es la única puerta de entrada/salida a la bóveda.
- Cada write_* hace backup del archivo existente antes de sobrescribir.
- Los errores de parseo se propagan como VaultError con contexto.
- Los formatos con listas anidadas usan secciones Markdown con
  bloques ```yaml``` internos, parseados con el parser de frontmatter
  reutilizado sobre el contenido de cada bloque.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterable

from app.models.domain import (
    ActividadDia,
    ActividadHabitual,
    Alimento,
    IngredienteReceta,
    ItemComida,
    Objetivos,
    Perfil,
    Receta,
    RegistroDiario,
    Unidad,
)
from app.storage import frontmatter
from app.storage.fs import (
    atomic_write_text,
    backup_file,
    read_text,
)


# ---------------------------------------------------------------------------
# Meses sin acentos, para rutas portables
# ---------------------------------------------------------------------------
_MESES = [
    "01-Enero", "02-Febrero", "03-Marzo", "04-Abril",
    "05-Mayo", "06-Junio", "07-Julio", "08-Agosto",
    "09-Septiembre", "10-Octubre", "11-Noviembre", "12-Diciembre",
]


def _month_dir(d: date) -> str:
    return _MESES[d.month - 1]


# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------
class VaultError(Exception):
    """Error de la capa Vault."""


class DuplicateIdError(VaultError):
    """El id ya existe."""


# ---------------------------------------------------------------------------
# Utilidades para listas planas: '## <id>' + bloque ```yaml```
# ---------------------------------------------------------------------------
def _dump_items(items: Iterable[dict[str, Any]]) -> str:
    """Serializa una lista de dicts como secciones '## id' + bloque ```yaml."""
    out: list[str] = []
    for item in items:
        item_id = item["id"]
        meta = {k: v for k, v in item.items() if k != "id"}
        block = frontmatter.dump(meta, "")
        lines = block.splitlines()
        inner = lines[1:-1] if lines and lines[0] == "---" else lines
        out.append(f"## {item_id}")
        out.append("")
        out.append("```yaml")
        out.extend(inner)
        out.append("```")
        out.append("")
    return "\n".join(out)


def _parse_items(body: str, *, id_key: str = "id") -> list[dict[str, Any]]:
    """Parsea secciones '## id' + ```yaml ... ``` y devuelve dicts con id."""
    items: list[dict[str, Any]] = []
    lines = body.splitlines()
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.startswith("## "):
            item_id = line[3:].strip()
            if not item_id:
                raise VaultError("Sección '## ' sin id.")
            i += 1
            while i < n and lines[i].strip() == "":
                i += 1
            if i >= n or lines[i].strip() != "```yaml":
                raise VaultError(f"Sección '## {item_id}' sin bloque ```yaml.")
            i += 1
            block_lines: list[str] = []
            while i < n and lines[i].strip() != "```":
                block_lines.append(lines[i])
                i += 1
            if i >= n:
                raise VaultError(f"Bloque ```yaml sin cierre en '## {item_id}'.")
            i += 1
            block_text = "---\n" + "\n".join(block_lines) + "\n---\n"
            meta, _ = frontmatter.parse(block_text)
            meta[id_key] = item_id
            items.append(meta)
        else:
            i += 1
    return items


# ---------------------------------------------------------------------------
# Vault
# ---------------------------------------------------------------------------
class Vault:
    def __init__(
        self,
        data_dir: Path,
        backup_root: Path,
        *,
        root_for_backup: Path | None = None,
    ) -> None:
        self.data_dir = Path(data_dir)
        self.backup_root = Path(backup_root)
        self._root_for_backup = Path(root_for_backup) if root_for_backup else self.data_dir

    # --- rutas base ---
    @property
    def perfil_path(self) -> Path:
        return self.data_dir / "01-Perfil" / "perfil.md"

    @property
    def objetivos_path(self) -> Path:
        return self.data_dir / "01-Perfil" / "objetivos.md"

    @property
    def actividad_path(self) -> Path:
        return self.data_dir / "01-Perfil" / "actividad.md"

    @property
    def alimentos_path(self) -> Path:
        return self.data_dir / "02-Alimentos" / "alimentos-habituales.md"

    @property
    def recetas_path(self) -> Path:
        return self.data_dir / "02-Alimentos" / "recetas.md"

        # Claves de frontmatter que no forman parte del modelo y se ignoran al leer.
    _META_IGNORADAS = {"tipo", "version"}

    def _read_typed(self, path: Path, model: type, default: Any = None) -> Any:
        if not path.exists():
            return default
        try:
            text = read_text(path)
            meta, _ = frontmatter.parse(text)
            meta_limpio = {k: v for k, v in meta.items() if k not in self._META_IGNORADAS}
            return model(**meta_limpio)
        except Exception as exc:
            raise VaultError(f"No se pudo leer {path}: {exc}") from exc

    def _write_typed(self, path: Path, model: Any) -> Path:
        try:
            if path.exists():
                backup_file(path, self.backup_root, self._root_for_backup)
            meta = model.model_dump(mode="json")
            text = frontmatter.dump(meta, "")
            atomic_write_text(path, text)
        except Exception as exc:
            raise VaultError(f"No se pudo escribir {path}: {exc}") from exc
        return path

    # --- perfil ---
    def read_perfil(self) -> Perfil | None:
        path = self.perfil_path
        if not path.exists():
            return None
        try:
            text = read_text(path)
            meta, _ = frontmatter.parse(text)
            # Si faltan los campos mínimos, el perfil no está configurado.
            if not all(k in meta for k in ("edad", "peso_kg", "altura_cm")):
                return None
            meta_limpio = {k: v for k, v in meta.items() if k not in self._META_IGNORADAS}
            return Perfil(**meta_limpio)
        except VaultError:
            raise
        except Exception as exc:
            raise VaultError(f"No se pudo leer {path}: {exc}") from exc

    def write_perfil(self, perfil: Perfil) -> Path:
        return self._write_typed(self.perfil_path, perfil)

    # --- objetivos ---
    def read_objetivos(self) -> Objetivos | None:
        return self._read_typed(self.objetivos_path, Objetivos)

    def write_objetivos(self, obj: Objetivos) -> Path:
        return self._write_typed(self.objetivos_path, obj)

    # --- actividad ---
    def read_actividad(self) -> ActividadHabitual | None:
        return self._read_typed(self.actividad_path, ActividadHabitual)

    def write_actividad(self, act: ActividadHabitual) -> Path:
        return self._write_typed(self.actividad_path, act)

    # --- alimentos ---
    def read_alimentos(self) -> list[Alimento]:
        if not self.alimentos_path.exists():
            return []
        try:
            text = read_text(self.alimentos_path)
            _, body = frontmatter.parse(text)
            raw = _parse_items(body)
            return [Alimento(**r) for r in raw]
        except VaultError:
            raise
        except Exception as exc:
            raise VaultError(f"No se pudieron leer alimentos: {exc}") from exc

    def write_alimentos(self, lista: list[Alimento]) -> Path:
        try:
            if self.alimentos_path.exists():
                backup_file(
                    self.alimentos_path, self.backup_root, self._root_for_backup
                )
            body = "# Alimentos habituales\n\n" + _dump_items(
                [a.model_dump(mode="json") for a in lista]
            )
            atomic_write_text(self.alimentos_path, body)
        except Exception as exc:
            raise VaultError(f"No se pudieron escribir alimentos: {exc}") from exc
        return self.alimentos_path

    def add_alimento(self, a: Alimento) -> Path:
        actuales = self.read_alimentos()
        if any(x.id == a.id for x in actuales):
            raise DuplicateIdError(f"Ya existe un alimento con id {a.id!r}")
        actuales.append(a)
        return self.write_alimentos(actuales)

    def get_alimento(self, id_: str) -> Alimento | None:
        for a in self.read_alimentos():
            if a.id == id_:
                return a
        return None

    def remove_alimento(self, id_: str) -> bool:
        actuales = self.read_alimentos()
        nuevas = [a for a in actuales if a.id != id_]
        if len(nuevas) == len(actuales):
            return False
        self.write_alimentos(nuevas)
        return True

    # --- recetas ---
    def _parse_recetas_body(self, body: str) -> list[dict[str, Any]]:
        """Parsea recetas.md con '## <id>', '### Ingredientes' y '#### ing-N'."""
        recetas: list[dict[str, Any]] = []
        lines = body.splitlines()
        i = 0
        n = len(lines)
        current: dict[str, Any] | None = None
        current_ing: dict[str, Any] | None = None
        mode: str = "none"

        def _flush_ing() -> None:
            nonlocal current_ing
            if current is not None and current_ing is not None:
                current["ingredientes"].append(current_ing)
                current_ing = None

        def _flush_receta() -> None:
            nonlocal current
            _flush_ing()
            if current is not None:
                recetas.append(current)
                current = None

        while i < n:
            line = lines[i]

            if line.startswith("## "):
                _flush_receta()
                rec_id = line[3:].strip()
                if not rec_id:
                    raise VaultError("Receta con '## ' sin id.")
                current = {"id": rec_id, "ingredientes": []}
                mode = "receta_meta"
                i += 1
                continue

            if line.strip() == "### Ingredientes":
                if current is None:
                    raise VaultError("'### Ingredientes' sin receta previa.")
                _flush_ing()
                mode = "ingredientes"
                i += 1
                continue

            if line.startswith("#### "):
                if current is None:
                    raise VaultError("'#### ' sin receta previa.")
                if mode not in ("ingredientes", "ing_item"):
                    raise VaultError("'#### ' fuera de sección de ingredientes.")
                _flush_ing()
                current_ing = {"_order": line[5:].strip()}
                mode = "ing_item"
                i += 1
                continue

            if line.strip() == "```yaml":
                i += 1
                block_lines: list[str] = []
                while i < n and lines[i].strip() != "```":
                    block_lines.append(lines[i])
                    i += 1
                if i >= n:
                    raise VaultError("Bloque ```yaml sin cierre.")
                i += 1
                block_text = "---\n" + "\n".join(block_lines) + "\n---\n"
                meta, _ = frontmatter.parse(block_text)

                if mode == "receta_meta" and current is not None:
                    current.update(meta)
                    mode = "ingredientes"
                elif mode == "ing_item" and current_ing is not None:
                    current_ing.update(meta)
                else:
                    raise VaultError(
                        f"Bloque ```yaml inesperado en modo {mode!r}."
                    )
                continue

            i += 1

        _flush_receta()
        return recetas

    def _dump_recetas_body(self, recetas: list[Receta]) -> str:
        """Serializa recetas con ingredientes en sub-secciones."""
        out: list[str] = ["# Recetas", ""]
        for r in recetas:
            out.append(f"## {r.id}")
            out.append("")
            out.append("```yaml")
            meta = {
                "nombre": r.nombre,
                "rendimiento_porciones": r.rendimiento_porciones,
                "notas": r.notas,
            }
            block = frontmatter.dump(meta, "")
            inner = block.splitlines()
            inner = inner[1:-1] if inner and inner[0] == "---" else inner
            out.extend(inner)
            out.append("```")
            out.append("")
            out.append("### Ingredientes")
            out.append("")
            for idx, ing in enumerate(r.ingredientes, start=1):
                out.append(f"#### ing-{idx}")
                out.append("")
                out.append("```yaml")
                ing_meta = {
                    "alimento_id": ing.alimento_id,
                    "cantidad": ing.cantidad,
                    "unidad": ing.unidad.value,
                }
                block = frontmatter.dump(ing_meta, "")
                inner = block.splitlines()
                inner = inner[1:-1] if inner and inner[0] == "---" else inner
                out.extend(inner)
                out.append("```")
                out.append("")
        return "\n".join(out)

    def read_recetas(self) -> list[Receta]:
        if not self.recetas_path.exists():
            return []
        try:
            text = read_text(self.recetas_path)
            _, body = frontmatter.parse(text)
            raw = self._parse_recetas_body(body)
            result: list[Receta] = []
            for r in raw:
                ingredients_raw = r.pop("ingredientes", [])
                ingredients: list[IngredienteReceta] = []
                for ing in ingredients_raw:
                    ing.pop("_order", None)
                    ingredients.append(IngredienteReceta(**ing))
                result.append(Receta(ingredientes=ingredients, **r))
            return result
        except VaultError:
            raise
        except Exception as exc:
            raise VaultError(f"No se pudieron leer recetas: {exc}") from exc

    def write_recetas(self, lista: list[Receta]) -> Path:
        try:
            if self.recetas_path.exists():
                backup_file(
                    self.recetas_path, self.backup_root, self._root_for_backup
                )
            body = self._dump_recetas_body(lista)
            atomic_write_text(self.recetas_path, body)
        except Exception as exc:
            raise VaultError(f"No se pudieron escribir recetas: {exc}") from exc
        return self.recetas_path

    def add_receta(self, r: Receta) -> Path:
        actuales = self.read_recetas()
        if any(x.id == r.id for x in actuales):
            raise DuplicateIdError(f"Ya existe una receta con id {r.id!r}")
        actuales.append(r)
        return self.write_recetas(actuales)

    def get_receta(self, id_: str) -> Receta | None:
        for r in self.read_recetas():
            if r.id == id_:
                return r
        return None

    def remove_receta(self, id_: str) -> bool:
        actuales = self.read_recetas()
        nuevas = [r for r in actuales if r.id != id_]
        if len(nuevas) == len(actuales):
            return False
        self.write_recetas(nuevas)
        return True

    # --- registro diario ---
    def _registro_dir(self, d: date) -> Path:
        return self.data_dir / "03-Registros" / f"{d.year:04d}" / _month_dir(d)

    def registro_path(self, d: date) -> Path:
        return self._registro_dir(d) / f"{d.isoformat()}.md"

    def read_registro(self, d: date) -> RegistroDiario | None:
        path = self.registro_path(d)
        if not path.exists():
            return None
        try:
            text = read_text(path)
            meta, body = frontmatter.parse(text)

            # Validar fecha del frontmatter contra el nombre del archivo
            fecha_str = meta.pop("fecha", None)
            if fecha_str is None:
                raise VaultError(f"Falta 'fecha' en {path}")
            try:
                fecha_meta = date.fromisoformat(str(fecha_str))
            except ValueError as exc:
                raise VaultError(f"Fecha inválida en {path}: {fecha_str!r}") from exc
            if fecha_meta != d:
                raise VaultError(
                    f"La fecha del frontmatter ({fecha_meta}) no coincide "
                    f"con el nombre del archivo ({d})."
                )

            # Actividad opcional en frontmatter como actividad_<campo>
            act_fields: dict[str, Any] = {}
            for k in list(meta.keys()):
                if k.startswith("actividad_"):
                    act_fields[k[len("actividad_"):]] = meta.pop(k)
            actividad = ActividadHabitual(**act_fields) if act_fields else None

            dia_fields: dict[str, Any] = {}
            for k in list(meta.keys()):
                if k.startswith("dia_"):
                    dia_fields[k[len("dia_"):]] = meta.pop(k)
            actividad_dia = ActividadDia(**dia_fields) if dia_fields else None

            observaciones = meta.pop("observaciones", None)
            meta.pop("tipo", None)
            if meta:
                raise VaultError(f"Claves desconocidas en {path}: {sorted(meta)}")

            # Items en el cuerpo como '## item-N' + bloque yaml
            raw_items = _parse_items(body)
            items: list[ItemComida] = []
            for r in raw_items:
                r.pop("id", None)
                items.append(ItemComida(**r))

            return RegistroDiario(
                fecha=d,
                items=items,
                actividad=actividad,
                actividad_dia=actividad_dia,
                observaciones=observaciones,
            )
        except VaultError:
            raise
        except Exception as exc:
            raise VaultError(f"No se pudo leer registro {d}: {exc}") from exc

    def write_registro(self, reg: RegistroDiario) -> Path:
        path = self.registro_path(reg.fecha)
        try:
            if path.exists():
                backup_file(path, self.backup_root, self._root_for_backup)

            meta: dict[str, Any] = {
                "tipo": "registro",
                "fecha": reg.fecha.isoformat(),
            }
            if reg.observaciones:
                meta["observaciones"] = reg.observaciones
            if reg.actividad is not None:
                for k, v in reg.actividad.model_dump(exclude_none=True).items():
                    meta[f"actividad_{k}"] = v
            if reg.actividad_dia is not None:
                for k, v in reg.actividad_dia.model_dump(exclude_none=True).items():
                    meta[f"dia_{k}"] = v

            body_lines: list[str] = [f"# Registro {reg.fecha.isoformat()}", ""]
            for idx, item in enumerate(reg.items, start=1):
                body_lines.append(f"## item-{idx}")
                body_lines.append("")
                body_lines.append("```yaml")
                item_meta = item.model_dump(mode="json", exclude_none=True)
                block = frontmatter.dump(item_meta, "")
                inner = block.splitlines()
                inner = inner[1:-1] if inner and inner[0] == "---" else inner
                body_lines.extend(inner)
                body_lines.append("```")
                body_lines.append("")

            body = "\n".join(body_lines)
            text = frontmatter.dump(meta, body)
            atomic_write_text(path, text)
        except Exception as exc:
            raise VaultError(f"No se pudo escribir registro {reg.fecha}: {exc}") from exc
        return path

    def list_registros(self, desde: date, hasta: date) -> list[date]:
        """Devuelve fechas con archivo de registro dentro de [desde, hasta]."""
        if hasta < desde:
            return []
        root = self.data_dir / "03-Registros"
        if not root.exists():
            return []
        fechas: set[date] = set()
        for p in root.rglob("*.md"):
            try:
                d = date.fromisoformat(p.stem)
            except ValueError:
                continue
            if desde <= d <= hasta:
                fechas.add(d)
        return sorted(fechas)