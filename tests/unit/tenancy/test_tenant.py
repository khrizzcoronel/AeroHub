import pytest
from aerohub_tenancy.domain import (
    Tenant,
    TenantInvalido,
    TransicionTenantInvalida,
    validar_transicion_estado,
)


def _tenant(**overrides):
    base = dict(
        id=1,
        codigo="MEC",
        razon_social="Aeropuerto de Prueba",
        aeropuerto_id=1,
        plan_id=1,
        estado="en_onboarding",
    )
    base.update(overrides)
    return Tenant(**base)


def test_tenant_valido_se_construye():
    t = _tenant()
    assert t.codigo == "MEC"


@pytest.mark.parametrize("codigo", ["", "m", "codigo con espacios", "a" * 31])
def test_codigo_invalido_rechazado(codigo):
    with pytest.raises(TenantInvalido):
        _tenant(codigo=codigo)


def test_razon_social_vacia_rechazada():
    with pytest.raises(TenantInvalido):
        _tenant(razon_social="   ")


def test_estado_invalido_rechazado():
    with pytest.raises(TenantInvalido):
        _tenant(estado="borrado")


def test_transicion_en_onboarding_a_activo_valida():
    validar_transicion_estado("en_onboarding", "activo")  # no lanza


def test_transicion_activo_a_suspendido_valida():
    validar_transicion_estado("activo", "suspendido")  # no lanza


def test_transicion_suspendido_a_activo_valida():
    validar_transicion_estado("suspendido", "activo")  # no lanza


def test_transicion_desde_dado_de_baja_rechazada():
    with pytest.raises(TransicionTenantInvalida):
        validar_transicion_estado("dado_de_baja", "activo")


def test_transicion_en_onboarding_a_suspendido_rechazada():
    # en_onboarding solo admite activo o dado_de_baja directamente.
    with pytest.raises(TransicionTenantInvalida):
        validar_transicion_estado("en_onboarding", "suspendido")


def test_transicion_a_estado_desconocido_rechazada():
    with pytest.raises(TransicionTenantInvalida):
        validar_transicion_estado("activo", "inexistente")
