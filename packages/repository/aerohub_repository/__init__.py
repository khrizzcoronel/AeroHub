"""Unico paquete autorizado a emitir SQL hacia MonetDB (P1, ADR-014, PN-15).

Estado de este paquete en S0.1 (fundacion de monorepo): existe como miembro
del workspace, con el `ContextVar` de tenant y el registro de excepcion de
alcance, para que `infrastructure/` de cada modulo pueda depender de el desde
ya. La logica del guardian en ejecucion (ADR-019, componentes G1-G4) y el
journal transaccional de continuidad (ADR-018, componente C1) se implementan
en el Sprint S0.2 — no se adelantan aqui para no mezclar el alcance de dos
sprints con criterios de aceptacion distintos (Plan §7.1 vs §7.2).
"""

from .contexto import ContextoTenantAusente, alcance_global, contexto_tenant_id

__all__ = ["contexto_tenant_id", "alcance_global", "ContextoTenantAusente"]
