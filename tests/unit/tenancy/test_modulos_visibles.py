"""Pruebas de dominio: mitad pura del calculo de modulos visibles (Sprint
S1.10, US2, research.md Decision 4) -- el mapeo rol -> modulos de
`aerohub_contracts.roles_modulos`. La otra mitad (interseccion con
licencia vigente) se verifica en integracion
(`tests/integration/test_perfil_modulos_visibles.py`), no aqui: necesita
`tenants.licencia` real, este archivo no toca la base."""

from aerohub_contracts import MODULOS, modulos_del_rol, scopes_del_rol


def test_role_platform_admin_no_ve_ningun_modulo_operativo():
    """Sprint S1.11 invirtio la expectativa original de S1.10 (que este rol
    veia los 9 modulos): role_platform_admin no tiene tenant propio ni
    scopes de negocio, asi que el menu le ofrecia pantallas que producian
    403 al primer clic. Su superficie real es administrar tenants/API Keys,
    que no depende de `modulos_visibles`.

    Este test quedo afirmando lo contrario desde S1.11 -- corregido en la
    auditoria de la capa operativa (2026-08-08) al encontrarlo en rojo.
    """
    assert modulos_del_rol("role_platform_admin") == frozenset()
    assert len(MODULOS) == 9  # el catalogo sigue teniendo los 9 modulos


def test_role_ramp_agent_ve_solo_su_modulo():
    assert modulos_del_rol("role_ramp_agent") == frozenset({"M4"})


def test_role_people_viewer_no_ve_ningun_modulo():
    assert modulos_del_rol("role_people_viewer") == frozenset()


def test_role_tenant_admin_no_ve_m7_ni_m8():
    modulos = modulos_del_rol("role_tenant_admin")
    assert "M7" not in modulos
    assert "M8" not in modulos
    assert "M1" in modulos


def test_rol_desconocido_no_ve_ningun_modulo():
    assert modulos_del_rol("role_inexistente") == frozenset()


def test_dos_roles_distintos_ven_conjuntos_distintos():
    assert modulos_del_rol("role_ramp_agent") != modulos_del_rol("role_billing_officer")


def test_rol_desconocido_no_tiene_scopes():
    assert scopes_del_rol("role_inexistente") == frozenset()
