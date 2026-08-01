"""Incidencia de rampa por desviacion del estandar de turnaround (Sprint
S1.5, Plan §8.5, RF-O16, OP2b; SDD-DATA-001 §8.5).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 §5.4, regla
1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SEVERIDADES_INCIDENCIA_RAMPA = ("baja", "media", "alta", "critica")


class IncidenciaRampaInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class IncidenciaRampa:
    id: int
    tenant_id: int
    tarea_turnaround_id: int
    tipo_incidencia_id: int
    descripcion: str
    severidad: str
    detectada_en: datetime
    resuelta_en: datetime | None = None
    resuelta_por_usuario_id: int | None = None

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise IncidenciaRampaInvalida("descripcion no puede ser vacia")
        if self.severidad not in SEVERIDADES_INCIDENCIA_RAMPA:
            raise IncidenciaRampaInvalida(f"severidad invalida: {self.severidad!r}")


def severidad_por_desviacion(*, es_ruta_critica: bool) -> str:
    """Una tarea de ruta critica retrasa el turnaround completo (no puede
    salir el vuelo sin ella, ver TIPOS_TAREA en db/seeds/generate.py); una
    que no lo es puede solaparse con otras sin extender el turnaround.
    RF-O16 no condiciona la GENERACION de la incidencia a es_ruta_critica
    (exige detectar cualquier desviacion del estandar) -- solo se usa aqui
    para graduar la severidad, no para filtrar que tareas se vigilan.
    """
    return "alta" if es_ruta_critica else "media"
