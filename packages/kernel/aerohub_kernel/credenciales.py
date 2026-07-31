"""Hash de credenciales con Argon2id (cierra SDD-DATA-001 M-07).

Usado para `tenants.usuario.hash_credencial` y `tenants.api_key.hash_secreto`
(SDD-DATA-001 §6.5, §6.8): "nunca almacena el secreto en claro". Argon2id es
la variante hibrida recomendada por OWASP para hash de contrasenas de
proposito general (resistente tanto a ataques por GPU como por canal
lateral); se fija aqui como algoritmo unico del proyecto, no como opcion
configurable por servicio.
"""

from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()


def hash_credencial(secreto_en_claro: str) -> str:
    """Nunca registrar `secreto_en_claro` en logs ni excepciones."""
    if not secreto_en_claro:
        raise ValueError("secreto_en_claro no puede ser vacio")
    return _hasher.hash(secreto_en_claro)


def verificar_credencial(secreto_en_claro: str, hash_almacenado: str) -> bool:
    try:
        _hasher.verify(hash_almacenado, secreto_en_claro)
    except VerifyMismatchError:
        return False
    return True


def requiere_rehash(hash_almacenado: str) -> bool:
    """True si el hash fue generado con parametros mas debiles que los
    actuales (p. ej. tras subir el costo de Argon2id en una version futura).
    """
    return _hasher.check_needs_rehash(hash_almacenado)
