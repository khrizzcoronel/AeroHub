"""Politica minima de contrasena (Sprint S1.10, ADR-020). Puro -- sin I/O,
sin conocer Argon2id ni la base de datos: solo la regla de que forma debe
tener una contrasena para ser aceptada.
"""

from __future__ import annotations

_LONGITUD_MINIMA = 10


class PasswordInvalida(Exception):
    pass


def validar_password(password: str) -> None:
    """Lanza `PasswordInvalida` con el primer requisito que falte -- el
    detalle se devuelve al llamador para responder 422 con el motivo
    (FR-013), nunca un mensaje generico sin utilidad para quien la eligio.
    """
    if len(password) < _LONGITUD_MINIMA:
        raise PasswordInvalida(f"la contrasena debe tener al menos {_LONGITUD_MINIMA} caracteres")
    if not any(c.isalpha() for c in password):
        raise PasswordInvalida("la contrasena debe incluir al menos una letra")
    if not any(c.isdigit() for c in password):
        raise PasswordInvalida("la contrasena debe incluir al menos un digito")
