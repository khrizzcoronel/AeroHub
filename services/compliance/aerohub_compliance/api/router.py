"""Endpoints HTTP de aerohub_compliance (Sprint S1.7, Plan Sec8.7,
RF-O13, RF-T11, RNF-S04; CU-O13).

Solo traduce HTTP <-> application/: valida forma con Pydantic, invoca el
caso de uso, traduce sus excepciones a codigos de estado. Ninguna regla de
negocio vive aqui (SRS Sec6.4).
"""

from __future__ import annotations

from datetime import date, datetime

from aerohub_contracts import requiere_scope
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..application import (
    AccesoAuditorUsuarioNoIdentificado,
    AccionNoEncontrada,
    ConsultarPostMortemNoEncontrado,
    IncidenteUsuarioNoIdentificado,
    PostMortemNoEncontrado,
    RemediacionIncompleta,
    ReporteUsuarioNoIdentificado,
    RolNoAutorizado,
    TipoIncidenteNoEncontrado,
    VentanaInvalida,
    agregar_accion,
    completar_accion,
    consultar_incidentes,
    consultar_post_mortem,
    crear_incidente,
    crear_post_mortem,
    editar_causa_raiz,
    otorgar_acceso_auditor,
    publicar_post_mortem,
    registrar_evidencia_soc2,
    registrar_reporte_dgac,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


class CrearIncidenteRequest(BaseModel):
    tipo_incidente_id: str
    descripcion: str
    severidad: str
    detectado_en: datetime


class CrearIncidenteResponse(BaseModel):
    incidente_id: str


class IncidenteResponse(BaseModel):
    id: str
    tipo_incidente_id: str
    descripcion: str
    severidad: str
    detectado_en: datetime
    estado: str


class CrearPostMortemRequest(BaseModel):
    incidente_ref: str
    severidad: str
    iniciado_en: datetime


class CrearPostMortemResponse(BaseModel):
    post_mortem_id: str


class EditarCausaRaizRequest(BaseModel):
    causa_raiz: str


class AgregarAccionRequest(BaseModel):
    descripcion: str
    responsable_usuario_id: str
    vence_en: datetime
    ticket_ref: str | None = None


class AgregarAccionResponse(BaseModel):
    accion_id: str


class AccionResponse(BaseModel):
    id: str
    descripcion: str
    responsable_usuario_id: str
    estado: str
    vence_en: datetime
    ticket_ref: str | None
    completada_en: datetime | None


class PostMortemResponse(BaseModel):
    id: str
    incidente_ref: str
    severidad: str
    estado: str
    iniciado_en: datetime
    causa_raiz: str | None
    publicado_en: datetime | None
    tiempo_resolucion_min: int | None


class PostMortemDetalleResponse(BaseModel):
    post_mortem: PostMortemResponse
    acciones: list[AccionResponse]


class RegistrarReporteRequest(BaseModel):
    tipo_reporte_id: str
    periodo_inicio: date
    periodo_fin: date
    contenido_ref: str
    hash_contenido: str


class RegistrarReporteResponse(BaseModel):
    reporte_id: str


class OtorgarAccesoAuditorRequest(BaseModel):
    auditor_usuario_id: str
    inicio: datetime
    fin: datetime
    alcance_json: dict
    motivo: str


class OtorgarAccesoAuditorResponse(BaseModel):
    acceso_id: str


class RegistrarEvidenciaRequest(BaseModel):
    control_soc2_id: str
    periodo_inicio: date
    periodo_fin: date
    ruta_artefacto: str
    hash_artefacto: str
    referencia_log_id: str | None = None


class RegistrarEvidenciaResponse(BaseModel):
    evidencia_id: str


@router.post(
    "/incidentes",
    response_model=CrearIncidenteResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def crear_incidente_endpoint(cuerpo: CrearIncidenteRequest) -> CrearIncidenteResponse:
    try:
        resultado = crear_incidente(
            tipo_incidente_id=int(cuerpo.tipo_incidente_id),
            descripcion=cuerpo.descripcion,
            severidad=cuerpo.severidad,
            detectado_en=cuerpo.detectado_en,
        )
    except TipoIncidenteNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except IncidenteUsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return CrearIncidenteResponse(incidente_id=str(resultado.incidente_id))


@router.get(
    "/incidentes",
    response_model=list[IncidenteResponse],
    dependencies=[Depends(requiere_scope("compliance:leer"))],
)
def listar_incidentes_endpoint() -> list[IncidenteResponse]:
    return [
        IncidenteResponse(
            id=str(i.id),
            tipo_incidente_id=str(i.tipo_incidente_id),
            descripcion=i.descripcion,
            severidad=i.severidad,
            detectado_en=i.detectado_en,
            estado=i.estado,
        )
        for i in consultar_incidentes()
    ]


@router.post(
    "/post-mortems",
    response_model=CrearPostMortemResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def crear_post_mortem_endpoint(cuerpo: CrearPostMortemRequest) -> CrearPostMortemResponse:
    """CU-O13 -- exclusivo role_sre (ADR-009)."""
    try:
        resultado = crear_post_mortem(
            incidente_ref=cuerpo.incidente_ref,
            severidad=cuerpo.severidad,
            iniciado_en=cuerpo.iniciado_en,
        )
    except RolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return CrearPostMortemResponse(post_mortem_id=str(resultado.post_mortem_id))


@router.patch(
    "/post-mortems/{post_mortem_id}",
    status_code=200,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def editar_causa_raiz_endpoint(
    post_mortem_id: int, cuerpo: EditarCausaRaizRequest
) -> dict[str, bool]:
    try:
        editar_causa_raiz(post_mortem_id=post_mortem_id, causa_raiz=cuerpo.causa_raiz)
    except RolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except PostMortemNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post(
    "/post-mortems/{post_mortem_id}/acciones",
    response_model=AgregarAccionResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def agregar_accion_endpoint(
    post_mortem_id: int, cuerpo: AgregarAccionRequest
) -> AgregarAccionResponse:
    try:
        resultado = agregar_accion(
            post_mortem_id=post_mortem_id,
            descripcion=cuerpo.descripcion,
            responsable_usuario_id=int(cuerpo.responsable_usuario_id),
            vence_en=cuerpo.vence_en,
            ticket_ref=cuerpo.ticket_ref,
        )
    except RolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except PostMortemNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AgregarAccionResponse(accion_id=str(resultado.accion_id))


@router.post(
    "/post-mortems/{post_mortem_id}/acciones/{accion_id}/completar",
    status_code=200,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def completar_accion_endpoint(post_mortem_id: int, accion_id: int) -> dict[str, bool]:
    try:
        completar_accion(accion_id=accion_id)
    except RolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except AccionNoEncontrada as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"ok": True}


@router.post(
    "/post-mortems/{post_mortem_id}/publicar",
    status_code=200,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def publicar_post_mortem_endpoint(post_mortem_id: int) -> dict[str, bool]:
    """FR-005: 409 si alguna accion de remediacion no esta completada."""
    try:
        publicar_post_mortem(post_mortem_id=post_mortem_id)
    except RolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except PostMortemNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RemediacionIncompleta as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {"ok": True}


@router.get(
    "/post-mortems/{post_mortem_id}",
    response_model=PostMortemDetalleResponse,
    dependencies=[Depends(requiere_scope("compliance:leer"))],
)
def obtener_post_mortem_endpoint(post_mortem_id: int) -> PostMortemDetalleResponse:
    try:
        cabecera, acciones = consultar_post_mortem(post_mortem_id=post_mortem_id)
    except ConsultarPostMortemNoEncontrado as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return PostMortemDetalleResponse(
        post_mortem=PostMortemResponse(
            id=str(cabecera.id),
            incidente_ref=cabecera.incidente_ref,
            severidad=cabecera.severidad,
            estado=cabecera.estado,
            iniciado_en=cabecera.iniciado_en,
            causa_raiz=cabecera.causa_raiz,
            publicado_en=cabecera.publicado_en,
            tiempo_resolucion_min=cabecera.tiempo_resolucion_min,
        ),
        acciones=[
            AccionResponse(
                id=str(a.id),
                descripcion=a.descripcion,
                responsable_usuario_id=str(a.responsable_usuario_id),
                estado=a.estado,
                vence_en=a.vence_en,
                ticket_ref=a.ticket_ref,
                completada_en=a.completada_en,
            )
            for a in acciones
        ],
    )


@router.post(
    "/reportes-dgac",
    response_model=RegistrarReporteResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def registrar_reporte_endpoint(cuerpo: RegistrarReporteRequest) -> RegistrarReporteResponse:
    try:
        resultado = registrar_reporte_dgac(
            tipo_reporte_id=int(cuerpo.tipo_reporte_id),
            periodo_inicio=cuerpo.periodo_inicio,
            periodo_fin=cuerpo.periodo_fin,
            contenido_ref=cuerpo.contenido_ref,
            hash_contenido=cuerpo.hash_contenido,
        )
    except ReporteUsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RegistrarReporteResponse(reporte_id=str(resultado.reporte_id))


@router.post(
    "/accesos-auditor",
    response_model=OtorgarAccesoAuditorResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def otorgar_acceso_auditor_endpoint(
    cuerpo: OtorgarAccesoAuditorRequest,
) -> OtorgarAccesoAuditorResponse:
    try:
        resultado = otorgar_acceso_auditor(
            auditor_usuario_id=int(cuerpo.auditor_usuario_id),
            inicio=cuerpo.inicio,
            fin=cuerpo.fin,
            alcance_json=cuerpo.alcance_json,
            motivo=cuerpo.motivo,
        )
    except AccesoAuditorUsuarioNoIdentificado as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except VentanaInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return OtorgarAccesoAuditorResponse(acceso_id=str(resultado.acceso_id))


@router.post(
    "/evidencia-soc2",
    response_model=RegistrarEvidenciaResponse,
    status_code=201,
    dependencies=[Depends(requiere_scope("compliance:escribir"))],
)
def registrar_evidencia_endpoint(cuerpo: RegistrarEvidenciaRequest) -> RegistrarEvidenciaResponse:
    resultado = registrar_evidencia_soc2(
        control_soc2_id=int(cuerpo.control_soc2_id),
        periodo_inicio=cuerpo.periodo_inicio,
        periodo_fin=cuerpo.periodo_fin,
        ruta_artefacto=cuerpo.ruta_artefacto,
        hash_artefacto=cuerpo.hash_artefacto,
        referencia_log_id=int(cuerpo.referencia_log_id) if cuerpo.referencia_log_id else None,
    )
    return RegistrarEvidenciaResponse(evidencia_id=str(resultado.evidencia_id))
