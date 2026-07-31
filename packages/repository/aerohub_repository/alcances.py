"""Registro G1 (ADR-019) de las tablas existentes hasta S0.2.

Centralizado aqui mientras no exista codigo de repositorio propio por
modulo (Fase 1 en adelante, Plan §8). A partir de que `services/<modulo>/
infrastructure/` tenga su propio codigo de acceso a datos, cada modulo
deberia registrar el alcance de SUS tablas junto a ese codigo, no aqui --
este archivo queda entonces limitado a las tablas verdaderamente
transversales (catalogo, compliance, continuidad).

Import este modulo (via aerohub_repository/__init__.py) para que los
registros existan antes de que cualquier consulta se ejecute; sin esto, G1
rechaza toda tabla con AlcanceNoDeclarado.

Regla para decidir 'tenant' vs 'interno': no toda tabla del esquema
`tenants` es de alcance 'tenant' -- solo las que tienen columna `tenant_id`
y de verdad requieren aislamiento por fila (SDD-DATA-001 §6). `plan`,
`plan_modulo`, `tenant`, `rol`, `usuario_rol` y `okr*` son catalogos o
tablas de alcance interno de la plataforma, sin `tenant_id`: el guardian
G2 no tiene columna que verificar en ellas, y forzar 'tenant' ahi seria
un alcance mal declarado, no una proteccion real.
"""

from __future__ import annotations

from .guard import registrar_alcance

_CATALOGO = (
    "pais",
    "aeropuerto",
    "aerolinea",
    "modelo_aeronave",
    "aeronave",
    "tipo_vuelo",
    "motivo_demora",
    "estado_vuelo_catalogo",
    "departamento",
    "modulo",
)
for _tabla in _CATALOGO:
    registrar_alcance("catalogo", _tabla, "global")

_TENANTS_ALCANCE_TENANT = ("licencia", "usuario", "api_key")
for _tabla in _TENANTS_ALCANCE_TENANT:
    registrar_alcance("tenants", _tabla, "tenant")

_TENANTS_ALCANCE_INTERNO = (
    "plan",
    "plan_modulo",
    "tenant",
    "rol",
    "usuario_rol",
    "okr",
    "okr_resultado_clave",
)
for _tabla in _TENANTS_ALCANCE_INTERNO:
    registrar_alcance("tenants", _tabla, "interno")

# tenant_id es nullable en ambas (eventos de alcance de plataforma sin
# tenant asociado son legitimos, SDD-DATA-001 §10.1 / ADR-018 C1) -- el
# guardian no puede exigir un filtro que la propia tabla no siempre porta.
registrar_alcance("compliance", "log_auditoria", "interno")
registrar_alcance("continuidad", "journal_mutacion", "interno")
