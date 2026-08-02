"""Invariantes de articulo de base de conocimientos (Sprint S1.8, CU-D6,
RF-012/RF-013/RF-014; data-model.md). Puro: sin SQLAlchemy, sin FastAPI, sin
acceso a datos (ADR-017 Sec5.4, regla 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

ESTADOS_ARTICULO_KB = ("borrador", "publicado", "archivado")

# FR-013: cada version es una fila nueva e identificable por separado, nunca
# se sobrescribe la anterior -- por eso no hay transicion "hacia atras".
_TRANSICIONES_VALIDAS: dict[str, frozenset[str]] = {
    "borrador": frozenset({"publicado"}),
    "publicado": frozenset({"archivado"}),
    "archivado": frozenset(),
}


class ArticuloKBInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class ArticuloKB:
    id: int
    titulo: str
    cuerpo: str
    version: int
    estado: str
    autor_usuario_id: int
    publicado_en: datetime | None = None
    embedding_ref: str | None = None

    def __post_init__(self) -> None:
        if not self.titulo.strip():
            raise ArticuloKBInvalido("titulo no puede ser vacio")
        if not self.cuerpo.strip():
            raise ArticuloKBInvalido("cuerpo no puede ser vacio")
        if self.version <= 0:
            raise ArticuloKBInvalido("version debe ser positiva")
        if self.estado not in ESTADOS_ARTICULO_KB:
            raise ArticuloKBInvalido(f"estado invalido: {self.estado!r}")


def transicion_valida(estado_actual: str, estado_nuevo: str) -> bool:
    if estado_actual not in _TRANSICIONES_VALIDAS or estado_nuevo not in ESTADOS_ARTICULO_KB:
        return False
    return estado_nuevo in _TRANSICIONES_VALIDAS[estado_actual]
