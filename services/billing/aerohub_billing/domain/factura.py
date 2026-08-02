"""Invariantes de factura y transiciones de estado (Sprint S1.6, CU-O17;
SDD-DATA-001 Sec9.5-9.6).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 Sec5.4,
regla 1). `total()` NO vive aqui -- se deriva por agregacion de
factura_linea en infrastructure/ (3NF, SDD-DATA-001 Sec9.5), no es un
calculo de dominio sobre datos que domain/ tenga en memoria.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

ESTADOS_FACTURA = ("borrador", "emitida", "pagada", "vencida", "disputada")

# Transiciones permitidas -- 'disputada' solo alcanzable desde 'emitida'
# (FR-007: role_billing_officer disputa una factura YA emitida, nunca una
# en borrador que el motor todavia esta construyendo).
_TRANSICIONES_VALIDAS: dict[str, tuple[str, ...]] = {
    "borrador": ("emitida",),
    "emitida": ("pagada", "vencida", "disputada"),
    "pagada": (),
    "vencida": (),
    "disputada": (),
}


class FacturaInvalida(Exception):
    pass


class TransicionInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Factura:
    id: int
    tenant_id: int
    aerolinea_id: int
    periodo_inicio: date
    periodo_fin: date
    moneda: str
    estado: str

    def __post_init__(self) -> None:
        if len(self.moneda) != 3 or not self.moneda.isalpha():
            raise FacturaInvalida(f"moneda debe ser codigo ISO 4217 de 3 letras: {self.moneda!r}")
        if self.estado not in ESTADOS_FACTURA:
            raise FacturaInvalida(f"estado invalido: {self.estado!r}")
        if self.periodo_fin < self.periodo_inicio:
            raise FacturaInvalida(
                f"periodo_fin ({self.periodo_fin}) no puede ser anterior a "
                f"periodo_inicio ({self.periodo_inicio})"
            )


def validar_transicion(*, estado_actual: str, estado_nuevo: str) -> None:
    if estado_nuevo not in _TRANSICIONES_VALIDAS.get(estado_actual, ()):
        raise TransicionInvalida(
            f"factura en estado {estado_actual!r} no puede transicionar a {estado_nuevo!r}"
        )
