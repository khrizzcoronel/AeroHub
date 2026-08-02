"""Conciliacion de pasajeros -- diferencia SIEMPRE derivada, nunca
almacenada (Sprint S1.6, CU-O17 paso de revision; SDD-DATA-001 Sec9.7).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 Sec5.4,
regla 1).
"""

from __future__ import annotations


def diferencia(*, pax_reportado_aerolinea: int, pax_registrado_sistema: int) -> int:
    return pax_reportado_aerolinea - pax_registrado_sistema


def puede_conciliar(*, pax_reportado_aerolinea: int, pax_registrado_sistema: int) -> bool:
    """Compuerta de pruebas del sprint: solo se puede marcar 'conciliado'
    si la diferencia es cero -- no existe forma de forzar una conciliacion
    con diferencia distinta de cero (spec.md, Acceptance Scenario US3.1)."""
    return diferencia(
        pax_reportado_aerolinea=pax_reportado_aerolinea,
        pax_registrado_sistema=pax_registrado_sistema,
    ) == 0
