"""Casos de uso de informes operativos de Tenancy (Sprint S1.18,
RF-I01/RF-I02). Sin logica de negocio nueva -- alcance 'interno', mismo
criterio que `listar_tenants` (consultar_tenants.py, S1.14).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import ahora_utc

from ..infrastructure import agrupar_tenants_por_plan_estado, listar_tenants_informe, sesion


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


def consultar_informe_tenants_simple(*, estado: str | None) -> InformeSimple:
    with sesion() as conn:
        filas = listar_tenants_informe(conn, estado=estado)
    parametros: dict[str, str] = {}
    if estado is not None:
        parametros["estado"] = estado
    return InformeSimple(
        parametros=parametros,
        generado_en=ahora_utc().isoformat(),
        filas=[
            {
                "tenant_id": str(f.id),
                "codigo": f.codigo,
                "razon_social": f.razon_social,
                "plan_id": str(f.plan_id),
                "estado": f.estado,
            }
            for f in filas
        ],
    )


def consultar_informe_tenants_compuesto() -> InformeCompuesto:
    with sesion() as conn:
        grupos = agrupar_tenants_por_plan_estado(conn)
    grupos_informe = [
        GrupoInforme(
            clave=f"{g.plan_id}:{g.estado}",
            metricas={
                "usuarios_activos": int(g.usuarios_activos or 0),
                "licencias_vigentes": int(g.licencias_vigentes or 0),
            },
            subtotal=int(g.cantidad_tenants),
        )
        for g in grupos
    ]
    total = sum(g.subtotal for g in grupos_informe)
    return InformeCompuesto(
        parametros={}, generado_en=ahora_utc().isoformat(), grupos=grupos_informe, total=total
    )
