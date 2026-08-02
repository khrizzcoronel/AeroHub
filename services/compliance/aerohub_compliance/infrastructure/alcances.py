"""Registro G1 (ADR-019) de las tablas propias de aerohub_compliance
(Sprint S1.7). `compliance.log_auditoria` ya la registra
`aerohub_repository.alcances` (alcance 'interno') -- no se re-registra
aqui, no es propiedad de este modulo.

`post_mortem_accion` no tiene `tenant_id` propio -- alcance 'interno',
aislada transitivamente vía `post_mortem_id` (mismo patron que
`tarifario_concepto` en S1.6). `post_mortem`/`evidencia_soc2` tienen
`tenant_id` NULLABLE -- alcance 'tenant' de todos modos: cuando es NULL,
la fila corresponde a un caso de plataforma y se escribe bajo
`alcance_global()` (ADR-019 G3), nunca con un `tenant_id` inventado.
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

registrar_alcance("compliance", "tipo_incidente", "global")
registrar_alcance("compliance", "incidente_seguridad", "tenant")
registrar_alcance("compliance", "tipo_reporte_regulatorio", "global")
registrar_alcance("compliance", "reporte_dgac", "tenant")
registrar_alcance("compliance", "acceso_auditor", "tenant")
registrar_alcance("compliance", "post_mortem", "tenant")
registrar_alcance("compliance", "post_mortem_accion", "interno")
registrar_alcance("compliance", "control_soc2", "global")
registrar_alcance("compliance", "evidencia_soc2", "tenant")
