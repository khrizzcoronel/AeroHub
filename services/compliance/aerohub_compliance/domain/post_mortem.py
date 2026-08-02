"""Invariantes de post-mortem y regla de publicacion (Sprint S1.7, CU-O13,
RF-O13; ADR-009). Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos
(ADR-017 Sec5.4, regla 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SEVERIDADES_POST_MORTEM = ("baja", "media", "alta", "critica")
ESTADOS_POST_MORTEM = ("en_progreso", "publicado")
ESTADOS_ACCION = ("pendiente", "en_progreso", "completada", "vencida")


class PostMortemInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PostMortem:
    id: int
    tenant_id: int | None
    incidente_ref: str
    severidad: str
    estado: str
    iniciado_en: datetime
    causa_raiz: str | None = None
    publicado_en: datetime | None = None
    tiempo_resolucion_min: int | None = None

    def __post_init__(self) -> None:
        if not self.incidente_ref.strip():
            raise PostMortemInvalido("incidente_ref no puede ser vacio")
        if self.severidad not in SEVERIDADES_POST_MORTEM:
            raise PostMortemInvalido(f"severidad invalida: {self.severidad!r}")
        if self.estado not in ESTADOS_POST_MORTEM:
            raise PostMortemInvalido(f"estado invalido: {self.estado!r}")
        if self.tiempo_resolucion_min is not None and self.tiempo_resolucion_min < 0:
            raise PostMortemInvalido("tiempo_resolucion_min no puede ser negativo")


@dataclass(frozen=True, slots=True)
class PostMortemAccion:
    id: int
    post_mortem_id: int
    descripcion: str
    responsable_usuario_id: int
    estado: str
    vence_en: datetime
    ticket_ref: str | None = None
    completada_en: datetime | None = None

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise PostMortemInvalido("descripcion no puede ser vacia")
        if self.estado not in ESTADOS_ACCION:
            raise PostMortemInvalido(f"estado de accion invalido: {self.estado!r}")


def puede_publicar(estados_de_acciones: list[str]) -> bool:
    """FR-005: no se puede publicar un post-mortem con alguna accion de
    remediacion sin completar. Una lista vacia (post-mortem sin acciones
    registradas) SI puede publicarse -- la regla es "ninguna abierta", no
    "al menos una completada"."""
    return all(estado == "completada" for estado in estados_de_acciones)
