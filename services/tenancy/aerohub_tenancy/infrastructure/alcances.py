"""Registro G1 (ADR-019) de las tablas de tenants -- movido desde
packages/repository/alcances.py en S1.1, siguiendo el patron que ese
modulo establecio para si mismo (ver su docstring) y que services/aodb ya
sigue desde S1.1.

No toda tabla de `tenants` es de alcance 'tenant': solo las que tienen
columna `tenant_id` y de verdad requieren aislamiento por fila
(SDD-DATA-001 §6). `plan`, `plan_modulo`, `tenant`, `rol`, `usuario_rol` y
`okr*` son catalogos o tablas de alcance interno de la plataforma, sin
`tenant_id` -- forzar 'tenant' ahi seria una declaracion incorrecta que el
guardian G2 no podria hacer cumplir (no tiene columna que verificar).
"""

from __future__ import annotations

from aerohub_repository.guard import registrar_alcance

_ALCANCE_TENANT = ("licencia", "usuario", "api_key", "invitacion")
for _tabla in _ALCANCE_TENANT:
    registrar_alcance("tenants", _tabla, "tenant")

# sesion/token_acceso/intento_acceso son 'interno' (Sprint S1.10,
# research.md Decision 9): se consultan ANTES de saber a que tenant
# pertenece quien hace la peticion (login, canje de token, registro de un
# intento fallido de un correo que quiza ni existe) -- declararlas
# 'tenant' obligaria a envolver cada peticion autenticada del sistema en
# alcance_global(), y un usuario de plataforma (tenant_id NULL) ni podria
# filtrar por tenant_id. `invitacion` si es 'tenant': siempre la crea un
# admin ya autenticado dentro de su propio tenant.
_ALCANCE_INTERNO = (
    "plan",
    "plan_modulo",
    "tenant",
    "rol",
    "usuario_rol",
    "okr",
    "okr_resultado_clave",
    "sesion",
    "token_acceso",
    "intento_acceso",
)
for _tabla in _ALCANCE_INTERNO:
    registrar_alcance("tenants", _tabla, "interno")
