"""Invariantes de terminal y puerta (Fase 3 de
docs/diseno/PLAN_CORRECCION_MODULOS.md, causa raiz backend: M3 no tenia
ningun alta/edicion de terminal o puerta, solo el tablero de solo lectura
y el flujo de asignacion).

Puro: sin SQLAlchemy, sin FastAPI (ADR-017 regla 1).
"""

from __future__ import annotations

# Mismos 2 valores que el CHECK de motor (db/ddl/monetdb/10_ops.sql,
# chk_puerta_tipo) -- domain falla rapido, antes de tocar la base.
TIPOS_PUERTA = ("contacto", "remota")


class TerminalInvalida(Exception):
    pass


class PuertaInvalida(Exception):
    pass


def validar_terminal(*, codigo: str, nombre: str) -> None:
    if not codigo or len(codigo) > 10:
        raise TerminalInvalida("codigo de terminal invalido (1 a 10 caracteres)")
    if not nombre or len(nombre) > 100:
        raise TerminalInvalida("nombre de terminal invalido (1 a 100 caracteres)")


def validar_puerta(*, codigo: str, tipo: str, envergadura_max_m: float) -> None:
    if not codigo or len(codigo) > 10:
        raise PuertaInvalida("codigo de puerta invalido (1 a 10 caracteres)")
    if tipo not in TIPOS_PUERTA:
        raise PuertaInvalida(
            f"tipo de puerta invalido: {tipo!r} (valores validos: {TIPOS_PUERTA})"
        )
    if envergadura_max_m <= 0:
        raise PuertaInvalida("envergadura_max_m debe ser mayor que cero")
