"""Otorgamiento de acceso temporal a un auditor regulatorio (Sprint S1.7,
append-only)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import generar_id

from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_acceso_auditor,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class UsuarioNoIdentificado(Exception):
    pass


class VentanaInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoOtorgarAcceso:
    acceso_id: int


@reintentar_en_conflicto()
def otorgar_acceso_auditor(
    *, auditor_usuario_id: int, inicio: datetime, fin: datetime, alcance_json: dict, motivo: str
) -> ResultadoOtorgarAcceso:
    otorgado_por = contexto_usuario_id()
    if otorgado_por is None:
        raise UsuarioNoIdentificado("otorgar_acceso_auditor requiere usuario identificado")
    if fin <= inicio:
        raise VentanaInvalida(f"fin ({fin}) debe ser posterior a inicio ({inicio})")
    tenant_id = contexto_tenant_id()
    acceso_id = generar_id()

    with sesion() as conn:
        insertar_acceso_auditor(
            conn,
            id=acceso_id,
            tenant_id=tenant_id,
            auditor_usuario_id=auditor_usuario_id,
            otorgado_por_usuario_id=otorgado_por,
            inicio=inicio,
            fin=fin,
            alcance_json=alcance_json,
            motivo=motivo,
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="acceso_auditor",
            operacion="INSERT",
            clave_primaria={"id": acceso_id},
            payload={"id": acceso_id, "auditor_usuario_id": auditor_usuario_id},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="acceso_auditor",
            registro_id=acceso_id,
            operacion="INSERT",
            valores_nuevos={"auditor_usuario_id": auditor_usuario_id, "motivo": motivo},
        )

    return ResultadoOtorgarAcceso(acceso_id=acceso_id)
