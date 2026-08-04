"""Endpoints de identidad y acceso (Sprint S1.10,
specs/012-identidad-y-acceso/contracts/auth-api.md).

Solo traduce HTTP <-> application/, igual que router.py. Las rutas
publicas (`/auth/login`, `/auth/recuperar`, `/auth/restablecer`,
`/auth/verificar-correo`, `/usuarios/aceptar-invitacion`) estan en
`RUTAS_EXENTAS` del middleware del gateway -- por definicion no exigen
JWT previo (FR-026).
"""

from __future__ import annotations

from aerohub_contracts import EnvioDeCorreoFallo, emitir_jwt_sesion, requiere_scope, sesion_id_de_jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..application import (
    CorreoYaRegistrado,
    CredencialesInvalidas,
    InvitacionRolNoAutorizado,
    InvitacionTokenInvalido,
    PasswordActualIncorrecta,
    RecuperacionTokenInvalido,
    RolDestinoInvalido,
    UsuarioDelTenantNoEncontrado,
    VerificacionTokenInvalido,
    aceptar_invitacion,
    actualizar_rol_usuario,
    cambiar_estado_usuario,
    cambiar_password,
    cerrar_sesion,
    consultar_mi_perfil,
    consultar_perfil,
    consultar_usuarios_del_tenant,
    iniciar_sesion,
    invitar_usuario,
    obtener_usuario_del_tenant,
    restablecer_password,
    solicitar_recuperacion,
    solicitar_verificacion,
    verificar_correo,
)
from ..domain import ESTADOS_VALIDOS_USUARIO, PasswordInvalida, TransicionUsuarioInvalida

router_auth = APIRouter(tags=["auth"])


def _sesion_id_del_encabezado(request: Request) -> int | None:
    encabezado = request.headers.get("authorization", "")
    if not encabezado.startswith("Bearer "):
        return None
    return sesion_id_de_jwt(encabezado.removeprefix("Bearer ").strip())


class LoginRequest(BaseModel):
    email: str
    password: str


class ModuloVisibleResponse(BaseModel):
    codigo: str
    nombre: str
    ruta: str | None


class PerfilResponse(BaseModel):
    usuario_id: str
    email: str
    nombre: str
    email_verificado: bool
    debe_cambiar_password: bool
    tenant_id: str | None
    tenant_codigo: str | None
    tenant_razon_social: str | None
    rol_codigo: str
    rol_nombre: str
    scopes: list[str]
    modulos_visibles: list[ModuloVisibleResponse]


class LoginResponse(BaseModel):
    token: str
    expira_en_minutos: int
    perfil: PerfilResponse


def _perfil_a_response(perfil) -> PerfilResponse:  # noqa: ANN001 -- PerfilAcceso, evita import ciclico de tipo
    return PerfilResponse(
        usuario_id=str(perfil.usuario_id),
        email=perfil.email,
        nombre=perfil.nombre,
        email_verificado=perfil.email_verificado,
        debe_cambiar_password=perfil.debe_cambiar_password,
        tenant_id=str(perfil.tenant_id) if perfil.tenant_id is not None else None,
        tenant_codigo=perfil.tenant_codigo,
        tenant_razon_social=perfil.tenant_razon_social,
        rol_codigo=perfil.rol_codigo,
        rol_nombre=perfil.rol_nombre,
        scopes=sorted(perfil.scopes),
        modulos_visibles=[
            ModuloVisibleResponse(codigo=m.codigo, nombre=m.nombre, ruta=m.ruta)
            for m in perfil.modulos_visibles
        ],
    )


@router_auth.post("/auth/login", response_model=LoginResponse)
def login(cuerpo: LoginRequest, request: Request) -> LoginResponse:
    """FR-001..FR-004: nunca distingue en la respuesta si fallo el correo
    o la contrasena -- un solo 401 para todos los casos de credencial
    invalida, cuenta inactiva, bloqueada o sin rol vigente."""
    try:
        resultado = iniciar_sesion(
            email=cuerpo.email,
            password=cuerpo.password,
            ip_origen=request.client.host if request.client else None,
        )
    except CredencialesInvalidas as exc:
        raise HTTPException(status_code=401, detail="correo o contrasena incorrectos") from exc

    token = emitir_jwt_sesion(
        rol=resultado.rol_codigo,
        tenant_id=resultado.tenant_id,
        usuario_id=resultado.usuario_id,
        scopes=resultado.scopes,
        sesion_id=resultado.sesion_id,
        minutos_expiracion=resultado.expira_en_minutos,
    )
    perfil = consultar_perfil(
        usuario_id=resultado.usuario_id,
        tenant_id=resultado.tenant_id,
        rol_codigo=resultado.rol_codigo,
        scopes=resultado.scopes,
    )
    return LoginResponse(
        token=token,
        expira_en_minutos=resultado.expira_en_minutos,
        perfil=_perfil_a_response(perfil),
    )


@router_auth.get("/auth/yo", response_model=PerfilResponse)
def obtener_mi_perfil() -> PerfilResponse:
    return _perfil_a_response(consultar_mi_perfil())


@router_auth.post("/auth/logout", status_code=200)
def logout(request: Request) -> dict[str, str]:
    sesion_id = _sesion_id_del_encabezado(request)
    if sesion_id is not None:
        cerrar_sesion(sesion_id=sesion_id)
    return {"estado": "sesion_cerrada"}


class CambiarPasswordRequest(BaseModel):
    password_actual: str
    password_nueva: str


@router_auth.post("/auth/cambiar-password", status_code=200)
def cambiar_mi_password(cuerpo: CambiarPasswordRequest, request: Request) -> dict[str, str]:
    try:
        cambiar_password(
            sesion_id_actual=_sesion_id_del_encabezado(request),
            password_actual=cuerpo.password_actual,
            password_nueva=cuerpo.password_nueva,
        )
    except PasswordActualIncorrecta as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except PasswordInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"estado": "password_cambiada"}


class RecuperarRequest(BaseModel):
    email: str


@router_auth.post("/auth/recuperar", status_code=202)
def recuperar_password(cuerpo: RecuperarRequest) -> dict[str, str]:
    """FR-021: SIEMPRE 202, exista o no la cuenta -- no se puede usar
    para descubrir que correos estan registrados."""
    solicitar_recuperacion(email=cuerpo.email)
    return {"estado": "solicitud_recibida"}


class RestablecerRequest(BaseModel):
    token: str
    password_nueva: str


@router_auth.post("/auth/restablecer", status_code=200)
def restablecer_mi_password(cuerpo: RestablecerRequest) -> dict[str, str]:
    try:
        restablecer_password(token=cuerpo.token, password_nueva=cuerpo.password_nueva)
    except RecuperacionTokenInvalido as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except PasswordInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"estado": "password_restablecida"}


class VerificarCorreoRequest(BaseModel):
    token: str


@router_auth.post("/auth/verificar-correo", status_code=200)
def verificar_mi_correo(cuerpo: VerificarCorreoRequest) -> dict[str, str]:
    try:
        verificar_correo(token=cuerpo.token)
    except VerificacionTokenInvalido as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    return {"estado": "correo_verificado"}


@router_auth.post("/auth/solicitar-verificacion", status_code=202)
def pedir_verificacion_de_correo() -> dict[str, str]:
    solicitar_verificacion()
    return {"estado": "verificacion_solicitada"}


class InvitarRequest(BaseModel):
    email: str
    rol_codigo: str


class InvitarResponse(BaseModel):
    invitacion_id: str
    expira_en: str


@router_auth.post("/usuarios/invitaciones", response_model=InvitarResponse, status_code=201)
def invitar(cuerpo: InvitarRequest) -> InvitarResponse:
    try:
        resultado = invitar_usuario(email=cuerpo.email, rol_codigo=cuerpo.rol_codigo)
    except InvitacionRolNoAutorizado as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except CorreoYaRegistrado as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RolDestinoInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except EnvioDeCorreoFallo as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return InvitarResponse(
        invitacion_id=str(resultado.invitacion_id), expira_en=resultado.expira_en.isoformat()
    )


class AceptarInvitacionRequest(BaseModel):
    token: str
    nombre: str
    password: str


class AceptarInvitacionResponse(BaseModel):
    usuario_id: str
    tenant_id: str


@router_auth.post(
    "/usuarios/aceptar-invitacion", response_model=AceptarInvitacionResponse, status_code=201
)
def aceptar(cuerpo: AceptarInvitacionRequest) -> AceptarInvitacionResponse:
    try:
        resultado = aceptar_invitacion(
            token=cuerpo.token, nombre=cuerpo.nombre, password=cuerpo.password
        )
    except InvitacionTokenInvalido as exc:
        raise HTTPException(status_code=410, detail=str(exc)) from exc
    except PasswordInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AceptarInvitacionResponse(
        usuario_id=str(resultado.usuario_id), tenant_id=str(resultado.tenant_id)
    )


class UsuarioResumenResponse(BaseModel):
    id: str
    email: str
    nombre: str
    estado: str
    creado_en: str
    ultimo_acceso_en: str | None
    rol_codigo: str | None
    rol_nombre: str | None


@router_auth.get(
    "/usuarios",
    response_model=list[UsuarioResumenResponse],
    dependencies=[Depends(requiere_scope("usuarios:administrar"))],
)
def listar_usuarios() -> list[UsuarioResumenResponse]:
    usuarios = consultar_usuarios_del_tenant()
    return [
        UsuarioResumenResponse(
            id=u.id,
            email=u.email,
            nombre=u.nombre,
            estado=u.estado,
            creado_en=u.creado_en.isoformat(),
            ultimo_acceso_en=u.ultimo_acceso_en.isoformat() if u.ultimo_acceso_en else None,
            rol_codigo=u.rol_codigo,
            rol_nombre=u.rol_nombre,
        )
        for u in usuarios
    ]


class UsuarioDetalleResponse(BaseModel):
    id: str
    email: str
    nombre: str
    estado: str
    rol_codigo: str | None
    rol_nombre: str | None


def _detalle_a_response(d) -> UsuarioDetalleResponse:  # noqa: ANN001
    return UsuarioDetalleResponse(
        id=str(d.id),
        email=d.email,
        nombre=d.nombre,
        estado=d.estado,
        rol_codigo=d.rol_codigo,
        rol_nombre=d.rol_nombre,
    )


@router_auth.get(
    "/usuarios/{usuario_id}",
    response_model=UsuarioDetalleResponse,
    dependencies=[Depends(requiere_scope("usuarios:administrar"))],
)
def obtener_usuario_endpoint(usuario_id: int) -> UsuarioDetalleResponse:
    try:
        return _detalle_a_response(obtener_usuario_del_tenant(usuario_id))
    except UsuarioDelTenantNoEncontrado as exc:
        # PN-01: 404, nunca 403 -- no confirmar que el usuario ajeno existe.
        raise HTTPException(status_code=404, detail="usuario no encontrado") from exc


class UsuarioActualizarRolRequest(BaseModel):
    rol_codigo: str


@router_auth.patch(
    "/usuarios/{usuario_id}",
    response_model=UsuarioDetalleResponse,
    dependencies=[Depends(requiere_scope("usuarios:administrar"))],
)
def actualizar_usuario_endpoint(
    usuario_id: int, cuerpo: UsuarioActualizarRolRequest
) -> UsuarioDetalleResponse:
    try:
        resultado = actualizar_rol_usuario(usuario_id=usuario_id, rol_codigo=cuerpo.rol_codigo)
    except UsuarioDelTenantNoEncontrado as exc:
        raise HTTPException(status_code=404, detail="usuario no encontrado") from exc
    except RolDestinoInvalido as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _detalle_a_response(resultado)


class UsuarioCambiarEstadoRequest(BaseModel):
    estado_nuevo: str = Field(description=f"uno de: {', '.join(ESTADOS_VALIDOS_USUARIO)}")


@router_auth.post(
    "/usuarios/{usuario_id}/estado",
    response_model=UsuarioDetalleResponse,
    dependencies=[Depends(requiere_scope("usuarios:administrar"))],
)
def cambiar_estado_usuario_endpoint(
    usuario_id: int, cuerpo: UsuarioCambiarEstadoRequest
) -> UsuarioDetalleResponse:
    try:
        resultado = cambiar_estado_usuario(usuario_id=usuario_id, estado_nuevo=cuerpo.estado_nuevo)
    except UsuarioDelTenantNoEncontrado as exc:
        raise HTTPException(status_code=404, detail="usuario no encontrado") from exc
    except TransicionUsuarioInvalida as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _detalle_a_response(resultado)
