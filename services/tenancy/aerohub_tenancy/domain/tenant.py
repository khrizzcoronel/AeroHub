"""Invariantes de tenant (Sprint S1.1, Plan §8.1, CU-O18).

A diferencia de catalogo.estado_vuelo_catalogo (abierto), `tenant.estado`
es un CHECK cerrado de 4 valores (SDD-DATA-001 §6.3) -- el dominio SI
codifica la maquina de estados completa aqui, no solo una regla parcial.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

ESTADOS_VALIDOS = ("en_onboarding", "activo", "suspendido", "dado_de_baja")

_TRANSICIONES_VALIDAS: dict[str, tuple[str, ...]] = {
    "en_onboarding": ("activo", "dado_de_baja"),
    "activo": ("suspendido", "dado_de_baja"),
    "suspendido": ("activo", "dado_de_baja"),
    "dado_de_baja": (),  # terminal
}

_CODIGO_PATRON = re.compile(r"^[A-Z0-9_-]{2,30}$")


class TenantInvalido(Exception):
    pass


class TransicionTenantInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Tenant:
    id: int
    codigo: str
    razon_social: str
    aeropuerto_id: int
    plan_id: int
    estado: str
    es_sandbox: bool = False

    def __post_init__(self) -> None:
        if not _CODIGO_PATRON.match(self.codigo):
            raise TenantInvalido(
                f"codigo debe ser 2-30 caracteres alfanumericos en mayuscula "
                f"(guion/guion bajo permitido): {self.codigo!r}"
            )
        if not self.razon_social.strip():
            raise TenantInvalido("razon_social no puede ser vacio")
        if self.estado not in ESTADOS_VALIDOS:
            raise TenantInvalido(f"estado invalido: {self.estado!r}")


def validar_transicion_estado(estado_actual: str, estado_nuevo: str) -> None:
    if estado_actual not in ESTADOS_VALIDOS:
        raise TransicionTenantInvalida(f"estado_actual invalido: {estado_actual!r}")
    if estado_nuevo not in ESTADOS_VALIDOS:
        raise TransicionTenantInvalida(f"estado_nuevo invalido: {estado_nuevo!r}")
    if estado_nuevo not in _TRANSICIONES_VALIDAS[estado_actual]:
        raise TransicionTenantInvalida(
            f"transicion invalida: '{estado_actual}' -> '{estado_nuevo}'"
        )
