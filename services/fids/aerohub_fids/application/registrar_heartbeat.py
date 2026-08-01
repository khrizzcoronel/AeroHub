"""Heartbeat de pantalla FIDS (Sprint S1.3, Plan §8.3, RF-O07, RNF-R04).

Cada heartbeat resetea `ultima_senal_en` y devuelve el estado a 'en_linea'
-- el monitor de senal (services/fids, tarea de fondo) es quien la mueve a
'sin_senal' cuando el heartbeat deja de llegar, nunca al reves.

Sin journal/auditoria (P8): un heartbeat es telemetria operacional de alta
frecuencia, no una mutacion de negocio -- auditar cada ping duplicaria el
volumen de compliance.log_auditoria sin aportar valor de cumplimiento.
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc

from ..infrastructure import (
    contexto_tenant_id,
    obtener_pantalla_por_id,
    registrar_heartbeat,
    sesion,
)


class PantallaNoEncontrada(Exception):
    pass


def registrar_heartbeat_pantalla(*, pantalla_id: int, version_firmware: str | None = None) -> None:
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        if obtener_pantalla_por_id(conn, pantalla_id) is None:
            raise PantallaNoEncontrada(f"pantalla {pantalla_id} no encontrada")
        registrar_heartbeat(
            conn,
            id=pantalla_id,
            tenant_id=tenant_id,
            ultima_senal_en=ahora_utc(),
            version_firmware=version_firmware,
        )
