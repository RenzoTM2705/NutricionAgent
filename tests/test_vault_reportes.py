"""Pruebas de persistencia de reportes en Vault."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.core.report_models import (
    BalanceResumen,
    ItemResumen,
    ReporteDiario,
    ReporteMensual,
    ReporteSemanal,
)
from app.core.results import Fuente, Nutrientes
from app.models.domain import Unidad
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _reporte_diario() -> ReporteDiario:
    return ReporteDiario(
        fecha=date(2026, 11, 12),
        items=[
            ItemResumen(
                indice=1, ref_tipo="alimento", ref_id="arroz",
                cantidad=150.0, unidad=Unidad.G, kcal=195.0,
                proteina_g=4.05, grasa_g=0.45, carbo_g=42.0,
            ),
        ],
        totales=Nutrientes(kcal=195.0, proteina_g=4.05, grasa_g=0.45, carbo_g=42.0),
        balance=BalanceResumen(
            consumo_kcal=195.0, gasto_kcal=2600.0,
            balance_kcal=-2405.0, fuente=Fuente.CALCULADO,
        ),
        fuente=Fuente.CALCULADO,
    )


def test_write_read_diario(vault: Vault):
    r = _reporte_diario()
    path = vault.write_reporte_diario(r)
    assert path.exists()
    assert path.name == "2026-11-12.md"
    got = vault.read_reporte_diario(date(2026, 11, 12))
    assert got is not None
    assert got.fecha == date(2026, 11, 12)
    assert got.fuente == Fuente.CALCULADO


def test_diario_contiene_tablas(vault: Vault):
    r = _reporte_diario()
    path = vault.write_reporte_diario(r)
    text = path.read_text(encoding="utf-8")
    assert "| # | Ref |" in text
    assert "| Kcal | 195.0 |" in text
    assert "| Balance (kcal) | -2405.0 |" in text


def test_diario_backup(vault: Vault, tmp_path: Path):
    r = _reporte_diario()
    vault.write_reporte_diario(r)
    vault.write_reporte_diario(r)
    backups = list((tmp_path / "backups").rglob("2026-11-12.md"))
    assert len(backups) == 1


def test_read_diario_inexistente(vault: Vault):
    assert vault.read_reporte_diario(date(2026, 11, 12)) is None


def test_write_read_semanal(vault: Vault):
    r = ReporteSemanal(
        desde=date(2026, 11, 9),
        hasta=date(2026, 11, 15),
        dias_con_datos=5,
        dias_sin_datos=2,
        dias_entrenados=3,
        promedios=Nutrientes(kcal=2100.0, proteina_g=140.0),
        balance_promedio=BalanceResumen(
            consumo_kcal=2100.0, gasto_kcal=2400.0,
            balance_kcal=-300.0, fuente=Fuente.CALCULADO,
        ),
        fuente=Fuente.CALCULADO,
    )
    path = vault.write_reporte_semanal(r)
    assert path.exists()
    got = vault.read_reporte_semanal(2026, 46)  # 9-15 nov 2026 es semana ISO 46
    assert got is not None
    assert got.dias_con_datos == 5
    assert got.dias_entrenados == 3


def test_read_semanal_inexistente(vault: Vault):
    assert vault.read_reporte_semanal(2026, 1) is None


def test_write_read_mensual(vault: Vault):
    r = ReporteMensual(
        desde=date(2026, 11, 1),
        hasta=date(2026, 11, 30),
        dias_con_datos=20,
        dias_sin_datos=10,
        dias_entrenados=12,
        consistencia_pct=66.7,
        promedios=Nutrientes(kcal=2100.0),
        balance_promedio=BalanceResumen(fuente=Fuente.PARCIAL),
        fuente=Fuente.PARCIAL,
    )
    path = vault.write_reporte_mensual(r)
    assert path.exists()
    got = vault.read_reporte_mensual(2026, 11)
    assert got is not None
    assert got.dias_con_datos == 20
    assert got.consistencia_pct == 66.7


def test_read_mensual_inexistente(vault: Vault):
    assert vault.read_reporte_mensual(2026, 1) is None