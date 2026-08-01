"""Invariantes de turnaround (Sprint S1.5, Plan §8.5, RF-O16; SDD-DATA-001
§8.3).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 §5.4, regla
1). Un turnaround empareja DOS vuelos (llegada y salida) de la MISMA
aeronave -- que ambos pertenezcan al mismo tenant y aeronave, y que
`vuelo_llegada` tenga sentido='L'/`vuelo_salida` sentido='S', se verifica
en infrastructure/ (requiere leer ops.vuelo, dato que domain/ no conoce).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import es_utc

ESTADOS_TURNAROUND = ("planificado", "en_curso", "completado", "interrumpido")


class TurnaroundInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Turnaround:
    id: int
    tenant_id: int
    vuelo_llegada_id: int
    vuelo_salida_id: int
    aeronave_id: int
    inicio_previsto: datetime
    fin_previsto: datetime
    estado: str
    inicio_real: datetime | None = None
    fin_real: datetime | None = None

    def __post_init__(self) -> None:
        if self.vuelo_llegada_id == self.vuelo_salida_id:
            raise TurnaroundInvalido(
                "vuelo_llegada_id y vuelo_salida_id no pueden ser el mismo vuelo"
            )
        if self.estado not in ESTADOS_TURNAROUND:
            raise TurnaroundInvalido(f"estado invalido: {self.estado!r}")
        if not es_utc(self.inicio_previsto) or not es_utc(self.fin_previsto):
            raise TurnaroundInvalido(
                "inicio_previsto y fin_previsto deben ser datetime en UTC (tz-aware)"
            )
        if self.fin_previsto <= self.inicio_previsto:
            raise TurnaroundInvalido(
                f"fin_previsto ({self.fin_previsto}) debe ser posterior a "
                f"inicio_previsto ({self.inicio_previsto})"
            )
        if (
            self.inicio_real is not None
            and self.fin_real is not None
            and self.fin_real < self.inicio_real
        ):
            raise TurnaroundInvalido(
                f"fin_real ({self.fin_real}) no puede ser anterior a "
                f"inicio_real ({self.inicio_real})"
            )
