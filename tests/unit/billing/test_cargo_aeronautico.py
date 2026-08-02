from decimal import Decimal

import pytest
from aerohub_billing.domain import CargoAeronauticoInvalido, calcular_monto


def test_calcula_monto_simple():
    r = calcular_monto(cantidad=Decimal(2), tarifa_unitaria=Decimal("10.00"), moneda="USD")
    assert r.tarifa_aplicada == Decimal("10.00")
    assert r.monto.monto == Decimal("20.00")
    assert r.monto.moneda == "USD"


def test_respeta_monto_minimo():
    r = calcular_monto(
        cantidad=Decimal(1),
        tarifa_unitaria=Decimal("1.00"),
        moneda="USD",
        monto_minimo=Decimal("50.00"),
    )
    assert r.monto.monto == Decimal("50.00")


def test_respeta_monto_maximo():
    r = calcular_monto(
        cantidad=Decimal(100),
        tarifa_unitaria=Decimal("10.00"),
        moneda="USD",
        monto_maximo=Decimal("500.00"),
    )
    assert r.monto.monto == Decimal("500.00")


def test_cantidad_cero_rechazada():
    with pytest.raises(CargoAeronauticoInvalido):
        calcular_monto(cantidad=Decimal(0), tarifa_unitaria=Decimal("10.00"), moneda="USD")


def test_tarifa_negativa_rechazada():
    with pytest.raises(CargoAeronauticoInvalido):
        calcular_monto(cantidad=Decimal(1), tarifa_unitaria=Decimal("-1.00"), moneda="USD")
