"""Registro G1 (ADR-019) de las tablas que consulta aerohub_passenger
(Sprint S1.6). `ops.terminal`/`ops.puerta`/`ops.asignacion_puerta` ya las
registra `aerohub_gates`/`aerohub_fids`; `rampa.turnaround` ya la registra
`aerohub_ramp` -- se re-registran aqui de forma defensiva e idempotente
(mismo patron establecido desde S1.4).

`billing.tiempo_espera_agregado` es alcance='tenant' aunque viva en el
esquema SQL `billing` -- este modulo, no `aerohub_billing`, es quien la
declara y escribe (research.md Decision 3).
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

registrar_alcance("ops", "terminal", "tenant")
registrar_alcance("ops", "puerta", "tenant")
registrar_alcance("ops", "asignacion_puerta", "tenant")
registrar_alcance("rampa", "turnaround", "tenant")
registrar_alcance("billing", "tiempo_espera_agregado", "tenant")
