"""Casos de uso de informes operativos de M4 Ground Ops (Sprint S1.18,
RF-I01/RF-I02). Sin logica de negocio nueva.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import ahora_utc

from ..infrastructure import agrupar_turnarounds_por_tipo_tarea, listar_turnarounds_informe, sesion


@dataclass(frozen=True, slots=True)
class InformeSimple:
    parametros: dict[str, str]
    generado_en: str
    filas: list[dict[str, object]]


@dataclass(frozen=True, slots=True)
class GrupoInforme:
    clave: str
    metricas: dict[str, object]
    subtotal: int


@dataclass(frozen=True, slots=True)
class InformeCompuesto:
    parametros: dict[str, str]
    generado_en: str
    grupos: list[GrupoInforme]
    total: int


def consultar_informe_turnarounds_simple(
    *, periodo_inicio: date, periodo_fin: date, estado: str | None
) -> InformeSimple:
    with sesion() as conn:
        filas = listar_turnarounds_informe(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin, estado=estado
        )
    parametros = {
        "periodo_inicio": periodo_inicio.isoformat(),
        "periodo_fin": periodo_fin.isoformat(),
    }
    if estado is not None:
        parametros["estado"] = estado
    return InformeSimple(
        parametros=parametros,
        generado_en=ahora_utc().isoformat(),
        filas=[
            {
                "turnaround_id": str(f.id),
                "vuelo_llegada_id": str(f.vuelo_llegada_id),
                "vuelo_salida_id": str(f.vuelo_salida_id) if f.vuelo_salida_id else None,
                "inicio_previsto": f.inicio_previsto.isoformat(),
                "estado": f.estado,
            }
            for f in filas
        ],
    )


def consultar_informe_turnarounds_compuesto(
    *, periodo_inicio: date, periodo_fin: date
) -> InformeCompuesto:
    with sesion() as conn:
        grupos = agrupar_turnarounds_por_tipo_tarea(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
    grupos_informe = [
        GrupoInforme(
            clave=str(g.tipo_tarea_id),
            metricas={
                "completadas": int(g.completadas),
                "con_incidencia": int(g.con_incidencia),
            },
            subtotal=int(g.cantidad_tareas),
        )
        for g in grupos
    ]
    total = sum(g.subtotal for g in grupos_informe)
    return InformeCompuesto(
        parametros={
            "periodo_inicio": periodo_inicio.isoformat(),
            "periodo_fin": periodo_fin.isoformat(),
        },
        generado_en=ahora_utc().isoformat(),
        grupos=grupos_informe,
        total=total,
    )
