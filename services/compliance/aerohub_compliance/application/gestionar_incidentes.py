"""Registro de incidentes de seguridad (Sprint S1.7, append-only,
PN-04 reforzada)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import generar_id

from ..domain import IncidenteSeguridad
from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_incidente_seguridad,
    obtener_tipo_incidente_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class TipoIncidenteNoEncontrado(Exception):
    pass


class UsuarioNoIdentificado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCrearIncidente:
    incidente_id: int


@reintentar_en_conflicto()
def crear_incidente(
    *, tipo_incidente_id: int, descripcion: str, severidad: str, detectado_en: datetime
) -> ResultadoCrearIncidente:
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("crear_incidente requiere una sesion con usuario identificado")
    tenant_id = contexto_tenant_id()
    incidente_id = generar_id()

    IncidenteSeguridad(
        id=incidente_id,
        tenant_id=tenant_id,
        tipo_incidente_id=tipo_incidente_id,
        descripcion=descripcion,
        severidad=severidad,
        detectado_en=detectado_en,
        reportado_por_usuario_id=usuario_id,
        estado="abierto",
    )

    with sesion() as conn:
        if obtener_tipo_incidente_por_id(conn, tipo_incidente_id) is None:
            raise TipoIncidenteNoEncontrado(f"tipo de incidente {tipo_incidente_id} no encontrado")

        insertar_incidente_seguridad(
            conn,
            id=incidente_id,
            tenant_id=tenant_id,
            tipo_incidente_id=tipo_incidente_id,
            descripcion=descripcion,
            severidad=severidad,
            detectado_en=detectado_en,
            reportado_por_usuario_id=usuario_id,
            estado="abierto",
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="incidente_seguridad",
            operacion="INSERT",
            clave_primaria={"id": incidente_id},
            payload={"id": incidente_id, "tipo_incidente_id": tipo_incidente_id},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="incidente_seguridad",
            registro_id=incidente_id,
            operacion="INSERT",
            valores_nuevos={"severidad": severidad, "estado": "abierto"},
        )

    return ResultadoCrearIncidente(incidente_id=incidente_id)
