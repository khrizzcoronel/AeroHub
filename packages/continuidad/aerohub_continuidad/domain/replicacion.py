"""Decision pura de que rango del journal drenar (Sprint S1.9, ADR-018 C3).

La idempotencia REAL de la escritura sobre el standby la garantiza el
UPSERT generico de `operaciones/shipper.py` (research.md Decision 9 de
specs/011-continuidad-rto-rpo/) -- esta funcion solo decide que entradas
vale la pena procesar en un ciclo, evitando releer trabajo ya confirmado.
"""

from __future__ import annotations


def debe_procesar(lsn: int, ultimo_lsn_aplicado: int) -> bool:
    return lsn > ultimo_lsn_aplicado
