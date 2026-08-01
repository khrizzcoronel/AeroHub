"""Registro G1 (ADR-019) de las tablas de ops que consulta aerohub_gates
(Sprint S1.4).

`ops.terminal`, `ops.puerta` y `ops.vuelo` ya las registra
`aerohub_aodb.infrastructure.alcances` -- pero el registro G1 es un dict
global poblado en tiempo de IMPORT (packages/repository/guard.py), y el
contrato de independencia de modulos prohibe que gates importe el codigo
de aodb para "confiar" en que ya corrio. Se re-registran aqui, de forma
defensiva e idempotente (mismo alcance='tenant' que ya declara aodb): cada
modulo declara el alcance de TODA tabla que consulta directamente, sin
depender del orden de import de otros modulos en el proceso compuesto
(services/gateway/main.py).
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

_TABLAS_OPS = ("terminal", "puerta", "vuelo", "asignacion_puerta")
for _tabla in _TABLAS_OPS:
    registrar_alcance("ops", _tabla, "tenant")
