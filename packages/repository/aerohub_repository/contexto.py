"""Contexto de tenant de la peticion en curso (ADR-014 control compensatorio 2;
ADR-019 G3).

El `tenant_id` nunca se acepta desde el cuerpo de la peticion: el middleware
de `services/gateway` es el unico que puebla este `ContextVar`, y lo hace a
partir del JWT ya validado. Todo repositorio de alcance tenant lee de aqui,
nunca de un parametro que el llamador pueda inventar.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass

_tenant_id: ContextVar[int | None] = ContextVar("aerohub_tenant_id", default=None)
_rol_actor: ContextVar[str | None] = ContextVar("aerohub_rol_actor", default=None)
_usuario_id: ContextVar[int | None] = ContextVar("aerohub_usuario_id", default=None)
_aerolinea_id: ContextVar[int | None] = ContextVar("aerohub_aerolinea_id", default=None)
_alcance_global_activo: ContextVar[AlcanceGlobalInfo | None] = ContextVar(
    "aerohub_alcance_global", default=None
)


class ContextoTenantAusente(Exception):
    """Se intento leer el tenant_id de la peticion fuera de un contexto que lo define.

    No es la excepcion que lanza el guardian ante una consulta sin filtro
    (esa es TenantScopeViolation, packages/repository/guard.py, S0.2). Esta
    excepcion es mas basica: protege contra el error de programacion de leer
    el contexto antes de que el middleware del Gateway lo haya poblado.
    """


@dataclass(frozen=True, slots=True)
class AlcanceGlobalInfo:
    motivo: str
    rol: str


def contexto_tenant_id() -> int:
    """Tenant de la peticion en curso. Lanza si no hay contexto poblado."""
    valor = _tenant_id.get()
    if valor is None:
        raise ContextoTenantAusente(
            "tenant_id no disponible: falta el middleware de services/gateway "
            "o esta operacion requiere alcance_global()."
        )
    return valor


def _establecer_tenant_id(tenant_id: int | None) -> Token[int | None]:
    """Uso exclusivo del middleware del Gateway (services/gateway/api/).

    `None` es valido: un actor de plataforma (p. ej. role_platform_admin
    aprovisionando un tenant nuevo, CU-O18) no tiene tenant propio -- su JWT
    no trae `tenant_id`, y `contexto_tenant_id()` debe seguir lanzando
    `ContextoTenantAusente` para ese caso, no devolver un valor inventado.
    """
    return _tenant_id.set(tenant_id)


def contexto_rol_actor() -> str:
    """Codigo de rol RBAC (p. ej. 'role_operations_controller') que
    packages/repository/base.py activa via SET ROLE en cada sesion (P2).

    Determinado por el Gateway a partir del JWT validado -- nunca elegido
    libremente por el cliente. Distinto del tenant_id: gobierna el eje
    departamental (privilegio de esquema en el motor), no el eje de tenant.
    """
    valor = _rol_actor.get()
    if valor is None:
        raise ContextoTenantAusente(
            "rol_actor no disponible: falta el middleware de services/gateway."
        )
    return valor


def _establecer_rol_actor(rol_actor: str) -> Token[str | None]:
    """Uso exclusivo del middleware del Gateway (services/gateway/api/)."""
    return _rol_actor.set(rol_actor)


def contexto_usuario_id() -> int | None:
    """Id de tenants.usuario del actor humano de la peticion.

    None para sesiones tecnicas sin usuario humano (p. ej. role_elt_reader
    ejecutando una DAG de Airflow) -- a diferencia de tenant_id y rol_actor,
    su ausencia no es un error de programacion.
    """
    return _usuario_id.get()


def _establecer_usuario_id(usuario_id: int | None) -> Token[int | None]:
    """Uso exclusivo del middleware del Gateway (services/gateway/api/)."""
    return _usuario_id.set(usuario_id)


def contexto_aerolinea_id() -> int | None:
    """Aerolinea a la que pertenece el actor humano, o None.

    Solo tiene valor para un usuario asociado a una aerolinea concreta
    (`tenants.usuario.aerolinea_id`) -- None para la gran mayoria, que es
    personal del aeropuerto y no de una aerolinea. Igual que `usuario_id`,
    su ausencia NO es un error de programacion.

    Existe para que infrastructure/ pueda aplicar la restriccion "solo sus
    itinerarios"/"sus cargos" que la matriz 4.3.1 asigna a
    role_airline_coordinator y que los archivos de GRANT delegan
    explicitamente a la aplicacion (MonetDB no tiene RLS) -- ver
    `_ROL_CON_ACCESO_RESTRINGIDO` en aerohub_aodb/aerohub_billing.

    Viaja en el JWT como el resto de la identidad, nunca se acepta del
    cuerpo de la peticion: un coordinador no puede pedir los vuelos de
    otra aerolinea cambiando un parametro.
    """
    return _aerolinea_id.get()


def _establecer_aerolinea_id(aerolinea_id: int | None) -> Token[int | None]:
    """Uso exclusivo del middleware del Gateway (services/gateway/api/)."""
    return _aerolinea_id.set(aerolinea_id)


def alcance_global_activo() -> AlcanceGlobalInfo | None:
    return _alcance_global_activo.get()


def rol_activo_de_sesion() -> str:
    """Rol que packages/repository/base.py debe activar via SET ROLE.

    Bajo alcance_global(), es el rol declarado en el bloque (p. ej.
    role_elt_reader durante una extraccion cruzada), no el rol_actor de la
    peticion -- alcance_global no es solo una anotacion de auditoria: activa
    de verdad ese rol tecnico para la sesion (ADR-019 G3).
    """
    info = alcance_global_activo()
    if info is not None:
        return info.rol
    return contexto_rol_actor()


@contextmanager
def alcance_global(*, motivo: str, rol: str) -> Iterator[None]:
    """Excepcion nominal y auditada al filtro de tenant obligatorio (ADR-019 G3).

    Uso legitimo: extraccion de role_elt_reader hacia bronce, aprovisionamiento
    de un tenant nuevo, diagnostico de plataforma por role_data_engineer /
    role_ml_engineer. Cada uso queda registrado en compliance.log_auditoria
    (packages/repository/audit.py, S0.2) — la superficie de excepcion es una
    lista finita y revisable, no una convencion implicita.
    """
    if not motivo or not rol:
        raise ValueError("alcance_global exige motivo y rol explicitos, sin valores por defecto")
    token = _alcance_global_activo.set(AlcanceGlobalInfo(motivo=motivo, rol=rol))
    try:
        yield
    finally:
        _alcance_global_activo.reset(token)
