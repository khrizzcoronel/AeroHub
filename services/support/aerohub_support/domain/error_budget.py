"""Calculo puro de consumo de error budget (Sprint S1.8, CU-D6, RF-007,
RNF-R02; research.md Decision 1). Sin I/O -- el uptime observado se obtiene
en infrastructure/prometheus.py y se le pasa a esta funcion ya calculado.
"""

from __future__ import annotations

UMBRAL_BLOQUEO_DESPLIEGUE_PCT = 80.0


class ErrorBudgetInvalido(Exception):
    pass


def calcular_consumo_error_budget(*, uptime_observado_pct: float, objetivo_slo_pct: float) -> float:
    """Consumo de error budget, en porcentaje del presupuesto MENSUAL total
    (no del uptime). No se acota a 100 -- un servicio puede consumir mas del
    presupuesto asignado (spec.md, caso borde ">100%"); 100% exacto es el
    caso en que el uptime observado iguala al objetivo de SLO (spec.md,
    Acceptance Scenario US2.3).
    """
    if not (0.0 <= uptime_observado_pct <= 100.0):
        raise ErrorBudgetInvalido(f"uptime_observado_pct fuera de rango: {uptime_observado_pct!r}")
    if not (0.0 < objetivo_slo_pct < 100.0):
        raise ErrorBudgetInvalido(f"objetivo_slo_pct fuera de rango: {objetivo_slo_pct!r}")

    downtime_pct = 100.0 - uptime_observado_pct
    presupuesto_total_pct = 100.0 - objetivo_slo_pct
    return (downtime_pct / presupuesto_total_pct) * 100.0
