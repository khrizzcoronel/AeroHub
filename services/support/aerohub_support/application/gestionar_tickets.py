"""Ciclo de vida de tickets de soporte con SLA (Sprint S1.8, CU-D6, US1;
RF-001..RF-005). `role_support` opera sobre tickets de CUALQUIER tenant via
`alcance_global()` (research.md Decision 5) -- un especialista de soporte es
un rol de plataforma, sin tenant propio en su JWT.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import ahora_utc, generar_id

from ..domain import (
    ESTADOS_TICKET,
    Ticket,
    TicketMensaje,
    calcular_sla_objetivo_min,
    transicion_valida_ticket,
)
from ..infrastructure import (
    actualizar_estado_ticket,
    alcance_global,
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
    escribir_journal,
    fijar_primera_respuesta,
    insertar_ticket,
    insertar_ticket_mensaje,
    listar_categorias_ticket,
    listar_mensajes_de_ticket,
    listar_tickets_de_tenant,
    listar_tickets_global,
    obtener_categoria_ticket_por_id,
    obtener_ticket_por_id_de_tenant,
    obtener_ticket_por_id_global,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)

_ROL_SUPPORT = "role_support"
_MOTIVO_ALCANCE_GLOBAL = "atencion_de_soporte"


class UsuarioNoIdentificado(Exception):
    pass


class CategoriaNoEncontrada(Exception):
    pass


class TicketNoEncontrado(Exception):
    pass


class RolNoAutorizado(Exception):
    pass


class MensajeInternoNoAutorizado(Exception):
    pass


class TransicionInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ResultadoCrearTicket:
    ticket_id: int
    sla_objetivo_min: int


@dataclass(frozen=True, slots=True)
class ResultadoResponderTicket:
    mensaje_id: int


@dataclass(frozen=True, slots=True)
class CategoriaTicketTablero:
    id: int
    codigo: str
    nombre: str


def consultar_categorias_ticket() -> list[CategoriaTicketTablero]:
    """Sprint S1.20 -- catalogo global (alcance='global'), sin filtro de
    tenant, para el select del formulario de alta de ticket."""
    with sesion() as conn:
        filas = listar_categorias_ticket(conn)
    return [CategoriaTicketTablero(id=f.id, codigo=f.codigo, nombre=f.nombre) for f in filas]


@dataclass(frozen=True, slots=True)
class TicketTablero:
    id: int
    tenant_id: int
    categoria_id: int
    creado_por_usuario_id: int
    asignado_a_usuario_id: int | None
    severidad: str
    estado: str
    asunto: str
    creado_en: datetime
    primera_respuesta_en: datetime | None
    resuelto_en: datetime | None
    sla_objetivo_min: int


@dataclass(frozen=True, slots=True)
class MensajeTablero:
    id: int
    ticket_id: int
    autor_usuario_id: int
    cuerpo: str
    enviado_en: datetime
    es_interno: bool


def _es_role_support() -> bool:
    return contexto_rol_actor() == _ROL_SUPPORT


def _a_tablero(fila) -> TicketTablero:  # noqa: ANN001 -- Row de SQLAlchemy, sin tipo publico
    return TicketTablero(
        id=fila.id,
        tenant_id=fila.tenant_id,
        categoria_id=fila.categoria_id,
        creado_por_usuario_id=fila.creado_por_usuario_id,
        asignado_a_usuario_id=fila.asignado_a_usuario_id,
        severidad=fila.severidad,
        estado=fila.estado,
        asunto=fila.asunto,
        creado_en=fila.creado_en,
        primera_respuesta_en=fila.primera_respuesta_en,
        resuelto_en=fila.resuelto_en,
        sla_objetivo_min=fila.sla_objetivo_min,
    )


def _mensaje_a_tablero(fila) -> MensajeTablero:  # noqa: ANN001
    return MensajeTablero(
        id=fila.id,
        ticket_id=fila.ticket_id,
        autor_usuario_id=fila.autor_usuario_id,
        cuerpo=fila.cuerpo,
        enviado_en=fila.enviado_en,
        es_interno=fila.es_interno,
    )


@reintentar_en_conflicto()
def crear_ticket(
    *, categoria_id: int, severidad: str, asunto: str, cuerpo_inicial: str
) -> ResultadoCrearTicket:
    tenant_id = contexto_tenant_id()
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("no se puede crear un ticket sin usuario identificado")

    ticket_id = generar_id()

    with sesion() as conn:
        categoria = obtener_categoria_ticket_por_id(conn, categoria_id)
        if categoria is None:
            raise CategoriaNoEncontrada(f"categoria {categoria_id} no encontrada")

        sla_objetivo_min = calcular_sla_objetivo_min(categoria.codigo)
        ahora = ahora_utc()

        # Domain valida antes del INSERT -- fail fast (P1).
        Ticket(
            id=ticket_id,
            tenant_id=tenant_id,
            categoria_id=categoria_id,
            creado_por_usuario_id=usuario_id,
            severidad=severidad,
            estado="abierto",
            asunto=asunto,
            creado_en=ahora,
            sla_objetivo_min=sla_objetivo_min,
        )

        insertar_ticket(
            conn,
            id=ticket_id,
            tenant_id=tenant_id,
            categoria_id=categoria_id,
            creado_por_usuario_id=usuario_id,
            severidad=severidad,
            asunto=asunto,
            sla_objetivo_min=sla_objetivo_min,
        )
        escribir_journal(
            conn,
            esquema="support",
            tabla="ticket",
            operacion="INSERT",
            clave_primaria={"id": ticket_id},
            payload={"id": ticket_id, "categoria_id": categoria_id, "severidad": severidad},
        )
        registrar_auditoria(
            conn,
            esquema="support",
            tabla="ticket",
            registro_id=ticket_id,
            operacion="INSERT",
            valores_nuevos={"asunto": asunto, "severidad": severidad, "estado": "abierto"},
        )

        mensaje_id = generar_id()
        TicketMensaje(
            id=mensaje_id,
            ticket_id=ticket_id,
            autor_usuario_id=usuario_id,
            cuerpo=cuerpo_inicial,
            enviado_en=ahora,
        )
        insertar_ticket_mensaje(
            conn,
            id=mensaje_id,
            ticket_id=ticket_id,
            autor_usuario_id=usuario_id,
            cuerpo=cuerpo_inicial,
            es_interno=False,
        )
        escribir_journal(
            conn,
            esquema="support",
            tabla="ticket_mensaje",
            operacion="INSERT",
            clave_primaria={"id": mensaje_id},
            payload={"id": mensaje_id, "ticket_id": ticket_id},
        )

    return ResultadoCrearTicket(ticket_id=ticket_id, sla_objetivo_min=sla_objetivo_min)


@reintentar_en_conflicto()
def responder_ticket(
    *, ticket_id: int, cuerpo: str, es_interno: bool
) -> ResultadoResponderTicket:
    es_support = _es_role_support()
    if es_interno and not es_support:
        raise MensajeInternoNoAutorizado(
            "solo role_support puede marcar un mensaje como interno"
        )

    mensaje_id = generar_id()
    ahora = ahora_utc()

    if es_support:
        with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_SUPPORT), sesion() as conn:
            fila = obtener_ticket_por_id_global(conn, ticket_id=ticket_id)
            if fila is None:
                raise TicketNoEncontrado(f"ticket {ticket_id} no encontrado")

            usuario_id = contexto_usuario_id()
            if usuario_id is None:
                raise UsuarioNoIdentificado("no se puede responder sin usuario identificado")

            TicketMensaje(
                id=mensaje_id,
                ticket_id=ticket_id,
                autor_usuario_id=usuario_id,
                cuerpo=cuerpo,
                enviado_en=ahora,
                es_interno=es_interno,
            )
            insertar_ticket_mensaje(
                conn,
                id=mensaje_id,
                ticket_id=ticket_id,
                autor_usuario_id=usuario_id,
                cuerpo=cuerpo,
                es_interno=es_interno,
            )
            # FR-003: condicional a nivel de UPDATE (solo si aun es NULL) --
            # seguro llamarlo en CADA respuesta de role_support, atomico
            # incluso ante dos especialistas respondiendo casi
            # simultaneamente (spec.md, Edge Cases).
            fijar_primera_respuesta(conn, id=ticket_id, primera_respuesta_en=ahora)
            escribir_journal(
                conn,
                esquema="support",
                tabla="ticket_mensaje",
                operacion="INSERT",
                clave_primaria={"id": mensaje_id},
                payload={"id": mensaje_id, "ticket_id": ticket_id},
            )
            registrar_auditoria(
                conn,
                esquema="support",
                tabla="ticket_mensaje",
                registro_id=mensaje_id,
                operacion="INSERT",
                valores_nuevos={"ticket_id": ticket_id, "es_interno": es_interno},
                tenant_id=fila.tenant_id,
            )
        return ResultadoResponderTicket(mensaje_id=mensaje_id)

    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        raise UsuarioNoIdentificado("no se puede responder sin usuario identificado")

    with sesion() as conn:
        fila = obtener_ticket_por_id_de_tenant(conn, ticket_id=ticket_id)
        if fila is None:
            raise TicketNoEncontrado(f"ticket {ticket_id} no encontrado")

        TicketMensaje(
            id=mensaje_id,
            ticket_id=ticket_id,
            autor_usuario_id=usuario_id,
            cuerpo=cuerpo,
            enviado_en=ahora,
        )
        insertar_ticket_mensaje(
            conn,
            id=mensaje_id,
            ticket_id=ticket_id,
            autor_usuario_id=usuario_id,
            cuerpo=cuerpo,
            es_interno=False,
        )
        escribir_journal(
            conn,
            esquema="support",
            tabla="ticket_mensaje",
            operacion="INSERT",
            clave_primaria={"id": mensaje_id},
            payload={"id": mensaje_id, "ticket_id": ticket_id},
        )

    return ResultadoResponderTicket(mensaje_id=mensaje_id)


@reintentar_en_conflicto()
def cambiar_estado_ticket(*, ticket_id: int, estado_nuevo: str) -> None:
    if not _es_role_support():
        raise RolNoAutorizado("solo role_support puede cambiar el estado de un ticket")
    if estado_nuevo not in ESTADOS_TICKET:
        raise TransicionInvalida(f"estado invalido: {estado_nuevo!r}")

    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_SUPPORT), sesion() as conn:
        fila = obtener_ticket_por_id_global(conn, ticket_id=ticket_id)
        if fila is None:
            raise TicketNoEncontrado(f"ticket {ticket_id} no encontrado")
        if not transicion_valida_ticket(fila.estado, estado_nuevo):
            raise TransicionInvalida(
                f"transicion invalida: {fila.estado!r} -> {estado_nuevo!r}"
            )

        ahora = ahora_utc()
        resuelto_en = ahora if estado_nuevo == "resuelto" else None
        actualizar_estado_ticket(conn, id=ticket_id, estado=estado_nuevo, resuelto_en=resuelto_en)
        escribir_journal(
            conn,
            esquema="support",
            tabla="ticket",
            operacion="UPDATE",
            clave_primaria={"id": ticket_id},
            payload={"id": ticket_id, "estado": estado_nuevo},
        )
        registrar_auditoria(
            conn,
            esquema="support",
            tabla="ticket",
            registro_id=ticket_id,
            operacion="UPDATE",
            valores_anteriores={"estado": fila.estado},
            valores_nuevos={"estado": estado_nuevo},
            tenant_id=fila.tenant_id,
        )


def consultar_ticket(*, ticket_id: int) -> tuple[TicketTablero, list[MensajeTablero]]:
    es_support = _es_role_support()

    if es_support:
        with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_SUPPORT), sesion() as conn:
            fila = obtener_ticket_por_id_global(conn, ticket_id=ticket_id)
            if fila is None:
                raise TicketNoEncontrado(f"ticket {ticket_id} no encontrado")
            mensajes = listar_mensajes_de_ticket(conn, ticket_id=ticket_id)
        return _a_tablero(fila), [_mensaje_a_tablero(m) for m in mensajes]

    with sesion() as conn:
        fila = obtener_ticket_por_id_de_tenant(conn, ticket_id=ticket_id)
        if fila is None:
            raise TicketNoEncontrado(f"ticket {ticket_id} no encontrado")
        todos = listar_mensajes_de_ticket(conn, ticket_id=ticket_id)
        mensajes = [m for m in todos if not m.es_interno]
    return _a_tablero(fila), [_mensaje_a_tablero(m) for m in mensajes]


def consultar_tickets(
    *, estado: str | None = None, severidad: str | None = None
) -> list[TicketTablero]:
    if _es_role_support():
        with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_SUPPORT), sesion() as conn:
            filas = listar_tickets_global(conn, estado=estado, severidad=severidad)
        return [_a_tablero(f) for f in filas]

    with sesion() as conn:
        filas = listar_tickets_de_tenant(conn)
    return [_a_tablero(f) for f in filas]
