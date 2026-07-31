import time

from aerohub_gateway.infrastructure.limitador import LimitadorTasa


def test_primera_peticion_siempre_se_permite():
    limitador = LimitadorTasa(capacidad=5, tasa_recarga=1.0)
    assert limitador.permitir("clave-a")


def test_agota_el_cupo_y_rechaza():
    limitador = LimitadorTasa(capacidad=3, tasa_recarga=0.0)  # sin recarga -- cupo fijo
    assert limitador.permitir("clave-a")
    assert limitador.permitir("clave-a")
    assert limitador.permitir("clave-a")
    assert not limitador.permitir("clave-a")


def test_cupos_independientes_por_clave():
    limitador = LimitadorTasa(capacidad=1, tasa_recarga=0.0)
    assert limitador.permitir("clave-a")
    assert not limitador.permitir("clave-a")
    assert limitador.permitir("clave-b")  # cupo propio, no compartido


def test_recarga_con_el_tiempo():
    limitador = LimitadorTasa(capacidad=1, tasa_recarga=100.0)  # recarga rapida
    assert limitador.permitir("clave-a")
    assert not limitador.permitir("clave-a")
    time.sleep(0.05)  # a 100 fichas/s, 0.05s recarga ~5 fichas
    assert limitador.permitir("clave-a")
