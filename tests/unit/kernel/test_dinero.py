from decimal import Decimal

import pytest
from aerohub_kernel import Dinero


def test_cuantiza_a_dos_decimales():
    d = Dinero(Decimal("10.005"), "USD")
    assert d.monto == Decimal("10.01")


def test_moneda_debe_ser_iso4217_de_tres_letras():
    with pytest.raises(ValueError):
        Dinero(Decimal("10"), "US")


def test_suma_misma_moneda():
    a = Dinero(Decimal("10.50"), "USD")
    b = Dinero(Decimal("5.25"), "USD")
    assert (a + b).monto == Decimal("15.75")


def test_suma_monedas_distintas_falla():
    a = Dinero(Decimal("10"), "USD")
    b = Dinero(Decimal("10"), "EUR")
    with pytest.raises(ValueError):
        _ = a + b


def test_comparacion():
    barato = Dinero(Decimal("5"), "USD")
    caro = Dinero(Decimal("10"), "USD")
    assert barato < caro
    assert barato <= barato
