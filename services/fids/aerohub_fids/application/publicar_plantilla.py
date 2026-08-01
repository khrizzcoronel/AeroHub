"""Publicacion de una version nueva de plantilla FIDS (Sprint S1.3, Plan
§8.3, RF-T03).

Cada publicacion es un INSERT de una fila INMUTABLE -- nunca se actualiza
una version ya publicada (una pantalla que apunta a una version antigua
sigue siendo resoluble). La version se auto-incrementa por `nombre`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aerohub_kernel import ahora_utc, generar_id

from ..domain import PlantillaFids
from ..infrastructure import (
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    insertar_plantilla,
    obtener_ultima_version_plantilla,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class UsuarioNoIdentificado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoPublicarPlantilla:
    plantilla_id: int
    version: int


@reintentar_en_conflicto()
def publicar_plantilla(
    *, nombre: str, definicion_json: dict[str, Any]
) -> ResultadoPublicarPlantilla:
    tenant_id = contexto_tenant_id()
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        # Publicar una plantilla es un acto humano trazable (RF-T03 exige
        # `creada_por_usuario_id`) -- a diferencia de una API Key/proceso
        # tecnico, que no representa a una persona.
        raise UsuarioNoIdentificado(
            "publicar_plantilla requiere una sesion con usuario identificado"
        )

    plantilla_id = generar_id()
    vigente_desde = ahora_utc()

    with sesion() as conn:
        version_anterior = obtener_ultima_version_plantilla(conn, nombre)
        version_nueva = 1 if version_anterior is None else version_anterior + 1

        # Domain valida ANTES de tocar la base -- fail fast (SRS RNF-M01),
        # incluida la verificacion de PN-11 (0 campos de PII).
        PlantillaFids(
            id=plantilla_id,
            tenant_id=tenant_id,
            nombre=nombre,
            definicion_json=definicion_json,
            version=version_nueva,
            vigente_desde=vigente_desde,
            creada_por_usuario_id=usuario_id,
        )

        insertar_plantilla(
            conn,
            id=plantilla_id,
            tenant_id=tenant_id,
            nombre=nombre,
            definicion_json=definicion_json,
            version=version_nueva,
            vigente_desde=vigente_desde,
            creada_por_usuario_id=usuario_id,
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="plantilla_fids",
            operacion="INSERT",
            clave_primaria={"id": plantilla_id},
            payload={"id": plantilla_id, "nombre": nombre, "version": version_nueva},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="plantilla_fids",
            registro_id=plantilla_id,
            operacion="INSERT",
            valores_nuevos={"nombre": nombre, "version": version_nueva},
        )

    return ResultadoPublicarPlantilla(plantilla_id=plantilla_id, version=version_nueva)
