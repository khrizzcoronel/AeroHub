"""Publicacion y consulta de changelog (Sprint S1.8, CU-D6, US5; RF-015,
RF-016). `changelog`/`changelog_item` son alcance 'global' -- visibles a
todos los tenants sin condicionar a licencia de modulo (research.md
Decision 7: `aerohub_support` no participa del mapa de licenciamiento).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc, generar_id

from ..infrastructure import (
    contexto_rol_actor,
    escribir_journal,
    insertar_changelog,
    insertar_changelog_item,
    listar_changelog,
    listar_items_de_changelog,
    obtener_modulo_por_codigo,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)

_ROL_AUTORIZADO = "role_platform_admin"


class RolNoAutorizado(Exception):
    pass


class ModuloNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ItemChangelogEntrada:
    modulo_codigo: str
    tipo_cambio: str
    descripcion: str


@dataclass(frozen=True, slots=True)
class ResultadoPublicarChangelog:
    changelog_id: int


@dataclass(frozen=True, slots=True)
class ItemChangelogTablero:
    id: int
    modulo_id: int
    tipo_cambio: str
    descripcion: str


@dataclass(frozen=True, slots=True)
class ChangelogTablero:
    id: int
    version_producto: str
    resumen: str
    publicado_en: datetime
    items: list[ItemChangelogTablero]


@reintentar_en_conflicto()
def publicar_changelog(
    *, version_producto: str, resumen: str, items: list[ItemChangelogEntrada]
) -> ResultadoPublicarChangelog:
    if contexto_rol_actor() != _ROL_AUTORIZADO:
        raise RolNoAutorizado("solo role_platform_admin puede publicar el changelog")

    changelog_id = generar_id()
    ahora = ahora_utc()

    with sesion() as conn:
        modulos_por_codigo: dict[str, int] = {}
        for item in items:
            if item.modulo_codigo not in modulos_por_codigo:
                fila_modulo = obtener_modulo_por_codigo(conn, item.modulo_codigo)
                if fila_modulo is None:
                    raise ModuloNoEncontrado(f"modulo {item.modulo_codigo!r} no encontrado")
                modulos_por_codigo[item.modulo_codigo] = fila_modulo.id

        insertar_changelog(
            conn,
            id=changelog_id,
            version_producto=version_producto,
            resumen=resumen,
            publicado_en=ahora,
        )
        escribir_journal(
            conn,
            esquema="support",
            tabla="changelog",
            operacion="INSERT",
            clave_primaria={"id": changelog_id},
            payload={"id": changelog_id, "version_producto": version_producto},
        )
        registrar_auditoria(
            conn,
            esquema="support",
            tabla="changelog",
            registro_id=changelog_id,
            operacion="INSERT",
            valores_nuevos={"version_producto": version_producto, "resumen": resumen},
        )

        for item in items:
            item_id = generar_id()
            insertar_changelog_item(
                conn,
                id=item_id,
                changelog_id=changelog_id,
                modulo_id=modulos_por_codigo[item.modulo_codigo],
                tipo_cambio=item.tipo_cambio,
                descripcion=item.descripcion,
            )
            escribir_journal(
                conn,
                esquema="support",
                tabla="changelog_item",
                operacion="INSERT",
                clave_primaria={"id": item_id},
                payload={"id": item_id, "changelog_id": changelog_id},
            )

    return ResultadoPublicarChangelog(changelog_id=changelog_id)


def consultar_changelog() -> list[ChangelogTablero]:
    with sesion() as conn:
        cabeceras = listar_changelog(conn)
        resultado = []
        for c in cabeceras:
            items = listar_items_de_changelog(conn, changelog_id=c.id)
            resultado.append(
                ChangelogTablero(
                    id=c.id,
                    version_producto=c.version_producto,
                    resumen=c.resumen,
                    publicado_en=c.publicado_en,
                    items=[
                        ItemChangelogTablero(
                            id=i.id,
                            modulo_id=i.modulo_id,
                            tipo_cambio=i.tipo_cambio,
                            descripcion=i.descripcion,
                        )
                        for i in items
                    ],
                )
            )
    return resultado
