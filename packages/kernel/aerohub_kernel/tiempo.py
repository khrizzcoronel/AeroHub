"""Utilidades de tiempo. SDD-DATA-001 §4: TIMESTAMPTZ, siempre UTC en almacenamiento;
la conversion a huso local ocurre solo en la capa de presentacion.
"""

from __future__ import annotations

from datetime import UTC, datetime


def ahora_utc() -> datetime:
    return datetime.now(UTC)


def es_utc(momento: datetime) -> bool:
    desplazamiento = momento.utcoffset()
    return desplazamiento is not None and desplazamiento.total_seconds() == 0
