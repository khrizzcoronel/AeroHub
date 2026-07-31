"""Identidad autenticada de la peticion (Sprint S1.1, Plan §8.1; ADR-014 P2).

Resultado de validar un JWT ya firmado -- las invariantes de FORMA que toda
identidad valida debe cumplir, no la validacion criptografica en si (eso es
infrastructure/jwt_.py, que si depende de PyJWT).
"""

from __future__ import annotations

from dataclasses import dataclass


class TokenInvalido(Exception):
    """Firma invalida, token expirado, o claims ausentes/malformados."""


class IdentidadInvalida(Exception):
    """El token es valido criptograficamente pero sus claims son incoherentes."""


@dataclass(frozen=True, slots=True)
class Identidad:
    """`tenant_id` es `None` para actores de plataforma sin tenant propio
    (p. ej. role_platform_admin aprovisionando un tenant nuevo, CU-O18) --
    distinto de un JWT malformado, que se rechaza antes de llegar aqui.
    """

    tenant_id: int | None
    rol: str
    usuario_id: int | None

    def __post_init__(self) -> None:
        if not self.rol:
            raise IdentidadInvalida("rol vacio")
        if self.tenant_id is not None and self.tenant_id <= 0:
            raise IdentidadInvalida("tenant_id debe ser positivo si esta presente")
