"""CU-IA02 -- Perfil de acceso: `GET /auth/yo` (Sprint S1.10, spec.md US2,
FR-009..FR-011, contracts/perfil-acceso.md).

Es la unica fuente desde la que el frontend construye su menu -- el
calculo de modulos visibles vive aqui, no duplicado en Angular
(research.md Decision 4).
"""

from __future__ import annotations

from dataclasses import dataclass

from aerohub_contracts import MODULOS, Modulo, modulos_del_rol, scopes_del_rol
from aerohub_kernel import ahora_utc

from ..infrastructure import (
    ContextoTenantAusente,
    alcance_global,
    contexto_rol_actor,
    contexto_tenant_id,
    contexto_usuario_id,
    existe_licencia_vigente,
    obtener_rol_por_codigo,
    obtener_tenant_por_id_global,
    obtener_usuario_por_id_global,
    sesion,
)

_MOTIVO_ALCANCE_GLOBAL = "consulta_perfil_acceso"
_ROL_PARA_LA_CONSULTA = "role_platform_admin"


class UsuarioNoEncontrado(Exception):
    """`usuario_id` proviene de un JWT ya validado -- llegar aqui sin fila
    es un estado inconsistente (usuario borrado con sesiones/tokens
    todavia vigentes), nunca una entrada de cliente; se reporta en vez de
    asumir silenciosamente que no puede pasar."""


@dataclass(frozen=True, slots=True)
class PerfilAcceso:
    usuario_id: int
    email: str
    nombre: str
    email_verificado: bool
    debe_cambiar_password: bool
    tenant_id: int | None
    tenant_codigo: str | None
    tenant_razon_social: str | None
    rol_codigo: str
    rol_nombre: str
    scopes: frozenset[str]
    modulos_visibles: list[Modulo]


def consultar_mi_perfil() -> PerfilAcceso:
    """Lee el contexto poblado por el middleware del Gateway y arma el
    perfil de quien esta haciendo la peticion -- version sin argumentos de
    `consultar_perfil`, para que `api/router_auth.py` (`GET /auth/yo`) no
    tenga que leer `aerohub_repository.contexto` directamente (ADR-017
    regla 3: api solo importa application)."""
    rol_codigo = contexto_rol_actor()
    try:
        tenant_id = contexto_tenant_id()
    except ContextoTenantAusente:
        tenant_id = None
    usuario_id = contexto_usuario_id()
    if usuario_id is None:
        # API Key (S1.2) no tiene usuario propio -- /auth/yo es un
        # concepto de sesion humana, no aplica a una identidad de API Key.
        raise UsuarioNoEncontrado("la identidad autenticada no tiene un usuario asociado")
    return consultar_perfil(
        usuario_id=usuario_id,
        tenant_id=tenant_id,
        rol_codigo=rol_codigo,
        scopes=scopes_del_rol(rol_codigo),
    )


def consultar_perfil(
    *, usuario_id: int, tenant_id: int | None, rol_codigo: str, scopes: frozenset[str]
) -> PerfilAcceso:
    """Corre siempre bajo `alcance_global()` y con los getters GLOBALES
    (`obtener_usuario_por_id_global`, no el tenant-scoped
    `obtener_usuario_por_id`) -- se invoca desde dos sitios con contexto
    de peticion distinto: `POST /auth/login` (todavia SIN JWT, sin
    contexto de tenant/rol poblado por el middleware) y `GET /auth/yo`
    (YA autenticado). Usar el mismo camino para ambos evita una rama que
    solo se ejercita desde uno de los dos llamadores."""
    ahora = ahora_utc()

    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL_PARA_LA_CONSULTA), sesion() as conn:
        fila_usuario = obtener_usuario_por_id_global(conn, usuario_id)
        if fila_usuario is None:
            raise UsuarioNoEncontrado(f"usuario {usuario_id} no encontrado")
        fila_rol = obtener_rol_por_codigo(conn, rol_codigo)
        rol_nombre = fila_rol.nombre if fila_rol else rol_codigo

        if tenant_id is None:
            fila_tenant = None
            modulos_visibles = [MODULOS[codigo] for codigo in sorted(modulos_del_rol(rol_codigo))]
        else:
            fila_tenant = obtener_tenant_por_id_global(conn, tenant_id)
            modulos_visibles = [
                MODULOS[codigo]
                for codigo in sorted(modulos_del_rol(rol_codigo))
                if existe_licencia_vigente(
                    conn, tenant_id=tenant_id, modulo_codigo=codigo, ahora=ahora
                )
            ]

    return PerfilAcceso(
        usuario_id=usuario_id,
        email=fila_usuario.email,
        nombre=fila_usuario.nombre,
        email_verificado=fila_usuario.email_verificado_en is not None,
        debe_cambiar_password=fila_usuario.debe_cambiar_password,
        tenant_id=tenant_id,
        tenant_codigo=fila_tenant.codigo if fila_tenant else None,
        tenant_razon_social=fila_tenant.razon_social if fila_tenant else None,
        rol_codigo=rol_codigo,
        rol_nombre=rol_nombre,
        scopes=scopes,
        modulos_visibles=modulos_visibles,
    )
