"""Endpoints HTTP de aerohub_support (Sprint S1.8, Plan Sec8.8; contracts/
support-api.md). Solo traduce HTTP <-> application/: valida forma con
Pydantic, invoca el caso de uso, traduce sus excepciones a codigos de
estado. Ninguna regla de negocio vive aqui (SRS Sec6.4). Ninguna ruta
requiere licencia de modulo (research.md Decision 7 -- D6/M8 son
capacidades de plataforma, no modulos M1-M6 licenciables).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from ..application import (
    ArticuloKBInvalido,
    ArticuloNoEncontrado,
    ChangelogRolNoAutorizado,
    ItemChangelogEntrada,
    KBRolNoAutorizado,
    KBUsuarioNoIdentificado,
    MensajeInternoNoAutorizado,
    ModuloNoEncontrado,
    ObservabilidadServicioInvalido,
    TicketCategoriaNoEncontrada,
    TicketInvalido,
    TicketNoEncontrado,
    TicketRolNoAutorizado,
    TicketUsuarioNoIdentificado,
    TransicionInvalida,
    buscar_articulos,
    cambiar_estado_ticket,
    consultar_categorias_ticket,
    consultar_changelog,
    consultar_ticket,
    consultar_tickets,
    crear_ticket,
    obtener_articulo,
    obtener_uptime_y_error_budget,
    publicar_articulo,
    publicar_changelog,
    responder_ticket,
)

router = APIRouter(prefix="/support", tags=["soporte"])


def _requiere_alguno_scope(*scopes: str):  # noqa: ANN201 -- fabrica de dependencia FastAPI
    """Variante de `aerohub_contracts.requiere_scope` para el unico
    endpoint de este modulo con audiencia dual (`support:leer` O
    `compliance:leer`, contracts/support-api.md). No vive en
    aerohub_contracts porque es especifica de esta ruta, no un patron
    transversal reutilizado por otros modulos todavia.
    """

    def _verificar(request: Request) -> None:
        scopes_de_la_peticion: frozenset[str] = getattr(request.state, "scopes", frozenset())
        if not any(s in scopes_de_la_peticion for s in scopes):
            raise HTTPException(
                status_code=403, detail=f"scope insuficiente: se requiere uno de {scopes!r}"
            )

    return _verificar


# --- Tickets ---------------------------------------------------------------


class CrearTicketRequest(BaseModel):
    categoria_id: str
    severidad: Literal["baja", "media", "alta", "critica"]
    asunto: str
    cuerpo_inicial: str


class CrearTicketResponse(BaseModel):
    ticket_id: str
    sla_objetivo_min: int


class MensajeResponse(BaseModel):
    id: str
    autor_usuario_id: str
    cuerpo: str
    enviado_en: datetime
    es_interno: bool


class TicketResponse(BaseModel):
    id: str
    tenant_id: str
    categoria_id: str
    creado_por_usuario_id: str
    asignado_a_usuario_id: str | None
    severidad: str
    estado: str
    asunto: str
    creado_en: datetime
    primera_respuesta_en: datetime | None
    resuelto_en: datetime | None
    sla_objetivo_min: int


class TicketDetalleResponse(BaseModel):
    ticket: TicketResponse
    mensajes: list[MensajeResponse]


class ResponderTicketRequest(BaseModel):
    cuerpo: str
    es_interno: bool = False


class ResponderTicketResponse(BaseModel):
    mensaje_id: str


class CambiarEstadoTicketRequest(BaseModel):
    estado: Literal["en_progreso", "esperando_cliente", "resuelto", "cerrado"]


def _ticket_response(t) -> TicketResponse:  # noqa: ANN001 -- TicketTablero de application/
    return TicketResponse(
        id=str(t.id),
        tenant_id=str(t.tenant_id),
        categoria_id=str(t.categoria_id),
        creado_por_usuario_id=str(t.creado_por_usuario_id),
        asignado_a_usuario_id=str(t.asignado_a_usuario_id) if t.asignado_a_usuario_id else None,
        severidad=t.severidad,
        estado=t.estado,
        asunto=t.asunto,
        creado_en=t.creado_en,
        primera_respuesta_en=t.primera_respuesta_en,
        resuelto_en=t.resuelto_en,
        sla_objetivo_min=t.sla_objetivo_min,
    )


class CategoriaTicketResponse(BaseModel):
    id: str
    codigo: str
    nombre: str


@router.get(
    "/catalogo/categorias-ticket",
    response_model=list[CategoriaTicketResponse],
    dependencies=[Depends(requiere_scope("support:leer"))],
)
def listar_categorias_ticket_endpoint() -> list[CategoriaTicketResponse]:
    """Sprint S1.20 -- catalogo global para el select del formulario de
    alta de ticket (antes no existia ningun listado, solo el id se
    conocia via GET/POST de un ticket ya creado)."""
    return [
        CategoriaTicketResponse(id=str(c.id), codigo=c.codigo, nombre=c.nombre)
        for c in consultar_categorias_ticket()
    ]


@router.post(
    "/tickets",
    response_model=CrearTicketResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("support:escribir"))],
)
def crear_ticket_endpoint(cuerpo: CrearTicketRequest) -> CrearTicketResponse:
    try:
        resultado = crear_ticket(
            categoria_id=int(cuerpo.categoria_id),
            severidad=cuerpo.severidad,
            asunto=cuerpo.asunto,
            cuerpo_inicial=cuerpo.cuerpo_inicial,
        )
    except TicketCategoriaNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (TicketUsuarioNoIdentificado, TicketInvalido) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CrearTicketResponse(
        ticket_id=str(resultado.ticket_id), sla_objetivo_min=resultado.sla_objetivo_min
    )


@router.get(
    "/tickets/{ticket_id}",
    response_model=TicketDetalleResponse,
    dependencies=[Depends(requiere_scope("support:leer"))],
)
def obtener_ticket_endpoint(ticket_id: int) -> TicketDetalleResponse:
    try:
        cabecera, mensajes = consultar_ticket(ticket_id=ticket_id)
    except TicketNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return TicketDetalleResponse(
        ticket=_ticket_response(cabecera),
        mensajes=[
            MensajeResponse(
                id=str(m.id),
                autor_usuario_id=str(m.autor_usuario_id),
                cuerpo=m.cuerpo,
                enviado_en=m.enviado_en,
                es_interno=m.es_interno,
            )
            for m in mensajes
        ],
    )


@router.get(
    "/tickets",
    response_model=list[TicketResponse],
    dependencies=[Depends(requiere_scope("support:leer"))],
)
def listar_tickets_endpoint(
    estado: str | None = None, severidad: str | None = None
) -> list[TicketResponse]:
    return [_ticket_response(t) for t in consultar_tickets(estado=estado, severidad=severidad)]


@router.post(
    "/tickets/{ticket_id}/mensajes",
    response_model=ResponderTicketResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("support:escribir"))],
)
def responder_ticket_endpoint(
    ticket_id: int, cuerpo: ResponderTicketRequest
) -> ResponderTicketResponse:
    try:
        resultado = responder_ticket(
            ticket_id=ticket_id, cuerpo=cuerpo.cuerpo, es_interno=cuerpo.es_interno
        )
    except MensajeInternoNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TicketNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TicketInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ResponderTicketResponse(mensaje_id=str(resultado.mensaje_id))


@router.patch(
    "/tickets/{ticket_id}/estado",
    status_code=200,
    dependencies=[Depends(requiere_scope("support:escribir"))],
)
def cambiar_estado_ticket_endpoint(
    ticket_id: int, cuerpo: CambiarEstadoTicketRequest
) -> dict[str, bool]:
    try:
        cambiar_estado_ticket(ticket_id=ticket_id, estado_nuevo=cuerpo.estado)
    except TicketRolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except TicketNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except TransicionInvalida as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True}


# --- Base de conocimientos ---------------------------------------------------


class PublicarArticuloRequest(BaseModel):
    titulo: str
    cuerpo: str
    etiquetas: list[str] = []


class PublicarArticuloResponse(BaseModel):
    articulo_id: str
    version: int


class ArticuloResponse(BaseModel):
    id: str
    titulo: str
    cuerpo: str
    version: int
    publicado_en: datetime | None
    etiquetas: list[str]


def _articulo_response(a) -> ArticuloResponse:  # noqa: ANN001 -- ArticuloKBTablero de application/
    return ArticuloResponse(
        id=str(a.id),
        titulo=a.titulo,
        cuerpo=a.cuerpo,
        version=a.version,
        publicado_en=a.publicado_en,
        etiquetas=a.etiquetas,
    )


@router.post(
    "/kb/articulos",
    response_model=PublicarArticuloResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("support:escribir"))],
)
def publicar_articulo_endpoint(cuerpo: PublicarArticuloRequest) -> PublicarArticuloResponse:
    try:
        resultado = publicar_articulo(
            titulo=cuerpo.titulo, cuerpo=cuerpo.cuerpo, etiquetas=cuerpo.etiquetas
        )
    except KBRolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except (KBUsuarioNoIdentificado, ArticuloKBInvalido) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PublicarArticuloResponse(
        articulo_id=str(resultado.articulo_id), version=resultado.version
    )


@router.get(
    "/kb/articulos",
    response_model=list[ArticuloResponse],
    dependencies=[Depends(requiere_scope("support:leer"))],
)
def buscar_articulos_endpoint(
    q: str | None = None, etiqueta: str | None = None
) -> list[ArticuloResponse]:
    return [_articulo_response(a) for a in buscar_articulos(texto=q, etiqueta=etiqueta)]


@router.get(
    "/kb/articulos/{articulo_id}",
    response_model=ArticuloResponse,
    dependencies=[Depends(requiere_scope("support:leer"))],
)
def obtener_articulo_endpoint(articulo_id: int) -> ArticuloResponse:
    try:
        articulo = obtener_articulo(articulo_id=articulo_id)
    except ArticuloNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _articulo_response(articulo)


# --- Changelog ---------------------------------------------------------------


class ItemChangelogRequest(BaseModel):
    modulo_codigo: str
    tipo_cambio: Literal["nuevo", "mejora", "correccion", "obsolescencia"]
    descripcion: str


class PublicarChangelogRequest(BaseModel):
    version_producto: str
    resumen: str
    items: list[ItemChangelogRequest]


class PublicarChangelogResponse(BaseModel):
    changelog_id: str


class ItemChangelogResponse(BaseModel):
    id: str
    modulo_id: str
    tipo_cambio: str
    descripcion: str


class ChangelogResponse(BaseModel):
    id: str
    version_producto: str
    resumen: str
    publicado_en: datetime
    items: list[ItemChangelogResponse]


@router.post(
    "/changelog",
    response_model=PublicarChangelogResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("support:escribir"))],
)
def publicar_changelog_endpoint(cuerpo: PublicarChangelogRequest) -> PublicarChangelogResponse:
    try:
        resultado = publicar_changelog(
            version_producto=cuerpo.version_producto,
            resumen=cuerpo.resumen,
            items=[
                ItemChangelogEntrada(
                    modulo_codigo=i.modulo_codigo,
                    tipo_cambio=i.tipo_cambio,
                    descripcion=i.descripcion,
                )
                for i in cuerpo.items
            ],
        )
    except ChangelogRolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ModuloNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PublicarChangelogResponse(changelog_id=str(resultado.changelog_id))


@router.get(
    "/changelog",
    response_model=list[ChangelogResponse],
    dependencies=[Depends(requiere_scope("support:leer"))],
)
def listar_changelog_endpoint() -> list[ChangelogResponse]:
    return [
        ChangelogResponse(
            id=str(c.id),
            version_producto=c.version_producto,
            resumen=c.resumen,
            publicado_en=c.publicado_en,
            items=[
                ItemChangelogResponse(
                    id=str(i.id),
                    modulo_id=str(i.modulo_id),
                    tipo_cambio=i.tipo_cambio,
                    descripcion=i.descripcion,
                )
                for i in c.items
            ],
        )
        for c in consultar_changelog()
    ]


# --- Observabilidad ------------------------------------------------------


class ObservabilidadUptimeResponse(BaseModel):
    servicio: str
    uptime_pct: float
    error_budget_consumido_pct: float


@router.get(
    "/observabilidad/uptime",
    response_model=ObservabilidadUptimeResponse,
    dependencies=[Depends(_requiere_alguno_scope("support:leer", "compliance:leer"))],
)
def obtener_uptime_endpoint(servicio: Literal["aodb", "fids"]) -> ObservabilidadUptimeResponse:
    try:
        resultado = obtener_uptime_y_error_budget(servicio)
    except ObservabilidadServicioInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ObservabilidadUptimeResponse(
        servicio=resultado.servicio,
        uptime_pct=resultado.uptime_pct,
        error_budget_consumido_pct=resultado.error_budget_consumido_pct,
    )
