"""Consultas de tablero: turnarounds del tenant y tareas de un turnaround
(con minimo privilegio para role_ramp_agent, ver
aerohub_ramp.infrastructure.consultas.listar_tareas_de_turnaround).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ..infrastructure import (
    contexto_rol_actor,
    contexto_usuario_id,
    listar_incidencias,
    listar_tareas_de_turnaround,
    listar_turnarounds,
    sesion,
)


@dataclass(frozen=True, slots=True)
class TurnaroundTablero:
    id: int
    vuelo_llegada_id: int
    numero_vuelo_llegada: str
    vuelo_salida_id: int
    numero_vuelo_salida: str
    aeronave_id: int
    inicio_previsto: datetime
    fin_previsto: datetime
    estado: str


@dataclass(frozen=True, slots=True)
class TareaTablero:
    id: int
    turnaround_id: int
    tipo_tarea_id: int
    agente_usuario_id: int
    inicio_real: datetime | None
    fin_real: datetime | None
    estado: str


@dataclass(frozen=True, slots=True)
class IncidenciaTablero:
    id: int
    tarea_turnaround_id: int
    tipo_incidencia_codigo: str
    descripcion: str
    severidad: str
    detectada_en: datetime


def consultar_turnarounds() -> list[TurnaroundTablero]:
    with sesion() as conn:
        filas = listar_turnarounds(conn)
    return [
        TurnaroundTablero(
            id=f.id,
            vuelo_llegada_id=f.vuelo_llegada_id,
            numero_vuelo_llegada=f.numero_vuelo_llegada,
            vuelo_salida_id=f.vuelo_salida_id,
            numero_vuelo_salida=f.numero_vuelo_salida,
            aeronave_id=f.aeronave_id,
            inicio_previsto=f.inicio_previsto,
            fin_previsto=f.fin_previsto,
            estado=f.estado,
        )
        for f in filas
    ]


def consultar_tareas_de_turnaround(*, turnaround_id: int) -> list[TareaTablero]:
    with sesion() as conn:
        filas = listar_tareas_de_turnaround(
            conn,
            turnaround_id=turnaround_id,
            rol_actor=contexto_rol_actor(),
            usuario_id=contexto_usuario_id(),
        )
    return [
        TareaTablero(
            id=f.id,
            turnaround_id=f.turnaround_id,
            tipo_tarea_id=f.tipo_tarea_id,
            agente_usuario_id=f.agente_usuario_id,
            inicio_real=f.inicio_real,
            fin_real=f.fin_real,
            estado=f.estado,
        )
        for f in filas
    ]


def consultar_incidencias() -> list[IncidenciaTablero]:
    with sesion() as conn:
        filas = listar_incidencias(conn)
    return [
        IncidenciaTablero(
            id=f.id,
            tarea_turnaround_id=f.tarea_turnaround_id,
            tipo_incidencia_codigo=f.tipo_incidencia_codigo,
            descripcion=f.descripcion,
            severidad=f.severidad,
            detectada_en=f.detectada_en,
        )
        for f in filas
    ]
