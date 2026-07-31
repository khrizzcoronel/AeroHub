import pytest
from aerohub_aodb.domain import (
    EstadoVuelo,
    TransicionEstadoInvalida,
    validar_origen_cambio,
    validar_transicion,
)

PROGRAMADO = EstadoVuelo(id=1, codigo="programado", es_terminal=False)
EMBARCANDO = EstadoVuelo(id=2, codigo="embarcando", es_terminal=False)
ATERRIZADO = EstadoVuelo(id=3, codigo="aterrizado", es_terminal=True)
CANCELADO = EstadoVuelo(id=4, codigo="cancelado", es_terminal=True)


def test_primer_estado_siempre_valido():
    validar_transicion(None, PROGRAMADO)  # no lanza


def test_transicion_entre_no_terminales_valida():
    validar_transicion(PROGRAMADO, EMBARCANDO)  # no lanza


def test_transicion_a_terminal_valida():
    validar_transicion(EMBARCANDO, ATERRIZADO)  # no lanza


def test_transicion_desde_terminal_rechazada():
    with pytest.raises(TransicionEstadoInvalida):
        validar_transicion(ATERRIZADO, EMBARCANDO)


def test_transicion_entre_dos_terminales_rechazada():
    with pytest.raises(TransicionEstadoInvalida):
        validar_transicion(ATERRIZADO, CANCELADO)


@pytest.mark.parametrize("origen", ["manual", "api", "automatico"])
def test_origen_cambio_valido(origen):
    validar_origen_cambio(origen)  # no lanza


def test_origen_cambio_invalido_rechazado():
    with pytest.raises(TransicionEstadoInvalida):
        validar_origen_cambio("desconocido")
