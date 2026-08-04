"""Invariantes de usuario (Sprint post-S1.13, workpanel de `usuarios`).

Mismo criterio que `tenant.py`: `usuario.estado` es un CHECK cerrado de 3
valores (db/ddl/monetdb/02_tenants.sql, chk_usuario_estado) -- el dominio
codifica la maquina de estados completa, no una regla parcial.
"""

from __future__ import annotations

ESTADOS_VALIDOS_USUARIO = ("activo", "suspendido", "eliminado_logicamente")

_TRANSICIONES_VALIDAS: dict[str, tuple[str, ...]] = {
    "activo": ("suspendido", "eliminado_logicamente"),
    "suspendido": ("activo", "eliminado_logicamente"),
    "eliminado_logicamente": (),  # terminal
}


class TransicionUsuarioInvalida(Exception):
    pass


def validar_transicion_estado_usuario(estado_actual: str, estado_nuevo: str) -> None:
    if estado_actual not in ESTADOS_VALIDOS_USUARIO:
        raise TransicionUsuarioInvalida(f"estado_actual invalido: {estado_actual!r}")
    if estado_nuevo not in ESTADOS_VALIDOS_USUARIO:
        raise TransicionUsuarioInvalida(f"estado_nuevo invalido: {estado_nuevo!r}")
    if estado_nuevo not in _TRANSICIONES_VALIDAS[estado_actual]:
        raise TransicionUsuarioInvalida(
            f"transicion invalida: '{estado_actual}' -> '{estado_nuevo}'"
        )
