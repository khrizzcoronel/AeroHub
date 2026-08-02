"""Escritura de compliance.* (Sprint S1.7). Solo INSERT para las tablas
append-only (`tipo_incidente`, `incidente_seguridad`,
`tipo_reporte_regulatorio`, `reporte_dgac`, `acceso_auditor`,
`control_soc2`, `evidencia_soc2`) -- PN-04 reforzada: ninguna funcion de
UPDATE/DELETE existe para ellas en este archivo, verificado por analisis
estatico (tests/negative/test_pn04_compliance_append_only.py).
`post_mortem`/`post_mortem_accion` son la UNICA excepcion (ADR-009):
tienen tambien `actualizar_*`.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import (
    acceso_auditor,
    control_soc2,
    evidencia_soc2,
    incidente_seguridad,
    post_mortem,
    post_mortem_accion,
    reporte_dgac,
    tipo_incidente,
    tipo_reporte_regulatorio,
)


def insertar_tipo_incidente(
    conn: Connection, *, id: int, codigo: str, descripcion: str, categoria: str
) -> None:
    conn.execute(
        insert(tipo_incidente).values(
            id=id, codigo=codigo, descripcion=descripcion, categoria=categoria
        )
    )


def insertar_incidente_seguridad(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    tipo_incidente_id: int,
    descripcion: str,
    severidad: str,
    detectado_en: datetime,
    reportado_por_usuario_id: int,
    estado: str,
) -> None:
    conn.execute(
        insert(incidente_seguridad).values(
            id=id,
            tenant_id=tenant_id,
            tipo_incidente_id=tipo_incidente_id,
            descripcion=descripcion,
            severidad=severidad,
            detectado_en=detectado_en,
            reportado_por_usuario_id=reportado_por_usuario_id,
            estado=estado,
        )
    )


def insertar_tipo_reporte_regulatorio(
    conn: Connection, *, id: int, codigo: str, nombre: str, periodicidad: str, autoridad: str
) -> None:
    conn.execute(
        insert(tipo_reporte_regulatorio).values(
            id=id, codigo=codigo, nombre=nombre, periodicidad=periodicidad, autoridad=autoridad
        )
    )


def insertar_reporte_dgac(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    tipo_reporte_id: int,
    periodo_inicio: date,
    periodo_fin: date,
    contenido_ref: str,
    hash_contenido: str,
    emitido_por_usuario_id: int,
) -> None:
    conn.execute(
        insert(reporte_dgac).values(
            id=id,
            tenant_id=tenant_id,
            tipo_reporte_id=tipo_reporte_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            contenido_ref=contenido_ref,
            hash_contenido=hash_contenido,
            emitido_por_usuario_id=emitido_por_usuario_id,
        )
    )


def insertar_acceso_auditor(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    auditor_usuario_id: int,
    otorgado_por_usuario_id: int,
    inicio: datetime,
    fin: datetime,
    alcance_json: dict,
    motivo: str,
) -> None:
    conn.execute(
        insert(acceso_auditor).values(
            id=id,
            tenant_id=tenant_id,
            auditor_usuario_id=auditor_usuario_id,
            otorgado_por_usuario_id=otorgado_por_usuario_id,
            inicio=inicio,
            fin=fin,
            alcance_json=alcance_json,
            motivo=motivo,
        )
    )


def insertar_control_soc2(
    conn: Connection, *, id: int, codigo_control: str, nombre: str, categoria: str
) -> None:
    conn.execute(
        insert(control_soc2).values(
            id=id, codigo_control=codigo_control, nombre=nombre, categoria=categoria
        )
    )


def insertar_evidencia_soc2(
    conn: Connection,
    *,
    id: int,
    control_soc2_id: int,
    tenant_id: int | None,
    periodo_inicio: date,
    periodo_fin: date,
    ruta_artefacto: str,
    hash_artefacto: str,
    referencia_log_id: int | None,
) -> None:
    conn.execute(
        insert(evidencia_soc2).values(
            id=id,
            control_soc2_id=control_soc2_id,
            tenant_id=tenant_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            ruta_artefacto=ruta_artefacto,
            hash_artefacto=hash_artefacto,
            referencia_log_id=referencia_log_id,
        )
    )


def insertar_post_mortem(
    conn: Connection,
    *,
    id: int,
    tenant_id: int | None,
    incidente_ref: str,
    severidad: str,
    iniciado_en: datetime,
) -> None:
    conn.execute(
        insert(post_mortem).values(
            id=id,
            tenant_id=tenant_id,
            incidente_ref=incidente_ref,
            severidad=severidad,
            estado="en_progreso",
            iniciado_en=iniciado_en,
        )
    )


def actualizar_causa_raiz_post_mortem(
    conn: Connection, *, id: int, tenant_id: int, causa_raiz: str
) -> None:
    conn.execute(
        update(post_mortem)
        .where(post_mortem.c.id == id, post_mortem.c.tenant_id == tenant_id)
        .values(causa_raiz=causa_raiz)
    )


def publicar_post_mortem(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    publicado_en: datetime,
    tiempo_resolucion_min: int,
) -> None:
    conn.execute(
        update(post_mortem)
        .where(post_mortem.c.id == id, post_mortem.c.tenant_id == tenant_id)
        .values(
            estado="publicado",
            publicado_en=publicado_en,
            tiempo_resolucion_min=tiempo_resolucion_min,
        )
    )


def insertar_post_mortem_accion(
    conn: Connection,
    *,
    id: int,
    post_mortem_id: int,
    descripcion: str,
    responsable_usuario_id: int,
    vence_en: datetime,
    ticket_ref: str | None,
) -> None:
    conn.execute(
        insert(post_mortem_accion).values(
            id=id,
            post_mortem_id=post_mortem_id,
            descripcion=descripcion,
            responsable_usuario_id=responsable_usuario_id,
            estado="pendiente",
            vence_en=vence_en,
            ticket_ref=ticket_ref,
        )
    )


def completar_post_mortem_accion(conn: Connection, *, id: int, completada_en: datetime) -> None:
    conn.execute(
        update(post_mortem_accion)
        .where(post_mortem_accion.c.id == id)
        .values(estado="completada", completada_en=completada_en)
    )
