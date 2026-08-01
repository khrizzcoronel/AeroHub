"""Alta de pantalla FIDS (Sprint S1.3, Plan §8.3, RF-O07)."""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import generar_id

from ..domain import PantallaFids
from ..infrastructure import (
    contexto_tenant_id,
    escribir_journal,
    insertar_pantalla,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


@dataclass(frozen=True, slots=True)
class ResultadoRegistrarPantalla:
    pantalla_id: int


@reintentar_en_conflicto()
def registrar_pantalla(
    *,
    terminal_id: int,
    codigo: str,
    plantilla_id: int,
    ubicacion_descripcion: str | None = None,
    version_firmware: str | None = None,
) -> ResultadoRegistrarPantalla:
    tenant_id = contexto_tenant_id()
    pantalla_id = generar_id()

    # Domain valida ANTES de tocar la base -- fail fast (SRS RNF-M01).
    PantallaFids(
        id=pantalla_id,
        tenant_id=tenant_id,
        terminal_id=terminal_id,
        codigo=codigo,
        plantilla_id=plantilla_id,
        estado="sin_senal",
        ubicacion_descripcion=ubicacion_descripcion,
        version_firmware=version_firmware,
    )

    with sesion() as conn:
        insertar_pantalla(
            conn,
            id=pantalla_id,
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            codigo=codigo,
            plantilla_id=plantilla_id,
            ubicacion_descripcion=ubicacion_descripcion,
            version_firmware=version_firmware,
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="pantalla_fids",
            operacion="INSERT",
            clave_primaria={"id": pantalla_id},
            payload={"id": pantalla_id, "codigo": codigo},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="pantalla_fids",
            registro_id=pantalla_id,
            operacion="INSERT",
            valores_nuevos={"codigo": codigo, "plantilla_id": plantilla_id},
        )

    return ResultadoRegistrarPantalla(pantalla_id=pantalla_id)
