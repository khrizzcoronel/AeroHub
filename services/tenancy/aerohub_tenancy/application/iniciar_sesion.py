"""CU-IA01 -- Iniciar sesion con credenciales propias (Sprint S1.10,
spec.md US1, FR-001..FR-004, FR-014, research.md Decision 3).

Corre bajo `alcance_global()`: en el login todavia no se sabe a que
tenant pertenece quien intenta entrar -- exactamente el mismo problema
que `verificar_api_key` (S1.2) ya resuelve con el mismo mecanismo.

Nunca distingue en la respuesta si fallo el correo o la contrasena (ni la
cuenta bloqueada, ni la inactiva, ni la falta de rol vigente) -- todos los
casos de fallo lanzan la misma excepcion `CredencialesInvalidas`; el
motivo real queda en `tenants.intento_acceso.resultado`, nunca expuesto al
llamador HTTP (contracts/auth-api.md).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from aerohub_contracts import scopes_del_rol
from aerohub_kernel import ahora_utc, generar_id
from aerohub_kernel import verificar_credencial as _verificar_credencial
from sqlalchemy.engine import Connection

from ..domain import RolVigenteInconsistente, resolver_rol_vigente
from ..infrastructure import (
    actualizar_ultimo_acceso,
    alcance_global,
    contar_intentos_fallidos_recientes,
    escribir_journal,
    fijar_bloqueo,
    insertar_intento_acceso,
    insertar_sesion,
    listar_roles_vigentes_del_usuario,
    obtener_usuario_por_email,
    registrar_auditoria,
    reintentar_en_conflicto,
    sesion,
)

_MOTIVO_ALCANCE_GLOBAL = "autenticacion_login"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"
_MAX_INTENTOS_FALLIDOS = 5
_VENTANA_BLOQUEO = timedelta(minutes=15)
_VENTANA_CONTEO = timedelta(minutes=15)
_MINUTOS_EXPIRACION_SESION = 15


class CredencialesInvalidas(Exception):
    """Correo inexistente, contrasena incorrecta, cuenta inactiva,
    bloqueada o sin rol vigente -- deliberadamente sin distinguir cual."""


@dataclass(frozen=True, slots=True)
class ResultadoLogin:
    sesion_id: int
    usuario_id: int
    tenant_id: int | None
    rol_codigo: str
    scopes: frozenset[str]
    debe_cambiar_password: bool
    expira_en_minutos: int


@reintentar_en_conflicto()
def iniciar_sesion(*, email: str, password: str, ip_origen: str | None = None) -> ResultadoLogin:
    """`sesion()` revierte TODA la transaccion si una excepcion escapa del
    bloque (P8, ver su propio docstring) -- incluida la fila de
    `intento_acceso` que un intento fallido necesita dejar escrita para
    auditoria y para el conteo de bloqueo por fuerza bruta. Por eso el
    cuerpo captura `CredencialesInvalidas` DENTRO del `with` (para que la
    transaccion cierre en commit con el intento ya escrito) y recien la
    relanza DESPUES de que el bloque terminó -- un bug real encontrado por
    verificacion empirica (Principio III): sin esto, ningun intento
    fallido quedaba nunca en `tenants.intento_acceso`, y el bloqueo tras
    N fallos nunca se disparaba.
    """
    ahora = ahora_utc()
    resultado: ResultadoLogin | None = None
    fallo: CredencialesInvalidas | None = None
    with (
        alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA),
        sesion() as conn,
    ):
        try:
            resultado = _intentar_login(
                conn, email=email, password=password, ip_origen=ip_origen, ahora=ahora
            )
        except CredencialesInvalidas as exc:
            fallo = exc

    if fallo is not None:
        raise fallo
    assert resultado is not None
    return resultado


def _intentar_login(
    conn: Connection, *, email: str, password: str, ip_origen: str | None, ahora: datetime
) -> ResultadoLogin:
    fila_usuario = obtener_usuario_por_email(conn, email)

    if fila_usuario is None:
        insertar_intento_acceso(
            conn,
            id=generar_id(),
            email_intentado=email,
            usuario_id=None,
            resultado="credencial_invalida",
            ip_origen=ip_origen,
        )
        raise CredencialesInvalidas("correo o contrasena incorrectos")

    usuario_id = fila_usuario.id

    if fila_usuario.bloqueado_hasta is not None and ahora < fila_usuario.bloqueado_hasta:
        insertar_intento_acceso(
            conn,
            id=generar_id(),
            email_intentado=email,
            usuario_id=usuario_id,
            resultado="cuenta_bloqueada",
            ip_origen=ip_origen,
        )
        raise CredencialesInvalidas("correo o contrasena incorrectos")

    if fila_usuario.estado != "activo":
        insertar_intento_acceso(
            conn,
            id=generar_id(),
            email_intentado=email,
            usuario_id=usuario_id,
            resultado="cuenta_inactiva",
            ip_origen=ip_origen,
        )
        raise CredencialesInvalidas("correo o contrasena incorrectos")

    credencial_valida = _verificar_credencial(password, fila_usuario.hash_credencial)
    if not credencial_valida:
        insertar_intento_acceso(
            conn,
            id=generar_id(),
            email_intentado=email,
            usuario_id=usuario_id,
            resultado="credencial_invalida",
            ip_origen=ip_origen,
        )
        fallos = contar_intentos_fallidos_recientes(conn, usuario_id, desde=ahora - _VENTANA_CONTEO)
        if fallos >= _MAX_INTENTOS_FALLIDOS:
            fijar_bloqueo(conn, usuario_id=usuario_id, bloqueado_hasta=ahora + _VENTANA_BLOQUEO)
        raise CredencialesInvalidas("correo o contrasena incorrectos")

    try:
        rol_vigente = resolver_rol_vigente(
            listar_roles_vigentes_del_usuario(conn, usuario_id), ahora=ahora
        )
    except RolVigenteInconsistente:
        insertar_intento_acceso(
            conn,
            id=generar_id(),
            email_intentado=email,
            usuario_id=usuario_id,
            resultado="sin_rol_vigente",
            ip_origen=ip_origen,
        )
        raise CredencialesInvalidas("correo o contrasena incorrectos") from None

    if rol_vigente is None:
        insertar_intento_acceso(
            conn,
            id=generar_id(),
            email_intentado=email,
            usuario_id=usuario_id,
            resultado="sin_rol_vigente",
            ip_origen=ip_origen,
        )
        raise CredencialesInvalidas("correo o contrasena incorrectos")

    sesion_id = generar_id()
    expira_en = ahora + timedelta(minutes=_MINUTOS_EXPIRACION_SESION)
    insertar_sesion(
        conn, id=sesion_id, usuario_id=usuario_id, expira_en=expira_en, ip_origen=ip_origen
    )
    escribir_journal(
        conn,
        esquema="tenants",
        tabla="sesion",
        operacion="INSERT",
        clave_primaria={"id": sesion_id},
        payload={"id": sesion_id, "usuario_id": usuario_id},
        tenant_id=fila_usuario.tenant_id,
    )
    actualizar_ultimo_acceso(conn, usuario_id=usuario_id, momento=ahora)
    insertar_intento_acceso(
        conn,
        id=generar_id(),
        email_intentado=email,
        usuario_id=usuario_id,
        resultado="exitoso",
        ip_origen=ip_origen,
    )
    registrar_auditoria(
        conn,
        esquema="tenants",
        tabla="sesion",
        registro_id=sesion_id,
        operacion="INSERT",
        valores_nuevos={"usuario_id": usuario_id},
        tenant_id=fila_usuario.tenant_id,
    )

    return ResultadoLogin(
        sesion_id=sesion_id,
        usuario_id=usuario_id,
        tenant_id=fila_usuario.tenant_id,
        rol_codigo=rol_vigente.codigo,
        scopes=scopes_del_rol(rol_vigente.codigo),
        debe_cambiar_password=fila_usuario.debe_cambiar_password,
        expira_en_minutos=_MINUTOS_EXPIRACION_SESION,
    )
