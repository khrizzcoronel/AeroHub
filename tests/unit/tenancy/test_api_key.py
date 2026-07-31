from datetime import UTC, datetime, timedelta

import pytest
from aerohub_tenancy.domain import ApiKey, ApiKeyInvalida


def _api_key(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        prefijo="0123456789ab",
        hash_secreto="hash-fake",
        creada_en=datetime(2026, 1, 1, tzinfo=UTC),
        estado="activa",
    )
    base.update(overrides)
    return ApiKey(**base)


def test_api_key_valida_se_construye():
    k = _api_key()
    assert k.prefijo == "0123456789ab"


@pytest.mark.parametrize(
    "prefijo", ["", "corto", "A123456789AB", "0123456789ab0", "0123456789g"]
)
def test_prefijo_invalido_rechazado(prefijo):
    with pytest.raises(ApiKeyInvalida):
        _api_key(prefijo=prefijo)


def test_hash_secreto_vacio_rechazado():
    with pytest.raises(ApiKeyInvalida):
        _api_key(hash_secreto="")


def test_estado_invalido_rechazado():
    with pytest.raises(ApiKeyInvalida):
        _api_key(estado="pausada")


def test_api_key_activa_sin_expiracion_esta_vigente():
    k = _api_key(estado="activa", expira_en=None)
    assert k.esta_vigente(datetime(2030, 1, 1, tzinfo=UTC))


def test_api_key_revocada_no_esta_vigente():
    k = _api_key(estado="revocada")
    assert not k.esta_vigente(datetime(2026, 1, 1, tzinfo=UTC))


def test_api_key_expirada_no_esta_vigente():
    expira = datetime(2026, 6, 1, tzinfo=UTC)
    k = _api_key(estado="activa", expira_en=expira)
    assert not k.esta_vigente(expira)
    assert not k.esta_vigente(expira + timedelta(seconds=1))


def test_api_key_activa_antes_de_expirar_esta_vigente():
    expira = datetime(2026, 6, 1, tzinfo=UTC)
    k = _api_key(estado="activa", expira_en=expira)
    assert k.esta_vigente(expira - timedelta(seconds=1))
