"""Pruebas de la lógica del asistente de configuración."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.models.domain import Sexo
from app.setup.wizard import SetupInput, aplicar_setup, perfil_existente
from app.storage.vault import Vault


@pytest.fixture
def vault(tmp_path: Path) -> Vault:
    data = tmp_path / "vault"
    backups = tmp_path / "backups"
    data.mkdir()
    backups.mkdir()
    return Vault(data, backups, root_for_backup=tmp_path)


def _input(**kw) -> SetupInput:
    base = dict(
        nombre="Renzo",
        edad=30,
        peso_kg=75.0,
        altura_cm=178.0,
        sexo="masculino",
        unidad_peso="kg",
        unidad_altura="cm",
        objetivo="mantenimiento",
    )
    base.update(kw)
    return SetupInput(**base)


def test_perfil_existente_falso_inicial(vault: Vault):
    assert perfil_existente(vault) is False


def test_setup_completo_guarda_perfil_objetivos_actividad(vault: Vault):
    data = _input(
        kcal_diarias=2200,
        proteina_g=150,
        tipo_trabajo="oficina",
        horas_actividad_laboral=8,
        frecuencia_gimnasio_semanal=3,
    )
    out = aplicar_setup(data, vault)
    assert out.ok is True, out.errores
    assert out.perfil is not None
    assert out.perfil.edad == 30
    assert out.objetivos is not None and out.objetivos.kcal_diarias == 2200
    assert out.actividad is not None and out.actividad.tipo_trabajo == "oficina"
    assert perfil_existente(vault) is True
    assert len(out.rutas_escritas) == 3


def test_setup_solo_perfil_sin_objetivos_ni_actividad(vault: Vault):
    out = aplicar_setup(_input(), vault)
    assert out.ok is True
    assert out.objetivos is None
    assert out.actividad is None
    # Solo se escribe perfil.md
    assert len(out.rutas_escritas) == 1
    # objetivos.md y actividad.md no deben existir
    assert not (vault.data_dir / "01-Perfil" / "objetivos.md").exists()
    assert not (vault.data_dir / "01-Perfil" / "actividad.md").exists()


def test_setup_sin_edad_falla(vault: Vault):
    data = _input(edad=None)
    out = aplicar_setup(data, vault)
    assert out.ok is False
    assert any(e.campo == "edad" for e in out.errores)
    assert perfil_existente(vault) is False


def test_setup_sin_peso_falla(vault: Vault):
    data = _input(peso_kg=None)
    out = aplicar_setup(data, vault)
    assert out.ok is False
    assert any(e.campo == "peso_kg" for e in out.errores)


def test_setup_sin_altura_falla(vault: Vault):
    data = _input(altura_cm=None)
    out = aplicar_setup(data, vault)
    assert out.ok is False
    assert any(e.campo == "altura_cm" for e in out.errores)


def test_setup_edad_fuera_de_rango(vault: Vault):
    data = _input(edad=0)
    out = aplicar_setup(data, vault)
    assert out.ok is False
    assert any(e.campo == "edad" for e in out.errores)


def test_setup_no_sobrescribe_por_defecto(vault: Vault):
    out1 = aplicar_setup(_input(), vault)
    assert out1.ok is True
    out2 = aplicar_setup(_input(edad=31), vault)
    assert out2.ok is False
    assert any(e.campo == "perfil" for e in out2.errores)


def test_setup_sobrescribe_explicito(vault: Vault):
    aplicar_setup(_input(), vault)
    out = aplicar_setup(_input(edad=31), vault, sobrescribir=True)
    assert out.ok is True
    p = vault.read_perfil()
    assert p is not None and p.edad == 31


def test_setup_sexo_desconocido_se_normaliza(vault: Vault):
    data = _input(sexo=None)
    out = aplicar_setup(data, vault)
    assert out.ok is True
    assert out.perfil is not None
    assert out.perfil.sexo == Sexo.NO_ESPECIFICADO


def test_setup_objetivos_invalidos(vault: Vault):
    data = _input(kcal_diarias=-10)
    out = aplicar_setup(data, vault)
    assert out.ok is False
    assert any("kcal_diarias" in e.campo for e in out.errores)
    assert perfil_existente(vault) is False


def test_setup_actividad_invalida(vault: Vault):
    data = _input(frecuencia_gimnasio_semanal=99)
    out = aplicar_setup(data, vault)
    assert out.ok is False
    assert any("frecuencia_gimnasio_semanal" in e.campo for e in out.errores)


def test_setup_modelo_se_propaga(vault: Vault):
    data = _input(modelo="qwen3:4b-instruct-2507-q4_K_M")
    out = aplicar_setup(data, vault)
    assert out.ok is True
    assert out.modelo == "qwen3:4b-instruct-2507-q4_K_M"