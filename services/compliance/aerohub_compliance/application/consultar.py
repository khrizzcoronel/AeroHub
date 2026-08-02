"""Consultas de tablero: post-mortem con acciones, listado de incidentes."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..infrastructure import (
    listar_acciones_de_post_mortem,
    listar_incidentes,
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
