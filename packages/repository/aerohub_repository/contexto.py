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
from contextvars import ContextVar
from dataclasses import dataclass

_tenant_id: ContextVar[int | None] = ContextVar("aerohub_tenant_id", default=None)
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


def _establecer_tenant_id(tenant_id: int) -> object:
    """Uso exclusivo del middleware del Gateway (services/gateway/api/)."""
    return _tenant_id.set(tenant_id)


def alcance_global_activo() -> AlcanceGlobalInfo | None:
    return _alcance_global_activo.get()


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
