"""Invariantes de tarifario (Sprint S1.6, Plan Sec8.6, RF-T10;
SDD-DATA-001 Sec9.2).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 Sec5.4,
regla 1). "A lo sumo un tarifario vigente por (tenant_id, moneda)" se
valida en infrastructure/ (requiere consultar otras filas, dato que
domain/ no conoce) -- aqui solo las invariantes de una fila aislada.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

ESTADOS_TARIFARIO = ("borrador", "vigente", "expirado")


class TarifarioInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Tarifario:
    id: int
    tenant_id: int
    nombre: str
    moneda: str
    vigente_desde: date
    estado: str
    creado_por_usuario_id: int
    vigente_hasta: date | None = None

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise TarifarioInvalido("nombre no puede ser vacio")
        if len(self.moneda) != 3 or not self.moneda.isalpha():
            raise TarifarioInvalido(f"moneda debe ser codigo ISO 4217 de 3 letras: {self.moneda!r}")
        if self.estado not in ESTADOS_TARIFARIO:
            raise TarifarioInvalido(f"estado invalido: {self.estado!r}")
        if self.vigente_hasta is not None and self.vigente_hasta < self.vigente_desde:
            raise TarifarioInvalido(
                f"vigente_hasta ({self.vigente_hasta}) no puede ser anterior a "
                f"vigente_desde ({self.vigente_desde})"
            )

    def vigente_en(self, fecha: date) -> bool:
        """Usado por el motor de facturacion (CU-O17) para elegir el
        tarifario aplicable a la fecha_operacion de cada vuelo -- no solo
        el que hoy tiene estado='vigente', sino el que efectivamente
        cubria esa fecha (permite recalcular periodos pasados con el
        tarifario historico correcto)."""
        if self.estado != "vigente":
            return False
        if fecha < self.vigente_desde:
            return False
        return self.vigente_hasta is None or fecha <= self.vigente_hasta
