"""Unico paquete autorizado a emitir SQL hacia MonetDB (P1, ADR-014, PN-15).

Importar este paquete pobla el registro G1 (alcances.py, side-effect de
importacion) antes de que cualquier consulta pueda ejecutarse -- sin eso,
guard.verificar_sentencia rechaza toda tabla con AlcanceNoDeclarado.
"""

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1
from .audit import registrar_auditoria
from .base import obtener_engine, sesion
from .contexto import (
    ContextoTenantAusente,
    alcance_global,
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
)
from .guard import AlcanceNoDeclarado, TenantScopeViolation
from .journal import escribir_journal

__all__ = [
    "contexto_tenant_id",
    "contexto_rol_actor",
    "contexto_usuario_id",
    "alcance_global",
    "ContextoTenantAusente",
    "AlcanceNoDeclarado",
    "TenantScopeViolation",
    "obtener_engine",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
]
