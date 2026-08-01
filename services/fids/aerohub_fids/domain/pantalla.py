"""Pantalla FIDS (Sprint S1.3, Plan §8.3, RF-O07, RNF-R04).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

ESTADOS_PANTALLA = ("en_linea", "sin_senal", "mantenimiento")


class PantallaInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class PantallaFids:
    id: int
    tenant_id: int
    terminal_id: int
    codigo: str
    plantilla_id: int
    estado: str
    ubicacion_descripcion: str | None = None
    ultima_senal_en: datetime | None = None
    version_firmware: str | None = None

    def __post_init__(self) -> None:
        if not self.codigo.strip():
            raise PantallaInvalida("codigo no puede ser vacio")
        if self.estado not in ESTADOS_PANTALLA:
            raise PantallaInvalida(f"estado invalido: {self.estado!r}")

    def esta_sin_senal(self, ahora: datetime, umbral_segundos: int) -> bool:
        """RNF-R04: sin senal si nunca reporto, o si el ultimo heartbeat
        supera el umbral (< 60s en produccion; configurable para que las
        pruebas no tengan que esperar 60s reales).
        """
        if self.ultima_senal_en is None:
            return True
        return (ahora - self.ultima_senal_en).total_seconds() > umbral_segundos
