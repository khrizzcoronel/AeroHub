"""Registro de evidencia de un control SOC 2 (Sprint S1.7, append-only,
RF-T11)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from aerohub_kernel import generar_id

from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_evidencia_soc2,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


@dataclass(frozen=True, slots=True)
class ResultadoRegistrarEvidencia:
    evidencia_id: int


@reintentar_en_conflicto()
def registrar_evidencia_soc2(
    *,
    control_soc2_id: int,
    periodo_inicio: date,
    periodo_fin: date,
    ruta_artefacto: str,
    hash_artefacto: str,
    referencia_log_id: int | None = None,
) -> ResultadoRegistrarEvidencia:
    tenant_id = contexto_tenant_id()
    evidencia_id = generar_id()

    with sesion() as conn:
        insertar_evidencia_soc2(
            conn,
            id=evidencia_id,
            control_soc2_id=control_soc2_id,
            tenant_id=tenant_id,
            periodo_inicio=periodo_inicio,
            periodo_fin=periodo_fin,
            ruta_artefacto=ruta_artefacto,
            hash_artefacto=hash_artefacto,
            referencia_log_id=referencia_log_id,
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="evidencia_soc2",
            operacion="INSERT",
            clave_primaria={"id": evidencia_id},
            payload={"id": evidencia_id, "control_soc2_id": control_soc2_id},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="evidencia_soc2",
            registro_id=evidencia_id,
            operacion="INSERT",
            valores_nuevos={"control_soc2_id": control_soc2_id, "hash_artefacto": hash_artefacto},
        )

    return ResultadoRegistrarEvidencia(evidencia_id=evidencia_id)
