"""Invariantes de vuelo (Sprint S1.1, Plan §8.1).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 §5.4, regla
1). Validado por construccion -- un `Vuelo` que exista en memoria ya
cumple sus invariantes; no hace falta volver a chequearlas en otra capa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from aerohub_kernel import es_utc

_SENTIDOS_VALIDOS = ("L", "S")


class VueloInvalido(Exception):
    """Un intento de construir un Vuelo que viola una invariante de dominio."""


@dataclass(frozen=True, slots=True)
class Vuelo:
    id: int
    tenant_id: int
    aerolinea_id: int
    aeronave_id: int
    numero_vuelo: str
    tipo_vuelo_id: int
    fecha_operacion: str  # ISO 8601 (YYYY-MM-DD); el tipo `date` se resuelve en infrastructure/
    sentido: str
    aeropuerto_origen_id: int
    aeropuerto_destino_id: int
    sta_utc: datetime
    std_utc: datetime
    eta_utc: datetime | None = None
    etd_utc: datetime | None = None
    ata_utc: datetime | None = None
    atd_utc: datetime | None = None
    pax_estimado: int | None = None

    def __post_init__(self) -> None:
        if self.sentido not in _SENTIDOS_VALIDOS:
            raise VueloInvalido(f"sentido debe ser 'L' o 'S': {self.sentido!r}")

        if self.aeropuerto_origen_id == self.aeropuerto_destino_id:
            raise VueloInvalido(
                "aeropuerto_origen_id y aeropuerto_destino_id no pueden ser el mismo "
                f"({self.aeropuerto_origen_id})"
            )

        if not es_utc(self.sta_utc) or not es_utc(self.std_utc):
            raise VueloInvalido("sta_utc y std_utc deben ser datetime en UTC (tz-aware)")

        # std (salida del origen) debe preceder a sta (llegada al destino)
        # para el mismo tramo -- verdadero independientemente de si esta
        # tenant registra el tramo como 'L' o 'S' (SDD-DATA-001 §7.3).
        if self.std_utc >= self.sta_utc:
            raise VueloInvalido(
                f"std_utc ({self.std_utc}) debe ser anterior a sta_utc ({self.sta_utc})"
            )

        if self.atd_utc is not None and self.ata_utc is not None and self.atd_utc > self.ata_utc:
            raise VueloInvalido(
                f"atd_utc ({self.atd_utc}) no puede ser posterior a ata_utc ({self.ata_utc})"
            )

        if not self.numero_vuelo.strip():
            raise VueloInvalido("numero_vuelo no puede ser vacio")

        if self.pax_estimado is not None and self.pax_estimado < 0:
            raise VueloInvalido(f"pax_estimado no puede ser negativo: {self.pax_estimado}")
