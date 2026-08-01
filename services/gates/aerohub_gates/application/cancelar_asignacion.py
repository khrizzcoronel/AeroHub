"""Cancelacion de una asignacion de puerta (Sprint S1.4). Libera la puerta
para nuevas asignaciones -- ver domain.puerta_ocupa_intervalo, que excluye
'cancelada' del chequeo de no solapamiento.
"""

from __future__ import annotations

from ..infrastructure import (
    cancelar_asignacion_puerta,
    contexto_tenant_id,
    escribir_journal,
    obtener_asignacion_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class AsignacionNoEncontrada(Exception):
    pass


@reintentar_en_conflicto()
def cancelar_asignacion(*, asignacion_id: int) -> None:
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        if obtener_asignacion_por_id(conn, asignacion_id) is None:
            raise AsignacionNoEncontrada(f"asignacion {asignacion_id} no encontrada")

        cancelar_asignacion_puerta(conn, id=asignacion_id, tenant_id=tenant_id)
        escribir_journal(
            conn,
            esquema="ops",
            tabla="asignacion_puerta",
            operacion="UPDATE",
            clave_primaria={"id": asignacion_id},
            payload={"id": asignacion_id, "estado": "cancelada"},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="asignacion_puerta",
            registro_id=asignacion_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "cancelada"},
        )
