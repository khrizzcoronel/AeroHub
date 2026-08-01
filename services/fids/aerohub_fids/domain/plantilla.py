"""Plantilla FIDS (Sprint S1.3, Plan §8.3, RF-T03).

`definicion_json` es un layout declarativo (posiciones, textos estaticos,
referencias a datos AGREGADOS de vuelo) -- SIN ningun campo que pueda
identificar a un pasajero (PN-11, RNF-S05). Domain hace cumplir eso de
forma verificable, no solo documentada: recorre el JSON completo buscando
claves de un vocabulario cerrado de PII prohibida.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

CLAVES_PII_PROHIBIDAS = frozenset(
    {
        "nombre_pasajero",
        "apellido_pasajero",
        "pasajero",
        "pasaporte",
        "documento_identidad",
        "email_pasajero",
        "telefono_pasajero",
        "asiento",
        "pnr",
        "boleto",
        "numero_boleto",
    }
)


class PlantillaInvalida(Exception):
    pass


def _ruta_pii(valor: Any, ruta: str = "") -> str | None:
    """Devuelve la RUTA de la primera clave prohibida encontrada, o None."""
    if isinstance(valor, dict):
        for clave, sub in valor.items():
            ruta_clave = f"{ruta}.{clave}" if ruta else str(clave)
            if isinstance(clave, str) and clave.lower() in CLAVES_PII_PROHIBIDAS:
                return ruta_clave
            encontrado = _ruta_pii(sub, ruta_clave)
            if encontrado is not None:
                return encontrado
    elif isinstance(valor, list):
        for i, item in enumerate(valor):
            encontrado = _ruta_pii(item, f"{ruta}[{i}]")
            if encontrado is not None:
                return encontrado
    return None


@dataclass(frozen=True, slots=True)
class PlantillaFids:
    id: int
    tenant_id: int
    nombre: str
    definicion_json: dict[str, Any]
    version: int
    vigente_desde: datetime
    creada_por_usuario_id: int

    def __post_init__(self) -> None:
        if not self.nombre.strip():
            raise PlantillaInvalida("nombre no puede ser vacio")
        if self.version <= 0:
            raise PlantillaInvalida("version debe ser positiva")
        if not isinstance(self.definicion_json, dict):
            raise PlantillaInvalida("definicion_json debe ser un objeto JSON")
        ruta = _ruta_pii(self.definicion_json)
        if ruta is not None:
            raise PlantillaInvalida(
                f"definicion_json contiene un campo de PII prohibido en {ruta!r} (PN-11)"
            )
