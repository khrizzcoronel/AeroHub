"""Tipo de dominio para montos monetarios (SDD-DATA-001 §4: DECIMAL(14,2), moneda ISO 4217).

Sin dependencia de framework: es el tipo que domain/ de cualquier modulo puede
usar sin arrastrar SQLAlchemy ni Pydantic.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_CUANTIZACION = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Dinero:
    monto: Decimal
    moneda: str  # ISO 4217, 3 letras

    def __post_init__(self) -> None:
        if len(self.moneda) != 3 or not self.moneda.isalpha():
            raise ValueError(f"moneda debe ser codigo ISO 4217 de 3 letras: {self.moneda!r}")
        cuantizado = self.monto.quantize(_CUANTIZACION, rounding=ROUND_HALF_UP)
        object.__setattr__(self, "monto", cuantizado)

    def _verificar_misma_moneda(self, otro: Dinero) -> None:
        if self.moneda != otro.moneda:
            raise ValueError(f"monedas incompatibles: {self.moneda} vs {otro.moneda}")

    def __add__(self, otro: Dinero) -> Dinero:
        self._verificar_misma_moneda(otro)
        return Dinero(self.monto + otro.monto, self.moneda)

    def __sub__(self, otro: Dinero) -> Dinero:
        self._verificar_misma_moneda(otro)
        return Dinero(self.monto - otro.monto, self.moneda)

    def __mul__(self, factor: Decimal | int) -> Dinero:
        return Dinero(self.monto * Decimal(factor), self.moneda)

    def __lt__(self, otro: Dinero) -> bool:
        self._verificar_misma_moneda(otro)
        return self.monto < otro.monto

    def __le__(self, otro: Dinero) -> bool:
        self._verificar_misma_moneda(otro)
        return self.monto <= otro.monto
