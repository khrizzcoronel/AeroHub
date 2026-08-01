"""Asignacion de plantilla vigente a una pantalla (Sprint S1.3, Plan §8.3,
RF-T03, RNF-P02: "propagacion < 1 s").

Publica el evento de cambio DESPUES de que la transaccion confirmo (mismo
principio que aerohub_aodb.application.registrar_cambio_estado en S1.2):
un reproductor jamas debe recibir un cambio que termino revirtiendose.
"""

from __future__ import annotations

from aerohub_kernel import ahora_utc

from ..infrastructure import (
    EventoPlantillaPantalla,
    actualizar_plantilla_de_pantalla,
    broadcaster_global,
    contexto_tenant_id,
    escribir_journal,
    obtener_pantalla_por_id,
    obtener_plantilla_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class PantallaNoEncontrada(Exception):
    pass


class PlantillaNoEncontrada(Exception):
    pass


@reintentar_en_conflicto()
def asignar_plantilla(*, pantalla_id: int, plantilla_id: int) -> None:
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        # PN-01: pantalla/plantilla de otro tenant = "no existe".
        if obtener_pantalla_por_id(conn, pantalla_id) is None:
            raise PantallaNoEncontrada(f"pantalla {pantalla_id} no encontrada")
        fila_plantilla = obtener_plantilla_por_id(conn, plantilla_id)
        if fila_plantilla is None:
            raise PlantillaNoEncontrada(f"plantilla {plantilla_id} no encontrada")

        actualizar_plantilla_de_pantalla(
            conn, id=pantalla_id, tenant_id=tenant_id, plantilla_id=plantilla_id
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="pantalla_fids",
            operacion="UPDATE",
            clave_primaria={"id": pantalla_id},
            payload={"id": pantalla_id, "plantilla_id": plantilla_id},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="pantalla_fids",
            registro_id=pantalla_id,
            operacion="UPDATE",
            valores_nuevos={"plantilla_id": plantilla_id},
        )
        definicion_json = fila_plantilla.definicion_json

    broadcaster_global.publicar(
        EventoPlantillaPantalla(
            tenant_id=tenant_id,
            pantalla_id=pantalla_id,
            plantilla_id=plantilla_id,
            definicion_json=definicion_json,
            ocurrido_en=ahora_utc(),
        )
    )
