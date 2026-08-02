"""Registro de reportes regulatorios DGAC (Sprint S1.7, append-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import generar_id

from ..domain import ReporteDgac
from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_reporte_dgac,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class UsuarioNoIdentificado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoRegistrarReporte:
    reporte_id: int


@reintentar_en_conflicto()
def registrar_reporte_dgac(
    *,
    tipo_reporte_id: int,
    periodo_inicio: date,
    periodo_fin: date,
    contenido_ref: str,
    hash_contenido: str,
) -> ResultadoRegistrarReporte:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("registrar_reporte_dgac requiere usuario identificado")
    tenant_id = contexto_tenant_id()
    reporte_id = generar_id()

    ReporteDgac(
        id=reporte_id,
        tenant_id=tenant_id,
        tipo_reporte_id=tipo_reporte_id,
        periodo_inicio=periodo_inicio,
        periodo_fin=periodo_fin,
        contenido_ref=contenido_ref,
        hash_contenido=hash_contenido,
        emitido_por_usuario_id=usuario_id,
    )

    with sesion() as conn:
        insertar_reporte_dgac(
            conn,
            id=reporte_id,
            tenant_id=tenant_id,
            tipo_reporte_id=tipo_reporte_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            contenido_ref=contenido_ref,
            hash_contenido=hash_contenido,
            emitido_por_usuario_id=usuario_id,
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="reporte_dgac",
            operacion="INSERT",
            clave_primaria={"id": reporte_id},
            payload={"id": reporte_id, "tipo_reporte_id": tipo_reporte_id},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="reporte_dgac",
            registro_id=reporte_id,
            operacion="INSERT",
            valores_nuevos={"hash_contenido": hash_contenido},
        )

    return ResultadoRegistrarReporte(reporte_id=reporte_id)
