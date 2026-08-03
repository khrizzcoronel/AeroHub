"""Workpanel de tenants (post S1.13): listar, ver detalle, editar y dar
de baja -- CU-O18 (S1.1) solo cubria crear. `domain.validar_transicion_estado`
ya existia desde S1.1 sin ningun llamador real; este modulo es su primer
consumidor.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..domain import TenantInvalido, TransicionTenantInvalida, validar_transicion_estado
from ..infrastructure import actualizar_tenant as _actualizar_tenant
from ..infrastructure import cambiar_estado_tenant as _cambiar_estado_tenant
from ..infrastructure import (
    escribir_journal,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from ..infrastructure import listar_tenants as _listar_tenants
from ..infrastructure import obtener_tenant_por_id as _obtener_tenant_por_id


class TenantNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class TenantResumen:
    id: int
    codigo: str
    razon_social: str
    aeropuerto_id: int
    plan_id: int
    estado: str
    es_sandbox: bool


def _fila_a_resumen(f: object) -> TenantResumen:
    return TenantResumen(
        id=f.id,  # type: ignore[attr-defined]
        codigo=f.codigo,  # type: ignore[attr-defined]
        razon_social=f.razon_social,  # type: ignore[attr-defined]
        aeropuerto_id=f.aeropuerto_id,  # type: ignore[attr-defined]
        plan_id=f.plan_id,  # type: ignore[attr-defined]
        estado=f.estado,  # type: ignore[attr-defined]
        es_sandbox=f.es_sandbox,  # type: ignore[attr-defined]
    )


def listar_tenants() -> list[TenantResumen]:
    with sesion() as conn:
        filas = _listar_tenants(conn)
    return [_fila_a_resumen(f) for f in filas]


def obtener_tenant(tenant_id: int) -> TenantResumen:
    with sesion() as conn:
        fila = _obtener_tenant_por_id(conn, tenant_id)
    if fila is None:
        raise TenantNoEncontrado(f"tenant {tenant_id} no encontrado")
    return _fila_a_resumen(fila)


@reintentar_en_conflicto()
def actualizar_tenant(
    *, tenant_id: int, razon_social: str, plan_id: int, es_sandbox: bool
) -> TenantResumen:
    """Domain valida primero (fail fast), luego persiste + journal +
    auditoria en la misma transaccion (P8)."""
    if not razon_social.strip():
        raise TenantInvalido("razon_social no puede ser vacio")

    with sesion() as conn:
        fila_actual = _obtener_tenant_por_id(conn, tenant_id)
        if fila_actual is None:
            raise TenantNoEncontrado(f"tenant {tenant_id} no encontrado")

        _actualizar_tenant(
            conn, id=tenant_id, razon_social=razon_social, plan_id=plan_id, es_sandbox=es_sandbox
        )
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="tenant",
            operacion="UPDATE",
            clave_primaria={"id": tenant_id},
            payload={"razon_social": razon_social, "plan_id": plan_id},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="tenant",
            registro_id=tenant_id,
            operacion="UPDATE",
            valores_anteriores={
                "razon_social": fila_actual.razon_social,
                "plan_id": fila_actual.plan_id,
            },
            valores_nuevos={"razon_social": razon_social, "plan_id": plan_id},
            tenant_id=tenant_id,
        )

    return obtener_tenant(tenant_id)


@reintentar_en_conflicto()
def cambiar_estado_tenant(*, tenant_id: int, estado_nuevo: str) -> TenantResumen:
    """Valida la transicion contra la maquina de estados de domain/tenant.py
    (existente desde S1.1, sin llamador real hasta ahora) antes de tocar
    la base -- fail fast.
    """
    with sesion() as conn:
        fila_actual = _obtener_tenant_por_id(conn, tenant_id)
        if fila_actual is None:
            raise TenantNoEncontrado(f"tenant {tenant_id} no encontrado")

        try:
            validar_transicion_estado(fila_actual.estado, estado_nuevo)
        except TransicionTenantInvalida:
            raise

        _cambiar_estado_tenant(conn, id=tenant_id, estado_nuevo=estado_nuevo)
        escribir_journal(
            conn,
            esquema="tenants",
            tabla="tenant",
            operacion="UPDATE",
            clave_primaria={"id": tenant_id},
            payload={"estado": estado_nuevo},
            tenant_id=tenant_id,
        )
        registrar_auditoria(
            conn,
            esquema="tenants",
            tabla="tenant",
            registro_id=tenant_id,
            operacion="UPDATE",
            valores_anteriores={"estado": fila_actual.estado},
            valores_nuevos={"estado": estado_nuevo},
            tenant_id=tenant_id,
        )

    return obtener_tenant(tenant_id)
