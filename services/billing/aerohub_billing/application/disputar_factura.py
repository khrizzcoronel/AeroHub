"""Emision y disputa de facturas (Sprint S1.6, CU-O17, FR-007).
role_billing_officer revisa y puede disputar -- NUNCA altera el calculo
original de un cargo (research.md Decision 5): disputar solo cambia
`factura.estado`, ningun `monto_calculado` de los cargos referenciados.
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc

from ..domain import validar_transicion
from ..infrastructure import (
    actualizar_estado_factura,
    contexto_tenant_id,
    escribir_journal,
    obtener_factura_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class FacturaNoEncontrada(Exception):
    pass


@reintentar_en_conflicto()
def emitir_factura(*, factura_id: int) -> None:
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        fila = obtener_factura_por_id(conn, factura_id)
        if fila is None:
            raise FacturaNoEncontrada(f"factura {factura_id} no encontrada")
        if fila.estado == "emitida":
            return  # idempotente -- ya emitida, sin cambios
        validar_transicion(estado_actual=fila.estado, estado_nuevo="emitida")

        ahora = ahora_utc()
        actualizar_estado_factura(
            conn, id=factura_id, tenant_id=tenant_id, estado_nuevo="emitida", emitida_en=ahora
        )
        escribir_journal(
            conn,
            esquema="billing",
            tabla="factura",
            operacion="UPDATE",
            clave_primaria={"id": factura_id},
            payload={"id": factura_id, "estado": "emitida"},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="factura",
            registro_id=factura_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "emitida"},
        )


@reintentar_en_conflicto()
def disputar_factura(*, factura_id: int, motivo: str) -> None:
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        fila = obtener_factura_por_id(conn, factura_id)
        if fila is None:
            raise FacturaNoEncontrada(f"factura {factura_id} no encontrada")
        validar_transicion(estado_actual=fila.estado, estado_nuevo="disputada")

        actualizar_estado_factura(
            conn, id=factura_id, tenant_id=tenant_id, estado_nuevo="disputada"
        )
        escribir_journal(
            conn,
            esquema="billing",
            tabla="factura",
            operacion="UPDATE",
            clave_primaria={"id": factura_id},
            payload={"id": factura_id, "estado": "disputada"},
        )
        registrar_auditoria(
            conn,
            esquema="billing",
            tabla="factura",
            registro_id=factura_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "disputada", "motivo": motivo},
        )
