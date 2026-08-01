"""Registro G1 (ADR-019) de las tablas que consulta aerohub_ramp (Sprint
S1.5).

`ops.vuelo` ya la registra `aerohub_aodb.infrastructure.alcances` -- se
re-registra aqui de forma defensiva e idempotente (mismo motivo que
`aerohub_gates.infrastructure.alcances`, S1.4): el registro G1 es un dict
global poblado en tiempo de IMPORT, y el contrato de independencia de
modulos prohibe que ramp importe el codigo de aodb para "confiar" en que
ya corrio.

`rampa.tipo_tarea`/`rampa.tipo_incidencia_rampa` son catalogos SIN
tenant_id (alcance 'global', igual que catalogo.*) -- el resto de `rampa`
es alcance 'tenant'.
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

registrar_alcance("ops", "vuelo", "tenant")
registrar_alcance("rampa", "tipo_tarea", "global")
registrar_alcance("rampa", "tipo_incidencia_rampa", "global")
registrar_alcance("rampa", "turnaround", "tenant")
registrar_alcance("rampa", "tarea_turnaround", "tenant")
registrar_alcance("rampa", "incidencia_rampa", "tenant")
