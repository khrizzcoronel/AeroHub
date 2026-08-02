"""Escritura de billing.tiempo_espera_agregado (Sprint S1.6). Solo
persiste -- application/ ya calculo el agregado y decide si upsertea.
"""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import insert, update
from sqlalchemy.engine import Connection

from .tablas import tiempo_espera_agregado


def insertar_o_actualizar_tiempo_espera(
    conn: Connection,
    *,
    id: int,
    tenant_id: int,
    terminal_id: int,
    fecha: date,
    franja_inicio: time,
    franja_fin: time,
    minutos_estimados: Decimal,
    muestra_n: int,
    calculado_en: datetime,
    existente_id: int | None,
) -> None:
    if existente_id is not None:
        conn.execute(
            update(tiempo_espera_agregado)
            .where(
                tiempo_espera_agregado.c.id == existente_id,
                tiempo_espera_agregado.c.tenant_id == tenant_id,
            )
            .values(
                minutos_estimados=minutos_estimados,
                muestra_n=muestra_n,
                calculado_en=calculado_en,
            )
        )
        return
    conn.execute(
        insert(tiempo_espera_agregado).values(
            id=id,
            tenant_id=tenant_id,
            terminal_id=terminal_id,
            fecha=fecha,
            franja_inicio=franja_inicio,
            franja_fin=franja_fin,
            minutos_estimados=minutos_estimados,
            muestra_n=muestra_n,
            calculado_en=calculado_en,
        )
    )
