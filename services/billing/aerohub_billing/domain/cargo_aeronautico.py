"""Calculo de un cargo aeronautico -- instantanea inmutable de un hecho
facturable (Sprint S1.6, CU-O17; SDD-DATA-001 Sec9.4).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 Sec5.4,
regla 1). `calcular_monto` es la UNICA formula del sprint -- se invoca una
vez, en el momento del calculo, y el resultado (tarifa_aplicada,
monto_calculado) se persiste sin recalculo posterior (research.md
Decision 5): este modulo nunca se ejecuta contra un cargo ya existente.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from aerohub_kernel import Dinero


class CargoAeronauticoInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class MontoCalculado:
    tarifa_aplicada: Decimal
    monto: Dinero


def calcular_monto(
    *,
    cantidad: Decimal,
    tarifa_unitaria: Decimal,
    moneda: str,
    monto_minimo: Decimal | None = None,
    monto_maximo: Decimal | None = None,
) -> MontoCalculado:
    """cantidad * tarifa_unitaria, con clamp a [monto_minimo, monto_maximo]
    si estan definidos (billing.tarifario_concepto, SDD-DATA-001 Sec9.3).
    `tarifa_aplicada` se devuelve sin modificar -- es la instantanea que se
    persiste, el clamp solo afecta al monto final.
    """
    if cantidad <= 0:
        raise CargoAeronauticoInvalido(f"cantidad debe ser > 0 (recibido {cantidad})")
    if tarifa_unitaria < 0:
        raise CargoAeronauticoInvalido(
            f"tarifa_unitaria debe ser >= 0 (recibido {tarifa_unitaria})"
        )

    monto = cantidad * tarifa_unitaria
    if monto_minimo is not None and monto < monto_minimo:
        monto = monto_minimo
    if monto_maximo is not None and monto > monto_maximo:
        monto = monto_maximo

    return MontoCalculado(tarifa_aplicada=tarifa_unitaria, monto=Dinero(monto, moneda))
