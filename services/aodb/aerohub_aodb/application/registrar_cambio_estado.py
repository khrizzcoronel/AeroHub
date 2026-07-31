"""Registro de cambio de estado de vuelo (Sprint S1.1, Plan §8.1).

Consulta el estado vigente (ops.v_vuelo_estado_actual) para validar la
transicion ANTES de insertar -- domain.validar_transicion necesita saber
si el estado actual es terminal, y esa informacion vive en el motor
(catalogo.estado_vuelo_catalogo.es_terminal), no en memoria.

`@reintentar_en_conflicto` (S1.2, RNF-P01): bajo cambios de estado
concurrentes sobre el MISMO vuelo, MonetDB puede abortar la transaccion en
el commit (SQLSTATE 40001, control de concurrencia optimista) -- se
reintenta la funcion COMPLETA, no solo el commit (ver el docstring de
aerohub_repository.reintentos).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_kernel import ahora_utc, generar_id
from sqlalchemy import select
from sqlalchemy.engine import Connection

from ..domain import EstadoVuelo, validar_origen_cambio, validar_transicion
from ..infrastructure import (
    EventoEstadoVuelo,
    broadcaster_global,
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    estado_vuelo_catalogo,
    insertar_vuelo_estado,
    obtener_estado_catalogo_por_codigo,
    obtener_estado_vuelo_actual_por_id,
    obtener_vuelo_por_id,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)


class VueloNoEncontrado(Exception):
    pass


class EstadoDesconocido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCambioEstado:
    vuelo_estado_id: int


@reintentar_en_conflicto()
def registrar_cambio_estado(
    *, vuelo_id: int, codigo_estado_nuevo: str, origen_cambio: str
) -> ResultadoCambioEstado:
    validar_origen_cambio(origen_cambio)
    tenant_id = contexto_tenant_id()

    with sesion() as conn:
        # PN-01: vuelo de otro tenant = "no existe" (0 filas), no una
        # excepcion que distinga "no existe" de "no es tuyo".
        if obtener_vuelo_por_id(conn, vuelo_id) is None:
            raise VueloNoEncontrado(f"vuelo {vuelo_id} no encontrado")

        fila_estado_nuevo = obtener_estado_catalogo_por_codigo(conn, codigo_estado_nuevo)
        if fila_estado_nuevo is None:
            raise EstadoDesconocido(f"codigo de estado desconocido: {codigo_estado_nuevo!r}")
        estado_nuevo = EstadoVuelo(
            id=fila_estado_nuevo.id,
            codigo=fila_estado_nuevo.codigo,
            es_terminal=fila_estado_nuevo.es_terminal,
        )

        fila_actual = obtener_estado_vuelo_actual_por_id(conn, vuelo_id)
        estado_actual = (
            None
            if fila_actual is None
            else _resolver_estado_catalogo(conn, fila_actual.estado_id)
        )
        validar_transicion(estado_actual, estado_nuevo)

        vuelo_estado_id = generar_id()
        insertar_vuelo_estado(
            conn,
            id=vuelo_estado_id,
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            estado_id=estado_nuevo.id,
            origen_cambio=origen_cambio,
            registrado_por_usuario_id=contexto_usuario_id(),
        )
        escribir_journal(
            conn,
            esquema="ops",
            tabla="vuelo_estado",
            operacion="INSERT",
            clave_primaria={"id": vuelo_estado_id},
            payload={"vuelo_id": vuelo_id, "estado_id": estado_nuevo.id},
        )
        registrar_auditoria(
            conn,
            esquema="ops",
            tabla="vuelo_estado",
            registro_id=vuelo_estado_id,
            operacion="INSERT",
            valores_nuevos={"vuelo_id": vuelo_id, "codigo_estado": codigo_estado_nuevo},
        )

    # Publicar DESPUES de que la transaccion confirmo (fuera del `with
    # sesion()`) -- un suscriptor jamas debe ver un evento de una mutacion
    # que termino revirtiendose (RNF-P01 mide propagacion de cambios
    # REALES, no intentos).
    broadcaster_global.publicar(
        EventoEstadoVuelo(
            tenant_id=tenant_id,
            vuelo_id=vuelo_id,
            vuelo_estado_id=vuelo_estado_id,
            estado_id=estado_nuevo.id,
            codigo_estado=codigo_estado_nuevo,
            ocurrido_en=ahora_utc(),
        )
    )
    return ResultadoCambioEstado(vuelo_estado_id=vuelo_estado_id)


def _resolver_estado_catalogo(conn: Connection, estado_id: int) -> EstadoVuelo:
    # obtener_estado_catalogo_por_codigo busca por codigo; aqui ya tenemos
    # el id (de v_vuelo_estado_actual) y necesitamos su es_terminal --
    # una consulta directa por id, sin pasar por contexto de tenant (el
    # catalogo es 'global').
    fila = conn.execute(
        select(estado_vuelo_catalogo).where(estado_vuelo_catalogo.c.id == estado_id)
    ).first()
    if fila is None:
        # estado_id viene de ops.vuelo_estado (FK logica hacia el catalogo)
        # -- si no aparece, el catalogo es inconsistente, no un caso de
        # negocio a manejar.
        raise EstadoDesconocido(f"estado_id {estado_id} no existe en el catalogo")
    return EstadoVuelo(id=fila.id, codigo=fila.codigo, es_terminal=fila.es_terminal)
