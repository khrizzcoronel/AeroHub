"""Invariantes de asignacion de puerta y regla de no solapamiento (Sprint
S1.4, Plan §8.4, RF-O02, PN-05; SDD-DATA-001 §7.5).

Puro: sin SQLAlchemy, sin FastAPI, sin acceso a datos (ADR-017 §5.4, regla
1). MonetDB carece de un tipo de rango con restriccion de exclusion nativa
(EXCLUDE USING gist de PostgreSQL) -- el no solapamiento de intervalos
[inicio_previsto, fin_previsto) sobre la misma puerta_id se verifica AQUI,
contra las asignaciones existentes que ya reservan la puerta (estado
'planificada' o 'activa'; una asignacion 'finalizada' o 'cancelada' libera
la puerta y no bloquea nada), documentado como riesgo acotado y no como
control cerrado (SDD-DATA-001 §21, hallazgo M-08).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from aerohub_kernel import es_utc

ESTADOS_ASIGNACION = ("planificada", "activa", "finalizada", "cancelada")
_ESTADOS_QUE_OCUPAN_PUERTA = ("planificada", "activa")


class AsignacionPuertaInvalida(Exception):
    pass


class SolapamientoPuertaInvalido(Exception):
    pass


class PuertaIncompatible(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AsignacionPuerta:
    id: int
    tenant_id: int
    vuelo_id: int
    puerta_id: int
    inicio_previsto: datetime
    fin_previsto: datetime
    asignado_por_usuario_id: int
    asignado_en: datetime
    estado: str
    inicio_real: datetime | None = None
    fin_real: datetime | None = None

    def __post_init__(self) -> None:
        if self.estado not in ESTADOS_ASIGNACION:
            raise AsignacionPuertaInvalida(f"estado invalido: {self.estado!r}")
        if not es_utc(self.inicio_previsto) or not es_utc(self.fin_previsto):
            raise AsignacionPuertaInvalida(
                "inicio_previsto y fin_previsto deben ser datetime en UTC (tz-aware)"
            )
        if self.fin_previsto <= self.inicio_previsto:
            raise AsignacionPuertaInvalida(
                f"fin_previsto ({self.fin_previsto}) debe ser posterior a "
                f"inicio_previsto ({self.inicio_previsto})"
            )
        if (
            self.inicio_real is not None
            and self.fin_real is not None
            and self.fin_real <= self.inicio_real
        ):
            raise AsignacionPuertaInvalida(
                f"fin_real ({self.fin_real}) debe ser posterior a inicio_real ({self.inicio_real})"
            )


def puerta_ocupa_intervalo(estado: str) -> bool:
    """Solo una asignacion 'planificada' o 'activa' reserva la puerta --
    'finalizada'/'cancelada' ya la liberaron y no participan en el chequeo
    de solapamiento de una asignacion nueva."""
    return estado in _ESTADOS_QUE_OCUPAN_PUERTA


def intervalos_se_solapan(
    inicio_a: datetime, fin_a: datetime, inicio_b: datetime, fin_b: datetime
) -> bool:
    """Interseccion de intervalos semiabiertos [inicio, fin) -- dos
    intervalos que solo se TOCAN (fin_a == inicio_b) NO se solapan: la
    puerta queda libre en el instante exacto en que termina la asignacion
    anterior.
    """
    return inicio_a < fin_b and inicio_b < fin_a


@dataclass(frozen=True, slots=True)
class IntervaloOcupado:
    """Una ventana [inicio, fin) que YA reserva la puerta -- ver
    puerta_ocupa_intervalo(); quien construye esta clase (infrastructure/)
    es responsable de filtrar por estado antes de pasarla aqui."""

    inicio: datetime
    fin: datetime
    asignacion_id: int


def verificar_no_solapamiento(
    *, inicio: datetime, fin: datetime, existentes: Iterable[IntervaloOcupado]
) -> None:
    for existente in existentes:
        if intervalos_se_solapan(inicio, fin, existente.inicio, existente.fin):
            raise SolapamientoPuertaInvalido(
                f"el intervalo [{inicio}, {fin}) se solapa con la asignacion "
                f"{existente.asignacion_id} ([{existente.inicio}, {existente.fin}))"
            )


def verificar_compatibilidad_envergadura(
    *, envergadura_aeronave_m: Decimal, envergadura_max_puerta_m: Decimal
) -> None:
    if envergadura_aeronave_m > envergadura_max_puerta_m:
        raise PuertaIncompatible(
            f"envergadura de la aeronave ({envergadura_aeronave_m}m) excede la "
            f"envergadura maxima de la puerta ({envergadura_max_puerta_m}m)"
        )
