from datetime import UTC, datetime, timedelta, timezone

import pytest
from aerohub_aodb.domain import Vuelo, VueloInvalido


def _vuelo(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        aerolinea_id=1,
        aeronave_id=1,
        numero_vuelo="XX100",
        tipo_vuelo_id=1,
        fecha_operacion="2026-08-01",
        sentido="L",
        aeropuerto_origen_id=1,
        aeropuerto_destino_id=2,
        sta_utc=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        std_utc=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
    )
    base.update(overrides)
    return Vuelo(**base)


def test_vuelo_valido_se_construye():
    v = _vuelo()
    assert v.numero_vuelo == "XX100"


def test_sentido_invalido_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(sentido="X")


def test_origen_igual_a_destino_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(aeropuerto_origen_id=5, aeropuerto_destino_id=5)


def test_std_posterior_a_sta_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(
            std_utc=datetime(2026, 8, 1, 11, 0, tzinfo=UTC),
            sta_utc=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
        )


def test_std_igual_a_sta_rechazado():
    momento = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    with pytest.raises(VueloInvalido):
        _vuelo(std_utc=momento, sta_utc=momento)


def test_sta_std_naive_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(sta_utc=datetime(2026, 8, 1, 10, 0), std_utc=datetime(2026, 8, 1, 9, 0))


def test_sta_std_en_otro_huso_rechazado():
    otro_huso = timezone(timedelta(hours=-5))
    with pytest.raises(VueloInvalido):
        _vuelo(
            sta_utc=datetime(2026, 8, 1, 10, 0, tzinfo=otro_huso),
            std_utc=datetime(2026, 8, 1, 9, 0, tzinfo=UTC),
        )


def test_atd_posterior_a_ata_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(
            ata_utc=datetime(2026, 8, 1, 10, 0, tzinfo=UTC),
            atd_utc=datetime(2026, 8, 1, 10, 5, tzinfo=UTC),
        )


def test_atd_igual_a_ata_permitido():
    momento = datetime(2026, 8, 1, 10, 0, tzinfo=UTC)
    v = _vuelo(ata_utc=momento, atd_utc=momento)
    assert v.ata_utc == v.atd_utc


def test_atd_sin_ata_no_valida_coherencia():
    # Aterrizaje aun no ocurrido: atd_utc solo no es suficiente para
    # disparar la validacion (se necesitan ambos para comparar).
    v = _vuelo(atd_utc=datetime(2026, 8, 1, 9, 5, tzinfo=UTC))
    assert v.ata_utc is None


def test_numero_vuelo_vacio_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(numero_vuelo="   ")


def test_pax_estimado_negativo_rechazado():
    with pytest.raises(VueloInvalido):
        _vuelo(pax_estimado=-1)


def test_pax_estimado_cero_permitido():
    v = _vuelo(pax_estimado=0)
    assert v.pax_estimado == 0


def test_vuelo_es_inmutable():
    v = _vuelo()
    with pytest.raises(AttributeError):
        v.numero_vuelo = "YY200"
