"""Ciclo de vida de post-mortem, exclusivo role_sre (Sprint S1.7, CU-O13,
RF-O13; ADR-009 -- unica excepcion de mutabilidad del esquema
`compliance`, aplicada aqui porque MonetDB no tiene RLS, mismo patron que
el minimo privilegio de role_ramp_agent en S1.5).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc, generar_id

from ..domain import PostMortem, puede_publicar
from ..infrastructure import (
    actualizar_causa_raiz_post_mortem,
    completar_post_mortem_accion,
    contexto_rol_actor,
    contexto_tenant_id,
    escribir_journal,
    insertar_post_mortem,
    insertar_post_mortem_accion,
    listar_acciones_de_post_mortem,
    obtener_post_mortem_accion_por_id,
    obtener_post_mortem_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)
from ..infrastructure import (
    publicar_post_mortem as _publicar_post_mortem_infra,
)

_ROL_AUTORIZADO = "role_sre"


class RolNoAutorizado(Exception):
    pass


class PostMortemNoEncontrado(Exception):
    pass


class AccionNoEncontrada(Exception):
    pass


class RemediacionIncompleta(Exception):
    pass


def _exigir_role_sre() -> None:
    if contexto_rol_actor() != _ROL_AUTORIZADO:
        raise RolNoAutorizado(
            "solo role_sre puede crear o editar un post-mortem (ADR-009)"
        )


@dataclass(frozen=True, slots=True)
class ResultadoCrearPostMortem:
    post_mortem_id: int


@reintentar_en_conflicto()
def crear_post_mortem(
    *, incidente_ref: str, severidad: str, iniciado_en: datetime
) -> ResultadoCrearPostMortem:
    _exigir_role_sre()
    tenant_id = contexto_tenant_id()
    post_mortem_id = generar_id()

    # Domain valida la fila aislada antes del INSERT -- fail fast.
    PostMortem(
        id=post_mortem_id,
        tenant_id=tenant_id,
        incidente_ref=incidente_ref,
        severidad=severidad,
        estado="en_progreso",
        iniciado_en=iniciado_en,
    )

    with sesion() as conn:
        insertar_post_mortem(
            conn,
            id=post_mortem_id,
            tenant_id=tenant_id,
            incidente_ref=incidente_ref,
            severidad=severidad,
            iniciado_en=iniciado_en,
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="post_mortem",
            operacion="INSERT",
            clave_primaria={"id": post_mortem_id},
            payload={"id": post_mortem_id, "incidente_ref": incidente_ref},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="post_mortem",
            registro_id=post_mortem_id,
            operacion="INSERT",
            valores_nuevos={"incidente_ref": incidente_ref, "estado": "en_progreso"},
        )

    return ResultadoCrearPostMortem(post_mortem_id=post_mortem_id)


@reintentar_en_conflicto()
def editar_causa_raiz(*, post_mortem_id: int, causa_raiz: str) -> None:
    _exigir_role_sre()
    tenant_id = contexto_tenant_id()
    with sesion() as conn:
        if obtener_post_mortem_por_id(conn, post_mortem_id) is None:
            raise PostMortemNoEncontrado(f"post-mortem {post_mortem_id} no encontrado")

        actualizar_causa_raiz_post_mortem(
            conn, id=post_mortem_id, tenant_id=tenant_id, causa_raiz=causa_raiz
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="post_mortem",
            operacion="UPDATE",
            clave_primaria={"id": post_mortem_id},
            payload={"id": post_mortem_id, "campo": "causa_raiz"},
        )
        # FR-007: toda edicion de causa_raiz/estado queda en log_auditoria,
        # preservando trazabilidad pese a la excepcion de mutabilidad.
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="post_mortem",
            registro_id=post_mortem_id,
            operacion="UPDATE",
            valores_nuevos={"causa_raiz": causa_raiz},
        )


@dataclass(frozen=True, slots=True)
class ResultadoAgregarAccion:
    accion_id: int


@reintentar_en_conflicto()
def agregar_accion(
    *,
    post_mortem_id: int,
    descripcion: str,
    responsable_usuario_id: int,
    vence_en: datetime,
    ticket_ref: str | None,
) -> ResultadoAgregarAccion:
    _exigir_role_sre()
    accion_id = generar_id()

    with sesion() as conn:
        if obtener_post_mortem_por_id(conn, post_mortem_id) is None:
            raise PostMortemNoEncontrado(f"post-mortem {post_mortem_id} no encontrado")

        insertar_post_mortem_accion(
            conn,
            id=accion_id,
            post_mortem_id=post_mortem_id,
            descripcion=descripcion,
            responsable_usuario_id=responsable_usuario_id,
            vence_en=vence_en,
            ticket_ref=ticket_ref,
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="post_mortem_accion",
            operacion="INSERT",
            clave_primaria={"id": accion_id},
            payload={"id": accion_id, "post_mortem_id": post_mortem_id},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="post_mortem_accion",
            registro_id=accion_id,
            operacion="INSERT",
            valores_nuevos={"post_mortem_id": post_mortem_id, "descripcion": descripcion},
        )

    return ResultadoAgregarAccion(accion_id=accion_id)


@reintentar_en_conflicto()
def completar_accion(*, accion_id: int) -> None:
    _exigir_role_sre()
    ahora = ahora_utc()

    with sesion() as conn:
        if obtener_post_mortem_accion_por_id(conn, accion_id) is None:
            raise AccionNoEncontrada(f"accion {accion_id} no encontrada")

        completar_post_mortem_accion(conn, id=accion_id, completada_en=ahora)
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="post_mortem_accion",
            operacion="UPDATE",
            clave_primaria={"id": accion_id},
            payload={"id": accion_id, "estado": "completada"},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="post_mortem_accion",
            registro_id=accion_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "completada"},
        )


@reintentar_en_conflicto()
def publicar_post_mortem(*, post_mortem_id: int) -> None:
    """FR-005: rechaza si alguna accion de remediacion no esta
    'completada' -- consulta que domain/ puro no puede hacer por si solo
    (necesita leer otra tabla)."""
    _exigir_role_sre()
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        fila = obtener_post_mortem_por_id(conn, post_mortem_id)
        if fila is None:
            raise PostMortemNoEncontrado(f"post-mortem {post_mortem_id} no encontrado")

        acciones = listar_acciones_de_post_mortem(conn, post_mortem_id=post_mortem_id)
        if not puede_publicar([a.estado for a in acciones]):
            raise RemediacionIncompleta(
                f"post-mortem {post_mortem_id} tiene acciones de remediacion sin completar"
            )

        ahora = ahora_utc()
        tiempo_resolucion_min = int((ahora - fila.iniciado_en).total_seconds() / 60)
        _publicar_post_mortem_infra(
            conn,
            id=post_mortem_id,
            tenant_id=tenant_id,
            publicado_en=ahora,
            tiempo_resolucion_min=tiempo_resolucion_min,
        )
        escribir_journal(
            conn,
            esquema="compliance",
            tabla="post_mortem",
            operacion="UPDATE",
            clave_primaria={"id": post_mortem_id},
            payload={"id": post_mortem_id, "estado": "publicado"},
        )
        registrar_auditoria(
            conn,
            esquema="compliance",
            tabla="post_mortem",
            registro_id=post_mortem_id,
            operacion="UPDATE",
            valores_nuevos={"estado": "publicado", "tiempo_resolucion_min": tiempo_resolucion_min},
        )
