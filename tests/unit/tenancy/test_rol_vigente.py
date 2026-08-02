"""Pruebas de dominio: resolucion de rol vigente y vigencia de sesion
(Sprint S1.10, US1, FR-014, data-model.md)."""

from datetime import UTC, datetime, timedelta

import pytest
from aerohub_tenancy.domain import (
    RolAsignado,
    RolVigenteInconsistente,
    resolver_rol_vigente,
    sesion_vigente,
)

_AHORA = datetime(2026, 8, 2, 12, 0, tzinfo=UTC)


def _rol(**overrides) -> RolAsignado:
    base = dict(rol_id=1, codigo="role_tenant_admin", nombre="Admin", expira_en=None)
    base.update(overrides)
    return RolAsignado(**base)


def test_un_rol_vigente_se_resuelve():
    resultado = resolver_rol_vigente([_rol()], ahora=_AHORA)
    assert resultado is not None
    assert resultado.codigo == "role_tenant_admin"


def test_ningun_rol_devuelve_none():
    assert resolver_rol_vigente([], ahora=_AHORA) is None


def test_rol_expirado_se_ignora():
    expirado = _rol(expira_en=_AHORA - timedelta(days=1))
    assert resolver_rol_vigente([expirado], ahora=_AHORA) is None


def test_rol_con_expiracion_futura_es_vigente():
    vigente = _rol(expira_en=_AHORA + timedelta(days=1))
    resultado = resolver_rol_vigente([vigente], ahora=_AHORA)
    assert resultado is not None


def test_varios_roles_vigentes_simultaneos_es_inconsistencia():
    dos_roles = [
        _rol(rol_id=1, codigo="role_tenant_admin"),
        _rol(rol_id=2, codigo="role_ramp_agent"),
    ]
    with pytest.raises(RolVigenteInconsistente):
        resolver_rol_vigente(dos_roles, ahora=_AHORA)


def test_un_vigente_y_uno_expirado_no_es_inconsistencia():
    vigente = _rol(rol_id=1, codigo="role_tenant_admin")
    expirado = _rol(rol_id=2, codigo="role_ramp_agent", expira_en=_AHORA - timedelta(days=1))
    resultado = resolver_rol_vigente([vigente, expirado], ahora=_AHORA)
    assert resultado is not None
    assert resultado.codigo == "role_tenant_admin"


def test_sesion_vigente_sin_revocar_y_no_vencida():
    assert sesion_vigente(revocada_en=None, expira_en=_AHORA + timedelta(minutes=1), ahora=_AHORA)


def test_sesion_revocada_no_es_vigente():
    assert not sesion_vigente(
        revocada_en=_AHORA - timedelta(minutes=1),
        expira_en=_AHORA + timedelta(minutes=1),
        ahora=_AHORA,
    )


def test_sesion_vencida_no_es_vigente():
    assert not sesion_vigente(
        revocada_en=None, expira_en=_AHORA - timedelta(minutes=1), ahora=_AHORA
    )
