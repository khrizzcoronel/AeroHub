"""Invariantes de ticket de soporte y calculo de SLA (Sprint S1.8, CU-D6,
RF-001/RF-002/RF-003; data-model.md). Puro: sin SQLAlchemy, sin FastAPI, sin
acceso a datos (ADR-017 Sec5.4, regla 1).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

SEVERIDADES_TICKET = ("baja", "media", "alta", "critica")
ESTADOS_TICKET = ("abierto", "en_progreso", "esperando_cliente", "resuelto", "cerrado")

# FR-002: sla_objetivo_min segun el modulo afectado. AODB/FIDS/RAMPA tienen
# valor explicito en el SRS (< 120 min / < 240 min); GATES se trata como
# operacion en tiempo real de la misma familia que AODB/FIDS. BILLING/CUENTA
# no tienen requisito explicito en el SRS -- se les asigna un objetivo mas
# laxo (no son incidentes de operacion en tiempo real), documentado aqui en
# vez de dejarlo implicito.
_SLA_MIN_POR_CATEGORIA: dict[str, int] = {
    "AODB": 119,
    "FIDS": 119,
    "GATES": 119,
    "RAMPA": 239,
    "BILLING": 239,
    "CUENTA": 479,
}
_SLA_MIN_POR_DEFECTO = 239

# Maquina de estados (data-model.md): abierto -> en_progreso ->
# (esperando_cliente <-> en_progreso) -> resuelto -> cerrado. No se permite
# saltar directamente de abierto a resuelto/cerrado.
_TRANSICIONES_VALIDAS: dict[str, frozenset[str]] = {
    "abierto": frozenset({"en_progreso"}),
    "en_progreso": frozenset({"esperando_cliente", "resuelto"}),
    "esperando_cliente": frozenset({"en_progreso"}),
    "resuelto": frozenset({"cerrado"}),
    "cerrado": frozenset(),
}


class TicketInvalido(Exception):
    pass


class TransicionEstadoInvalida(Exception):
    pass


@dataclass(frozen=True, slots=True)
class Ticket:
    id: int
    tenant_id: int
    categoria_id: int
    creado_por_usuario_id: int
    severidad: str
    estado: str
    asunto: str
    creado_en: datetime
    sla_objetivo_min: int
    asignado_a_usuario_id: int | None = None
    primera_respuesta_en: datetime | None = None
    resuelto_en: datetime | None = None

    def __post_init__(self) -> None:
        if not self.asunto.strip():
            raise TicketInvalido("asunto no puede ser vacio")
        if self.severidad not in SEVERIDADES_TICKET:
            raise TicketInvalido(f"severidad invalida: {self.severidad!r}")
        if self.estado not in ESTADOS_TICKET:
            raise TicketInvalido(f"estado invalido: {self.estado!r}")
        if self.sla_objetivo_min <= 0:
            raise TicketInvalido("sla_objetivo_min debe ser positivo")


@dataclass(frozen=True, slots=True)
class TicketMensaje:
    id: int
    ticket_id: int
    autor_usuario_id: int
    cuerpo: str
    enviado_en: datetime
    es_interno: bool = False

    def __post_init__(self) -> None:
        if not self.cuerpo.strip():
            raise TicketInvalido("cuerpo del mensaje no puede ser vacio")


def calcular_sla_objetivo_min(categoria_codigo: str) -> int:
    return _SLA_MIN_POR_CATEGORIA.get(categoria_codigo.upper(), _SLA_MIN_POR_DEFECTO)


def transicion_valida(estado_actual: str, estado_nuevo: str) -> bool:
    if estado_actual not in _TRANSICIONES_VALIDAS or estado_nuevo not in ESTADOS_TICKET:
        return False
    return estado_nuevo in _TRANSICIONES_VALIDAS[estado_actual]
