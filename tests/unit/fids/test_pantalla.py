from datetime import UTC, datetime, timedelta

import pytest
from aerohub_fids.domain import PantallaFids, PantallaInvalida


def _pantalla(**overrides):
    base = dict(
        id=1,
        tenant_id=1,
        terminal_id=1,
        codigo="T1-A1",
        plantilla_id=1,
        estado="en_linea",
    )
    base.update(overrides)
    return PantallaFids(**base)


def test_pantalla_valida_se_construye():
    p = _pantalla()
    assert p.codigo == "T1-A1"


def test_codigo_vacio_rechazado():
    with pytest.raises(PantallaInvalida):
        _pantalla(codigo="  ")


def test_estado_invalido_rechazado():
    with pytest.raises(PantallaInvalida):
        _pantalla(estado="apagada")


def test_sin_senal_si_nunca_reporto():
    p = _pantalla(ultima_senal_en=None)
    assert p.esta_sin_senal(datetime(2026, 1, 1, tzinfo=UTC), umbral_segundos=60)


def test_sin_senal_si_supera_el_umbral():
    ultima = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    p = _pantalla(ultima_senal_en=ultima)
    ahora = ultima + timedelta(seconds=61)
    assert p.esta_sin_senal(ahora, umbral_segundos=60)


def test_con_senal_dentro_del_umbral():
    ultima = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    p = _pantalla(ultima_senal_en=ultima)
    ahora = ultima + timedelta(seconds=59)
    assert not p.esta_sin_senal(ahora, umbral_segundos=60)
