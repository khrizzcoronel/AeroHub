"""Casos de uso de informes operativos de M9 Compliance (Sprint S1.18,
RF-I01/RF-I02/RF-I04). El informe compuesto (emision de reporte_dgac)
tiene validez externa (regulatoria) -- su emision se registra en
compliance.log_auditoria (research.md Decision 4).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import ahora_utc

from ..infrastructure import (
    agrupar_reportes_dgac_por_tipo,
    contexto_tenant_id,
    contexto_usuario_id,
    listar_eventos_auditoria_informe,
    registrar_auditoria,
    sesion,
)


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


def consultar_informe_auditoria_simple(*, periodo_inicio: date, periodo_fin: date) -> InformeSimple:
    with sesion() as conn:
        filas = listar_eventos_auditoria_informe(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
    return InformeSimple(
        parametros={
            "periodo_inicio": periodo_inicio.isoformat(),
            "periodo_fin": periodo_fin.isoformat(),
        },
        generado_en=ahora_utc().isoformat(),
        filas=[
            {
                "evento_id": str(f.id),
                "esquema": f.esquema,
                "tabla": f.tabla,
                "operacion": f.operacion,
                "usuario_id": str(f.usuario_id) if f.usuario_id else None,
                "rol_codigo": f.rol_codigo,
                "ocurrido_en": f.ocurrido_en.isoformat() if f.ocurrido_en else None,
            }
            for f in filas
        ],
    )


def consultar_informe_reportes_dgac_compuesto(
    *, periodo_inicio: date, periodo_fin: date
) -> InformeCompuesto:
    with sesion() as conn:
        grupos = agrupar_reportes_dgac_por_tipo(
            conn, periodo_inicio=periodo_inicio, periodo_fin=periodo_fin
        )
    grupos_informe = [
        GrupoInforme(clave=str(g.tipo_reporte_id), metricas={}, subtotal=int(g.cantidad_reportes))
        for g in grupos
    ]
    total = sum(g.subtotal for g in grupos_informe)

    # RF-I04: informe regulatorio -- validez externa, se registra en
    # compliance.log_auditoria (research.md Decision 4).
    usuario_id = contexto_usuario_id()
    if usuario_id is not None:
        with sesion() as conn:
            registrar_auditoria(
                conn,
                esquema="compliance",
                tabla="informe_reportes_dgac",
                registro_id=0,
                operacion="INSERT",
                valores_nuevos={
                    "periodo_inicio": periodo_inicio.isoformat(),
                    "periodo_fin": periodo_fin.isoformat(),
                    "total": total,
                },
            )

    return InformeCompuesto(
        parametros={
            "periodo_inicio": periodo_inicio.isoformat(),
            "periodo_fin": periodo_fin.isoformat(),
            "tenant_id": str(contexto_tenant_id()),
        },
        generado_en=ahora_utc().isoformat(),
        grupos=grupos_informe,
        total=total,
    )
