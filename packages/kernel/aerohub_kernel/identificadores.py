"""Codigos IATA/ICAO como tipos de dominio (SDD-DATA-001 §4: CHAR(2)/CHAR(3)/CHAR(4)).

Validar la forma del codigo en el tipo evita que un dato malformado llegue a
domain/ de un modulo distinto; no valida contra el catalogo global (eso es
responsabilidad de infrastructure/, que si tiene acceso a la base).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CodigoIATA:
    """2 letras (aerolinea, motivo de demora) o 3 letras (aeropuerto)."""

    valor: str

    def __post_init__(self) -> None:
        v = self.valor.upper()
        if len(v) not in (2, 3) or not v.isalnum():
            raise ValueError(f"codigo IATA invalido: {self.valor!r}")
        object.__setattr__(self, "valor", v)

    def __str__(self) -> str:
        return self.valor


@dataclass(frozen=True, slots=True)
class CodigoICAO:
    """3 letras (aerolinea) o 4 letras (aeropuerto, tipo de aeronave)."""

    valor: str

    def __post_init__(self) -> None:
        v = self.valor.upper()
        if len(v) not in (3, 4) or not v.isalnum():
            raise ValueError(f"codigo ICAO invalido: {self.valor!r}")
        object.__setattr__(self, "valor", v)

    def __str__(self) -> str:
        return self.valor
