"""Publicacion y busqueda de la base de conocimientos (Sprint S1.8, CU-D6,
US4; RF-012..RF-014). `articulo_kb`/`etiqueta` son alcance 'global' -- sin
tenant_id, no requieren `alcance_global()` para escribir/leer (el guardian
G2 solo exige filtro de tenant sobre tablas alcance='tenant').
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc, generar_id

from ..domain import ArticuloKB
from ..infrastructure import (
    asociar_etiqueta_articulo,
    buscar_articulos_kb,
    contexto_rol_actor,
    contexto_usuario_id,
    escribir_journal,
    insertar_articulo_kb,
    insertar_etiqueta,
    listar_etiquetas_de_articulo,
    obtener_articulo_kb_por_id,
    obtener_etiqueta_por_nombre,
    obtener_version_maxima_articulo,
    publicar_articulo_kb,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)

_ROLES_AUTORIZADOS = ("role_support", "role_platform_admin")


class RolNoAutorizado(Exception):
    pass


class UsuarioNoIdentificado(Exception):
    pass


class ArticuloNoEncontrado(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoPublicarArticulo:
    articulo_id: int
    version: int


@dataclass(frozen=True, slots=True)
class ArticuloKBTablero:
    id: int
    titulo: str
    cuerpo: str
    version: int
    publicado_en: datetime | None
    etiquetas: list[str]


def _exigir_rol_autorizado() -> None:
    if contexto_rol_actor() not in _ROLES_AUTORIZADOS:
        raise RolNoAutorizado(
            "solo role_support o role_platform_admin pueden publicar en la KB"
        )


@reintentar_en_conflicto()
def publicar_articulo(
    *, titulo: str, cuerpo: str, etiquetas: list[str]
) -> ResultadoPublicarArticulo:
    _exigir_rol_autorizado()
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("no se puede publicar un articulo sin usuario identificado")

    articulo_id = generar_id()

    with sesion() as conn:
        version = obtener_version_maxima_articulo(conn, titulo=titulo) + 1

        # Domain valida antes del INSERT -- fail fast (P1).
        ArticuloKB(
            id=articulo_id,
            titulo=titulo,
            cuerpo=cuerpo,
            version=version,
            estado="borrador",
            autor_usuario_id=usuario_id,
        )

        insertar_articulo_kb(
            conn,
            id=articulo_id,
            titulo=titulo,
            cuerpo=cuerpo,
            version=version,
            autor_usuario_id=usuario_id,
        )
        escribir_journal(
            conn,
            esquema="support",
            tabla="articulo_kb",
            operacion="INSERT",
            clave_primaria={"id": articulo_id},
            payload={"id": articulo_id, "titulo": titulo, "version": version},
        )

        ahora = ahora_utc()
        publicar_articulo_kb(conn, id=articulo_id, publicado_en=ahora)
        escribir_journal(
            conn,
            esquema="support",
            tabla="articulo_kb",
            operacion="UPDATE",
            clave_primaria={"id": articulo_id},
            payload={"id": articulo_id, "estado": "publicado"},
        )
        registrar_auditoria(
            conn,
            esquema="support",
            tabla="articulo_kb",
            registro_id=articulo_id,
            operacion="INSERT",
            valores_nuevos={"titulo": titulo, "version": version, "estado": "publicado"},
        )

        for nombre in etiquetas:
            fila_etiqueta = obtener_etiqueta_por_nombre(conn, nombre)
            if fila_etiqueta is None:
                etiqueta_id = generar_id()
                insertar_etiqueta(conn, id=etiqueta_id, nombre=nombre)
                escribir_journal(
                    conn,
                    esquema="support",
                    tabla="etiqueta",
                    operacion="INSERT",
                    clave_primaria={"id": etiqueta_id},
                    payload={"id": etiqueta_id, "nombre": nombre},
                )
            else:
                etiqueta_id = fila_etiqueta.id
            asociar_etiqueta_articulo(conn, articulo_id=articulo_id, etiqueta_id=etiqueta_id)
            escribir_journal(
                conn,
                esquema="support",
                tabla="articulo_kb_etiqueta",
                operacion="INSERT",
                clave_primaria={"articulo_id": articulo_id, "etiqueta_id": etiqueta_id},
                payload={"articulo_id": articulo_id, "etiqueta_id": etiqueta_id},
            )

    return ResultadoPublicarArticulo(articulo_id=articulo_id, version=version)


def buscar_articulos(
    *, texto: str | None = None, etiqueta: str | None = None
) -> list[ArticuloKBTablero]:
    with sesion() as conn:
        filas = buscar_articulos_kb(conn, texto=texto, etiqueta_nombre=etiqueta)
        return [
            ArticuloKBTablero(
                id=f.id,
                titulo=f.titulo,
                cuerpo=f.cuerpo,
                version=f.version,
                publicado_en=f.publicado_en,
                etiquetas=listar_etiquetas_de_articulo(conn, articulo_id=f.id),
            )
            for f in filas
        ]


def obtener_articulo(*, articulo_id: int) -> ArticuloKBTablero:
    with sesion() as conn:
        fila = obtener_articulo_kb_por_id(conn, articulo_id)
        if fila is None:
            raise ArticuloNoEncontrado(f"articulo {articulo_id} no encontrado")
        etiquetas = listar_etiquetas_de_articulo(conn, articulo_id=articulo_id)

    return ArticuloKBTablero(
        id=fila.id,
        titulo=fila.titulo,
        cuerpo=fila.cuerpo,
        version=fila.version,
        publicado_en=fila.publicado_en,
        etiquetas=etiquetas,
    )
