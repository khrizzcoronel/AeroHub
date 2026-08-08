"""Identidad autenticada de la peticion (Sprint S1.1, Plan §8.1; ADR-014 P2;
scopes agregados en S1.2, Plan §8.2, PN-07).

Resultado de validar un JWT o una API Key ya verificados -- las invariantes
de FORMA que toda identidad valida debe cumplir, no la validacion
criptografica en si (eso es infrastructure/, que si depende de PyJWT/Argon2).
"""

from __future__ import annotations

from dataclasses import dataclass, field


class TokenInvalido(Exception):
    """Firma invalida, token expirado, o claims ausentes/malformados."""


class IdentidadInvalida(Exception):
    """El token es valido criptograficamente pero sus claims son incoherentes."""


@dataclass(frozen=True, slots=True)
class Identidad:
    """`tenant_id` es `None` para actores de plataforma sin tenant propio
    (p. ej. role_platform_admin aprovisionando un tenant nuevo, CU-O18) --
    distinto de un JWT malformado, que se rechaza antes de llegar aqui.

    `scopes`: conjunto de permisos de grano fino (p. ej. "vuelos:leer") que
    cada api/ de cada modulo verifica con
    `aerohub_contracts.scopes.requiere_scope` (PN-07: "scope insuficiente"
    -> 403 sin fuga de informacion). Distinto de `rol`, que gobierna el
    privilegio a nivel de motor (SET ROLE); scopes es un control adicional
    a nivel de API, mas granular que un rol RBAC completo.
    """

    tenant_id: int | None
    rol: str
    usuario_id: int | None
    scopes: frozenset[str] = field(default_factory=frozenset)
    sesion_id: int | None = None
    """`None` para identidades de API Key (S1.2) -- no tienen sesion
    revocable, la vigencia de la clave ya se verifico en
    `verificar_api_key`. Solo un JWT de login (S1.10) trae sesion_id."""

    aerolinea_id: int | None = None
    """Aerolinea del usuario (`tenants.usuario.aerolinea_id`), o `None` para
    la gran mayoria -- personal del aeropuerto, no de una aerolinea.

    Habilita la restriccion "solo sus itinerarios"/"sus cargos" que la
    matriz 4.3.1 asigna a role_airline_coordinator (hallazgo 3 de la
    auditoria de la capa operativa, 2026-08-08): el filtro se aplica en
    infrastructure/ de aodb y billing leyendo `contexto_aerolinea_id()`,
    nunca un parametro del cliente."""

    def __post_init__(self) -> None:
        if not self.rol:
            raise IdentidadInvalida("rol vacio")
        if self.tenant_id is not None and self.tenant_id <= 0:
            raise IdentidadInvalida("tenant_id debe ser positivo si esta presente")
