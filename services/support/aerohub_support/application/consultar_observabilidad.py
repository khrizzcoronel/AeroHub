"""Uptime y consumo de error budget de servicios criticos (Sprint S1.8,
CU-D6, US2; RF-006, RF-007). Orquesta infrastructure.prometheus (I/O) +
domain.error_budget (calculo puro) -- sin persistencia propia (research.md
Decision 1). Reutilizado por `tools/verificar_error_budget.py` (US3).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import calcular_consumo_error_budget
from ..infrastructure import ServicioInvalido, consultar_uptime_mensual

__all__ = [
    "OBJETIVO_SLO_PCT",
    "ResultadoObservabilidad",
    "obtener_uptime_y_error_budget",
    "ServicioInvalido",
]

# FR-007: 99.9% MVP / 99.95% Scale -- este sprint implementa el objetivo MVP.
OBJETIVO_SLO_PCT = 99.9


@dataclass(frozen=True, slots=True)
class ResultadoObservabilidad:
    servicio: str
    uptime_pct: float
    error_budget_consumido_pct: float


def obtener_uptime_y_error_budget(servicio: str) -> ResultadoObservabilidad:
    uptime_pct = consultar_uptime_mensual(servicio)
    consumo_pct = calcular_consumo_error_budget(
        uptime_observado_pct=uptime_pct, objetivo_slo_pct=OBJETIVO_SLO_PCT
    )
    return ResultadoObservabilidad(
        servicio=servicio, uptime_pct=uptime_pct, error_budget_consumido_pct=consumo_pct
    )
