"""Invariantes de incidente de seguridad (Sprint S1.7, SDD-DATA-001
Sec10.3). Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos
(ADR-017 Sec5.4, regla 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SEVERIDADES_INCIDENTE = ("baja", "media", "alta", "critica")
ESTADOS_INCIDENTE = ("abierto", "en_investigacion", "contenido", "cerrado")


class IncidenteSeguridadInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class IncidenteSeguridad:
    id: int
    tenant_id: int
    tipo_incidente_id: int
    descripcion: str
    severidad: str
    detectado_en: datetime
    reportado_por_usuario_id: int
    estado: str

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise IncidenteSeguridadInvalido("descripcion no puede ser vacia")
        if self.severidad not in SEVERIDADES_INCIDENTE:
            raise IncidenteSeguridadInvalido(f"severidad invalida: {self.severidad!r}")
        if self.estado not in ESTADOS_INCIDENTE:
            raise IncidenteSeguridadInvalido(f"estado invalido: {self.estado!r}")
