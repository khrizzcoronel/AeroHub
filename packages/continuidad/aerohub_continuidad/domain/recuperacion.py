"""Calculo puro de RTO/RPO observados (Sprint S1.9, ADR-018 C4). Sin I/O --
las marcas de tiempo se miden en operaciones/restauracion.py.
"""

from __future__ import annotations

from datetime import datetime


class RecuperacionInvalida(Exception):
    pass


def calcular_rto_observado_segundos(inicio: datetime, fin: datetime) -> int:
    if fin < inicio:
        raise RecuperacionInvalida("fin no puede ser anterior a inicio")
    return int((fin - inicio).total_seconds())


def calcular_rpo_observado_segundos(
    momento_snapshot: datetime, momento_restauracion: datetime
) -> int:
    """Ventana de perdida de datos observada: cuanto tiempo separa el
    punto de corte del snapshot restaurado del momento de la prueba -- es
    lo que se perderia en el peor caso (primario Y el flujo continuo del
    journal totalmente inalcanzables, sin poder aplicar ningun delta
    posterior al snapshot)."""
    if momento_restauracion < momento_snapshot:
        raise RecuperacionInvalida("momento_restauracion no puede ser anterior a momento_snapshot")
    return int((momento_restauracion - momento_snapshot).total_seconds())
