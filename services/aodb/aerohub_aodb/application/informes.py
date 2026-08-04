"""Casos de uso de informes operativos de M1 AODB (Sprint S1.18,
RF-I01/RF-I02). Sin logica de negocio nueva -- arma la forma
parametros/generado_en/filas (simple) o grupos/total (compuesto) sobre
las consultas ya agregadas por SQL de infrastructure/consultas_informe.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import ahora_utc

from ..infrastructure import agrupar_vuelos_por_aerolinea, listar_vuelos_informe, sesion


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


def consultar_informe_vuelos_simple(
    *, periodo_inicio: date, periodo_fin: date, aerolinea_id: int | None
) -> InformeSimple:
    with sesion() as conn:
        filas = listar_vuelos_informe(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin, aerolinea_id=aerolinea_id
        )
    parametros = {
        "periodo_inicio": periodo_inicio.isoformat(),
        "periodo_fin": periodo_fin.isoformat(),
    }
    if aerolinea_id is not None:
        parametros["aerolinea_id"] = str(aerolinea_id)
    return InformeSimple(
        parametros=parametros,
        generado_en=ahora_utc().isoformat(),
        filas=[
            {
                "vuelo_id": str(f.id),
                "fecha_operacion": f.fecha_operacion.isoformat(),
                "aerolinea_id": str(f.aerolinea_id),
                "numero_vuelo": f.numero_vuelo,
                "sentido": f.sentido,
            }
            for f in filas
        ],
    )


def consultar_informe_vuelos_compuesto(
    *, periodo_inicio: date, periodo_fin: date
) -> InformeCompuesto:
    with sesion() as conn:
        grupos = agrupar_vuelos_por_aerolinea(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
    grupos_informe = [
        GrupoInforme(
            clave=str(g.aerolinea_id),
            metricas={
                "con_llegada": int(g.con_llegada),
                "puntualidad_pct": (
                    round(100 * g.a_tiempo / g.con_llegada, 1) if g.con_llegada else 0.0
                ),
            },
            subtotal=int(g.cantidad_vuelos),
        )
        for g in grupos
    ]
    # Total = suma de subtotales YA agregados por SQL, nunca re-suma de
    # filas crudas (plan v3.0 §8-bis.0 regla 2 / RF-I02).
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
