"""Registro G1 (ADR-019) de las tablas que consulta aerohub_billing
(Sprint S1.6).

`ops.vuelo` ya la registra `aerohub_aodb.infrastructure.alcances` -- se
re-registra aqui de forma defensiva e idempotente (mismo patron que
`aerohub_ramp`/`aerohub_gates`).

`billing.concepto_cargo` es catalogo global (sin tenant_id), igual que
`catalogo.*`. `billing.tarifario_concepto` y `billing.factura_linea` NO
tienen columna `tenant_id` propia -- el guardian G2 no puede verificar un
predicado que no existe, asi que se declaran 'interno' (mismo tratamiento
que `tenants.plan_modulo`): el aislamiento de tenant se aplica de forma
transitiva en infrastructure/consultas.py, filtrando siempre por la fila
padre (`tarifario`/`factura`) que si tiene `tenant_id`.
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

registrar_alcance("ops", "vuelo", "tenant")
registrar_alcance("billing", "concepto_cargo", "global")
registrar_alcance("billing", "tarifario", "tenant")
registrar_alcance("billing", "tarifario_concepto", "interno")
registrar_alcance("billing", "cargo_aeronautico", "tenant")
registrar_alcance("billing", "factura", "tenant")
registrar_alcance("billing", "factura_linea", "interno")
registrar_alcance("billing", "conciliacion_pax", "tenant")
