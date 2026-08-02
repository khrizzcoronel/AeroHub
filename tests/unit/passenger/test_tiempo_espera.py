from datetime import time
from decimal import Decimal

from aerohub_passenger.domain import (
    agregacion_por_franja,
    descarta_por_muestra_insuficiente,
    franja_de,
)


def test_franja_de_bucketiza_por_ancho():
    inicio, fin = franja_de(time(8, 17), franja_minutos=30)
    assert inicio == time(8, 0)
    assert fin == time(8, 30)


def test_franja_de_segunda_mitad_de_la_hora():
    inicio, fin = franja_de(time(8, 45), franja_minutos=30)
    assert inicio == time(8, 30)
    assert fin == time(9, 0)


def test_agregacion_promedia_las_duraciones():
    r = agregacion_por_franja([Decimal(10), Decimal(20), Decimal(30)])
    assert r.minutos_estimados == Decimal("20.00")
    assert r.muestra_n == 3


def test_agregacion_sin_muestras():
    r = agregacion_por_franja([])
    assert r.muestra_n == 0
    assert r.minutos_estimados == Decimal("0")


def test_descarta_por_muestra_insuficiente():
    assert descarta_por_muestra_insuficiente(0) is True
    assert descarta_por_muestra_insuficiente(1) is False
