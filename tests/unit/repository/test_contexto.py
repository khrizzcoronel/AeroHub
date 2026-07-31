import pytest
from aerohub_repository.contexto import (
    ContextoTenantAusente,
    _establecer_tenant_id,
    alcance_global,
    alcance_global_activo,
    contexto_tenant_id,
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
