import pytest
from aerohub_repository.contexto import (
    ContextoTenantAusente,
    _establecer_rol_actor,
    _establecer_tenant_id,
    _establecer_usuario_id,
    alcance_global,
    alcance_global_activo,
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
    rol_activo_de_sesion,
)


def test_contexto_ausente_lanza():
    with pytest.raises(ContextoTenantAusente):
        contexto_tenant_id()


def test_contexto_poblado_por_middleware():
    token = _establecer_tenant_id(42)
    try:
        assert contexto_tenant_id() == 42
    finally:
        import aerohub_repository.contexto as mod

        mod._tenant_id.reset(token)


def test_alcance_global_exige_motivo_y_rol():
    with pytest.raises(ValueError), alcance_global(motivo="", rol="role_data_engineer"):
        pass
    with pytest.raises(ValueError), alcance_global(motivo="extraccion_bronce", rol=""):
        pass


def test_alcance_global_se_registra_y_se_limpia():
    assert alcance_global_activo() is None
    with alcance_global(motivo="extraccion_bronce", rol="role_elt_reader"):
        info = alcance_global_activo()
        assert info is not None
        assert info.motivo == "extraccion_bronce"
        assert info.rol == "role_elt_reader"
    assert alcance_global_activo() is None


def test_rol_actor_ausente_lanza():
    with pytest.raises(ContextoTenantAusente):
        contexto_rol_actor()


def test_rol_actor_poblado_por_middleware():
    token = _establecer_rol_actor("role_operations_controller")
    try:
        assert contexto_rol_actor() == "role_operations_controller"
    finally:
        import aerohub_repository.contexto as mod

        mod._rol_actor.reset(token)


def test_usuario_id_ausente_devuelve_none_sin_lanzar():
    assert contexto_usuario_id() is None


def test_usuario_id_poblado_por_middleware():
    token = _establecer_usuario_id(7)
    try:
        assert contexto_usuario_id() == 7
    finally:
        import aerohub_repository.contexto as mod

        mod._usuario_id.reset(token)


def test_rol_activo_de_sesion_usa_rol_actor_sin_alcance_global():
    token = _establecer_rol_actor("role_billing_officer")
    try:
        assert rol_activo_de_sesion() == "role_billing_officer"
    finally:
        import aerohub_repository.contexto as mod

        mod._rol_actor.reset(token)


def test_rol_activo_de_sesion_usa_el_rol_de_alcance_global_si_esta_activo():
    token = _establecer_rol_actor("role_billing_officer")
    try:
        with alcance_global(motivo="extraccion_bronce", rol="role_elt_reader"):
            assert rol_activo_de_sesion() == "role_elt_reader"
        assert rol_activo_de_sesion() == "role_billing_officer"
    finally:
        import aerohub_repository.contexto as mod

        mod._rol_actor.reset(token)
