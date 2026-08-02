"""Purga automatica del journal de mutaciones (Sprint S1.9, ADR-018 C1,
completa la retencion de 48h vigente desde S0.2). Elimina UNICAMENTE
entradas que cumplen AMBAS condiciones a la vez: antiguedad mayor a la
ventana de retencion Y ya confirmadas aplicadas por TODAS las replicas
registradas en `shipper_checkpoint` (research.md Decision 7 de
specs/011-continuidad-rto-rpo/) -- purgar solo por antiguedad podria
destruir una entrada que el shipper todavia no replico tras una
interrupcion prolongada (spec.md, Edge Cases).
"""

from __future__ import annotations

from datetime import timedelta

from aerohub_kernel import ahora_utc
from aerohub_repository import alcance_global, sesion
from sqlalchemy import delete, func, select

from .tablas import journal_mutacion, shipper_checkpoint

_MOTIVO_ALCANCE_GLOBAL = "purga_journal_continuidad"
_ROL = "role_platform_admin"
_VENTANA_RETENCION = timedelta(hours=48)


def purgar_journal_confirmado() -> int:
    """Retorna la cantidad de entradas purgadas. `0` si ninguna replica
    esta registrada todavia en shipper_checkpoint -- fail-closed: sin una
    confirmacion de avance conocida, no se asume que nada este replicado."""
    limite_antiguedad = ahora_utc() - _VENTANA_RETENCION

    with alcance_global(motivo=_MOTIVO_ALCANCE_GLOBAL, rol=_ROL), sesion() as conn:
        lsn_minimo_confirmado = conn.execute(
            select(func.min(shipper_checkpoint.c.ultimo_lsn_aplicado))
        ).scalar()
        if lsn_minimo_confirmado is None:
            return 0

        resultado = conn.execute(
            delete(journal_mutacion).where(
                journal_mutacion.c.ocurrido_en < limite_antiguedad,
                journal_mutacion.c.lsn <= lsn_minimo_confirmado,
            )
        )
        return resultado.rowcount
