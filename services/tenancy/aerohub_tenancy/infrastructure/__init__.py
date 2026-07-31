from aerohub_repository import escribir_journal, registrar_auditoria, sesion
from aerohub_repository.contexto import alcance_global, contexto_tenant_id, contexto_usuario_id

from . import alcances as _alcances  # noqa: F401 -- side effect: registra G1 de tenants.*
from .consultas import obtener_usuario_por_id
from .provisionamiento import insertar_tenant, insertar_usuario_admin

# Regla 4 de ADR-017 (.importlinter "solo-infrastructure-toca-repository"):
# solo infrastructure/ importa aerohub_repository. application/ obtiene
# sesion/journal/auditoria/contexto reexportados desde aqui, nunca del
# paquete transversal directamente.
__all__ = [
    "obtener_usuario_por_id",
    "insertar_tenant",
    "insertar_usuario_admin",
    "sesion",
    "escribir_journal",
    "registrar_auditoria",
    "alcance_global",
    "contexto_tenant_id",
    "contexto_usuario_id",
]
