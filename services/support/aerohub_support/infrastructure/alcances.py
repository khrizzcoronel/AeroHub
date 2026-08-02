"""Registro G1 (ADR-019) de las tablas propias de aerohub_support (Sprint
S1.8). `ticket_mensaje` no tiene `tenant_id` propio -- alcance 'interno',
aislada transitivamente via `ticket_id` -> `ticket.tenant_id` (mismo patron
que `post_mortem_accion` en S1.7, data-model.md Decision 4).

`catalogo.modulo` ya la registra `aerohub_gateway.infrastructure.alcances`
-- se re-registra aqui de forma defensiva e idempotente (mismo motivo que
`aerohub_ramp.infrastructure.alcances` con `ops.vuelo`): el registro G1 es un
dict global poblado en tiempo de IMPORT, y el contrato de independencia de
modulos prohibe que support importe el codigo de gateway para "confiar" en
que ya corrio.
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

registrar_alcance("support", "categoria_ticket", "global")
registrar_alcance("support", "ticket", "tenant")
registrar_alcance("support", "ticket_mensaje", "interno")
registrar_alcance("support", "articulo_kb", "global")
registrar_alcance("support", "etiqueta", "global")
registrar_alcance("support", "articulo_kb_etiqueta", "global")
registrar_alcance("support", "changelog", "global")
registrar_alcance("support", "changelog_item", "global")
registrar_alcance("catalogo", "modulo", "global")
