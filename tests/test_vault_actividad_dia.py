"""Pruebas de serialización de actividad_dia en Vault."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.models.domain import ActividadDia, RegistroDiario
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def test_registro_sin_actividad_dia(vault: Vault):
    reg = RegistroDiario(fecha=date(2026, 11, 12))
    vault.write_registro(reg)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.actividad_dia is None


def test_registro_con_actividad_dia_completa(vault: Vault):
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(
            horas_trabajo=8.0,
            horas_de_pie=4.0,
            pasos=9000,
            gimnasio=True,
            gimnasio_duracion_min=60,
            tipo_entrenamiento="fuerza",
            otros_deportes="caminata",
            notas="buen día",
        ),
    )
    vault.write_registro(reg)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    a = got.actividad_dia
    assert a is not None
    assert a.horas_trabajo == 8.0
    assert a.horas_de_pie == 4.0
    assert a.pasos == 9000
    assert a.gimnasio is True
    assert a.gimnasio_duracion_min == 60
    assert a.tipo_entrenamiento == "fuerza"
    assert a.otros_deportes == "caminata"
    assert a.notas == "buen día"


def test_registro_actividad_dia_parcial(vault: Vault):
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(pasos=8000),
    )
    vault.write_registro(reg)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.actividad_dia is not None
    assert got.actividad_dia.pasos == 8000
    assert got.actividad_dia.gimnasio is None
    assert got.actividad_dia.horas_trabajo is None


def test_frontmatter_contiene_dia(vault: Vault):
    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(pasos=9000, gimnasio=True),
    )
    vault.write_registro(reg)
    text = vault.registro_path(date(2026, 11, 12)).read_text(encoding="utf-8")
    assert "dia_pasos: 9000" in text
    assert "dia_gimnasio: true" in text


def test_actividad_habitual_y_dia_coexisten(vault: Vault):
    from app.models.domain import ActividadHabitual

    reg = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad=ActividadHabitual(tipo_trabajo="oficina"),
        actividad_dia=ActividadDia(pasos=9000),
    )
    vault.write_registro(reg)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.actividad is not None
    assert got.actividad.tipo_trabajo == "oficina"
    assert got.actividad_dia is not None
    assert got.actividad_dia.pasos == 9000


def test_sobrescribir_actividad_dia(vault: Vault, tmp_path: Path):
    reg1 = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(pasos=5000),
    )
    vault.write_registro(reg1)
    reg2 = RegistroDiario(
        fecha=date(2026, 11, 12),
        actividad_dia=ActividadDia(pasos=10000),
    )
    vault.write_registro(reg2)
    got = vault.read_registro(date(2026, 11, 12))
    assert got is not None
    assert got.actividad_dia is not None
    assert got.actividad_dia.pasos == 10000
    backups = list((tmp_path / "backups").rglob("2026-11-12.md"))
    assert len(backups) == 1