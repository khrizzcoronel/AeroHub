"""Catalogos de solo lectura de M9 Compliance (Sprint S1.19) -- ya
sembrados desde S1.7 (`insertar_tipo_incidente`/etc. en comandos.py, sin
endpoint de alta: mismo patron que concepto_cargo/tipo_tarea de otros
modulos), pero sin ningun listado hasta ahora. Sin esto, los formularios
de alta de incidente/reporte/evidencia obligarian a pegar ids Snowflake
a mano.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.engine import Connection, Row

from .tablas import control_soc2, tipo_incidente, tipo_reporte_regulatorio


def listar_tipos_incidente(conn: Connection) -> list[Row]:
    return list(conn.execute(select(tipo_incidente)))


def listar_tipos_reporte_regulatorio(conn: Connection) -> list[Row]:
    return list(conn.execute(select(tipo_reporte_regulatorio)))


def listar_controles_soc2(conn: Connection) -> list[Row]:
    return list(conn.execute(select(control_soc2)))
