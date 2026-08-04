"""Casos de uso de informes operativos de M3 Gates (Sprint S1.18,
RF-I01/RF-I02). Sin logica de negocio nueva.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import ahora_utc

from ..infrastructure import agrupar_asignaciones_por_puerta, listar_asignaciones_informe, sesion


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


def consultar_informe_asignaciones_simple(
    *, periodo_inicio: date, periodo_fin: date, puerta_id: int | None
) -> InformeSimple:
    with sesion() as conn:
        filas = listar_asignaciones_informe(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin, puerta_id=puerta_id
        )
    parametros = {
        "periodo_inicio": periodo_inicio.isoformat(),
        "periodo_fin": periodo_fin.isoformat(),
    }
    if puerta_id is not None:
        parametros["puerta_id"] = str(puerta_id)
    return InformeSimple(
        parametros=parametros,
        generado_en=ahora_utc().isoformat(),
        filas=[
            {
                "asignacion_id": str(f.id),
                "vuelo_id": str(f.vuelo_id),
                "puerta_id": str(f.puerta_id),
                "inicio_previsto": f.inicio_previsto.isoformat(),
                "fin_previsto": f.fin_previsto.isoformat(),
                "estado": f.estado,
            }
            for f in filas
        ],
    )


def consultar_informe_asignaciones_compuesto(
    *, periodo_inicio: date, periodo_fin: date
) -> InformeCompuesto:
    with sesion() as conn:
        grupos = agrupar_asignaciones_por_puerta(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
    grupos_informe = [
        GrupoInforme(
            clave=str(g.puerta_id),
            metricas={"con_conflicto": int(g.con_conflicto)},
            subtotal=int(g.cantidad_asignaciones),
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
