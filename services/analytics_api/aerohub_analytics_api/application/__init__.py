"""Casos de uso del panel táctico (M7). Orquesta `domain/` +
`infrastructure/` -- ninguna sentencia de ClickHouse vive aquí (ADR-017
§5.4, regla 1)."""

from __future__ import annotations

from ..domain import GrupoTactico, InformeTactico, validar_modulo_codigo
from ..infrastructure import leer_filas_modulo, leer_total_modulo


def consultar_informe_tactico(modulo_codigo: str) -> InformeTactico:
    validar_modulo_codigo(modulo_codigo)
    filas = leer_filas_modulo(modulo_codigo)
    total = leer_total_modulo(modulo_codigo)
    return InformeTactico(
        modulo_codigo=modulo_codigo,
        grupos=[
            GrupoTactico(
                clave=clave,
                subtotal=int(subtotal),
                metrica_principal=metrica or None,
            )
            for clave, subtotal, metrica, _calculado_en in filas
        ],
        total_general=total,
        calculado_en=filas[0][3] if filas else None,
    )
