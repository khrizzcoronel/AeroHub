"""Consultas de tablero: post-mortem con acciones, listado de incidentes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from ..infrastructure import (
    listar_acciones_de_post_mortem,
    listar_accesos_auditor,
    listar_evidencia_soc2,
    listar_incidentes,
    listar_post_mortems,
    listar_reportes_dgac,
    obtener_post_mortem_por_id,
    sesion,
)


class PostMortemNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PostMortemTablero:
    id: int
    incidente_ref: str
    severidad: str
    estado: str
    iniciado_en: datetime
    causa_raiz: str | None
    publicado_en: datetime | None
    tiempo_resolucion_min: int | None


@dataclass(frozen=True, slots=True)
class AccionTablero:
    id: int
    descripcion: str
    responsable_usuario_id: int
    estado: str
    vence_en: datetime
    ticket_ref: str | None
    completada_en: datetime | None


@dataclass(frozen=True, slots=True)
class IncidenteTablero:
    id: int
    tipo_incidente_id: int
    descripcion: str
    severidad: str
    detectado_en: datetime
    estado: str


def consultar_post_mortem(*, post_mortem_id: int) -> tuple[PostMortemTablero, list[AccionTablero]]:
    with sesion() as conn:
        f = obtener_post_mortem_por_id(conn, post_mortem_id)
        if f is None:
            raise PostMortemNoEncontrado(f"post-mortem {post_mortem_id} no encontrado")
        cabecera = PostMortemTablero(
            id=f.id,
            incidente_ref=f.incidente_ref,
            severidad=f.severidad,
            estado=f.estado,
            iniciado_en=f.iniciado_en,
            causa_raiz=f.causa_raiz,
            publicado_en=f.publicado_en,
            tiempo_resolucion_min=f.tiempo_resolucion_min,
        )
        acciones = [
            AccionTablero(
                id=a.id,
                descripcion=a.descripcion,
                responsable_usuario_id=a.responsable_usuario_id,
                estado=a.estado,
                vence_en=a.vence_en,
                ticket_ref=a.ticket_ref,
                completada_en=a.completada_en,
            )
            for a in listar_acciones_de_post_mortem(conn, post_mortem_id=post_mortem_id)
        ]
    return cabecera, acciones


def consultar_incidentes() -> list[IncidenteTablero]:
    with sesion() as conn:
        filas = listar_incidentes(conn)
    return [
        IncidenteTablero(
            id=f.id,
            tipo_incidente_id=f.tipo_incidente_id,
            descripcion=f.descripcion,
            severidad=f.severidad,
            detectado_en=f.detectado_en,
            estado=f.estado,
        )
        for f in filas
    ]


@dataclass(frozen=True, slots=True)
class PostMortemResumen:
    id: int
    incidente_ref: str
    severidad: str
    estado: str
    iniciado_en: datetime
    publicado_en: datetime | None


def consultar_post_mortems() -> list[PostMortemResumen]:
    """Sprint S1.19 -- listado que faltaba desde S1.7 (spec.md FR-007)."""
    with sesion() as conn:
        filas = listar_post_mortems(conn)
    return [
        PostMortemResumen(
            id=f.id,
            incidente_ref=f.incidente_ref,
            severidad=f.severidad,
            estado=f.estado,
            iniciado_en=f.iniciado_en,
            publicado_en=f.publicado_en,
        )
        for f in filas
    ]


@dataclass(frozen=True, slots=True)
class ReporteDgacResumen:
    id: int
    tipo_reporte_id: int
    periodo_inicio: date
    periodo_fin: date
    contenido_ref: str
    hash_contenido: str
    emitido_en: datetime


def consultar_reportes_dgac() -> list[ReporteDgacResumen]:
    with sesion() as conn:
        filas = listar_reportes_dgac(conn)
    return [
        ReporteDgacResumen(
            id=f.id,
            tipo_reporte_id=f.tipo_reporte_id,
            periodo_inicio=f.periodo_inicio,
            periodo_fin=f.periodo_fin,
            contenido_ref=f.contenido_ref,
            hash_contenido=f.hash_contenido,
            emitido_en=f.emitido_en,
        )
        for f in filas
    ]


@dataclass(frozen=True, slots=True)
class AccesoAuditorResumen:
    id: int
    auditor_usuario_id: int
    inicio: datetime
    fin: datetime
    motivo: str


def consultar_accesos_auditor() -> list[AccesoAuditorResumen]:
    with sesion() as conn:
        filas = listar_accesos_auditor(conn)
    return [
        AccesoAuditorResumen(
            id=f.id,
            auditor_usuario_id=f.auditor_usuario_id,
            inicio=f.inicio,
            fin=f.fin,
            motivo=f.motivo,
        )
        for f in filas
    ]


@dataclass(frozen=True, slots=True)
class EvidenciaSoc2Resumen:
    id: int
    control_soc2_id: int
    periodo_inicio: date
    periodo_fin: date
    ruta_artefacto: str
    hash_artefacto: str
    generado_en: datetime


def consultar_evidencia_soc2() -> list[EvidenciaSoc2Resumen]:
    with sesion() as conn:
        filas = listar_evidencia_soc2(conn)
    return [
        EvidenciaSoc2Resumen(
            id=f.id,
            control_soc2_id=f.control_soc2_id,
            periodo_inicio=f.periodo_inicio,
            periodo_fin=f.periodo_fin,
            ruta_artefacto=f.ruta_artefacto,
            hash_artefacto=f.hash_artefacto,
            generado_en=f.generado_en,
        )
        for f in filas
    ]
