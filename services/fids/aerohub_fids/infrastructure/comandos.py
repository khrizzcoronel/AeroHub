"""Escritura de ops.plantilla_fids y ops.pantalla_fids (Sprint S1.3).

Solo persiste -- domain/ ya valido, application/ ya genero el id y decide
journal/auditoria.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import pantalla_fids, plantilla_fids


def insertar_plantilla(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    nombre: str,
    definicion_json: dict,
    version: int,
    vigente_desde: datetime,
    creada_por_usuario_id: int,
) -> None:
    conn.execute(
        insert(plantilla_fids).values(
            id=id,
            tenant_id=tenant_id,
            nombre=nombre,
            definicion_json=definicion_json,
            version=version,
            vigente_desde=vigente_desde,
            creada_por_usuario_id=creada_por_usuario_id,
        )
    )


def insertar_pantalla(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    terminal_id: int,
    codigo: str,
    plantilla_id: int,
    ubicacion_descripcion: str | None = None,
    version_firmware: str | None = None,
) -> None:
    conn.execute(
        insert(pantalla_fids).values(
            id=id,
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            codigo=codigo,
            plantilla_id=plantilla_id,
            ubicacion_descripcion=ubicacion_descripcion,
            version_firmware=version_firmware,
            ultima_senal_en=None,
            # 'sin_senal' hasta el primer heartbeat -- optimista ('en_linea'
            # de entrada) seria incorrecto: la pantalla fisica todavia no
            # ha confirmado nada.
            estado="sin_senal",
        )
    )


def actualizar_plantilla_de_pantalla(
    conn: Connection, *, id: int, tenant_id: int, plantilla_id: int
) -> None:
    conn.execute(
        update(pantalla_fids)
        .where(pantalla_fids.c.id == id, pantalla_fids.c.tenant_id == tenant_id)
        .values(plantilla_id=plantilla_id)
    )


def registrar_heartbeat(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    ultima_senal_en: datetime,
    version_firmware: str | None = None,
) -> None:
    valores = {"ultima_senal_en": ultima_senal_en, "estado": "en_linea"}
    if version_firmware is not None:
        valores["version_firmware"] = version_firmware
    conn.execute(
        update(pantalla_fids)
        .where(pantalla_fids.c.id == id, pantalla_fids.c.tenant_id == tenant_id)
        .values(**valores)
    )


def marcar_pantalla_sin_senal(conn: Connection, *, id: int) -> None:
    """SIN filtro de tenant_id -- uso exclusivo del monitor de senal
    (RNF-R04) bajo `alcance_global()`, que ya identifico la fila via
    `listar_pantallas_para_monitoreo` sin conocer/necesitar un tenant
    ambiente. No sobrescribe 'mantenimiento' (una pantalla apagada a
    proposito no es una alerta).
    """
    conn.execute(
        update(pantalla_fids)
        .where(pantalla_fids.c.id == id, pantalla_fids.c.estado != "mantenimiento")
        .values(estado="sin_senal")
    )
