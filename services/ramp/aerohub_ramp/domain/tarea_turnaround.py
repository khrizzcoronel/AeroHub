"""Tarea de turnaround: duracion DERIVADA de fin_real - inicio_real, nunca
almacenada (3NF, SDD-DATA-001 §8.4), y deteccion de desviacion del
estandar de su tipo de tarea (RF-O16, CU-O16).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 §5.4, regla
1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import es_utc

ESTADOS_TAREA_TURNAROUND = ("pendiente", "en_curso", "completada", "omitida")


class TareaTurnaroundInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TareaTurnaround:
    id: int
    tenant_id: int
    turnaround_id: int
    tipo_tarea_id: int
    agente_usuario_id: int
    estado: str
    inicio_real: datetime | None = None
    fin_real: datetime | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_TAREA_TURNAROUND:
            raise TareaTurnaroundInvalida(f"estado invalido: {self.estado!r}")
        if self.inicio_real is not None and not es_utc(self.inicio_real):
            raise TareaTurnaroundInvalida("inicio_real debe ser datetime en UTC (tz-aware)")
        if self.fin_real is not None and not es_utc(self.fin_real):
            raise TareaTurnaroundInvalida("fin_real debe ser datetime en UTC (tz-aware)")
        if (
            self.inicio_real is not None
            and self.fin_real is not None
            and self.fin_real < self.inicio_real
        ):
            raise TareaTurnaroundInvalida(
                f"fin_real ({self.fin_real}) no puede ser anterior a "
                f"inicio_real ({self.inicio_real})"
            )

    def duracion_minutos(self) -> float | None:
        """Derivada al vuelo -- NUNCA se persiste una columna de duracion
        (SDD-DATA-001 §8.4). None si la tarea todavia no tiene ambos
        extremos (no iniciada, o iniciada pero no finalizada)."""
        if self.inicio_real is None or self.fin_real is None:
            return None
        return (self.fin_real - self.inicio_real).total_seconds() / 60


def excede_estandar(*, duracion_minutos: float, duracion_estandar_min: int) -> bool:
    """RF-O16: "superar el estandar" -- sin margen de tolerancia adicional,
    ninguna fuente (SRS, SDD, analisis estrategico) documenta uno."""
    return duracion_minutos > duracion_estandar_min
