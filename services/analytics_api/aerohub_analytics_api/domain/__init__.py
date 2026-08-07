"""Entidades del panel táctico (M7, ClickHouse). Puro: sin cliente de
ClickHouse, sin FastAPI (ADR-017 §5.4, regla 1) -- igual que domain/ en
cualquier otro módulo de negocio.

Alcance de este sprint (pedido directo del usuario, 2026-08-05, demo
mínima -- no la ingesta medallion completa de la Fase 2/S2.1-S2.4):
`GrupoTactico`/`InformeTactico` son la forma ya usada por los informes
compuestos de MonetDB (S1.18) -- se reutiliza la misma forma para que el
frontend no necesite dos contratos distintos según el origen de dato.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

MODULOS_TACTICOS = ("vuelos", "puertas", "rampa", "billing", "tenants", "compliance")


class ModuloTacticoInvalido(Exception):
    pass


@dataclass(frozen=True, slots=True)
class GrupoTactico:
    clave: str
    subtotal: int
    metrica_principal: str | None


@dataclass(frozen=True, slots=True)
class InformeTactico:
    modulo_codigo: str
    grupos: list[GrupoTactico]
    total_general: int
    calculado_en: datetime | None


def validar_modulo_codigo(modulo_codigo: str) -> None:
    if modulo_codigo not in MODULOS_TACTICOS:
        raise ModuloTacticoInvalido(f"módulo táctico desconocido: {modulo_codigo!r}")
