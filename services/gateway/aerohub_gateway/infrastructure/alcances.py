"""Registro G1 (ADR-019) de las tablas que consulta aerohub_gateway
(Sprint S1.7, verificacion de licencia).

`tenants.licencia` ya la registra `aerohub_tenancy.infrastructure.alcances`
(alcance 'tenant') y `catalogo.modulo` ya la registra
`aerohub_repository.alcances` (alcance 'global') -- ambas se re-registran
aqui de forma defensiva e idempotente, mismo patron que `ops.vuelo` en
aerohub_gates/aerohub_ramp (S1.4/S1.5): aerohub_gateway no puede importar
aerohub_tenancy (independencia de modulos), asi que no puede "confiar" en
que su registro ya corrio antes de servir una peticion.
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

registrar_alcance("tenants", "licencia", "tenant")
registrar_alcance("catalogo", "modulo", "global")
