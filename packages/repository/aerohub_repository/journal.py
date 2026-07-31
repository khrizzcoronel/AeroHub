"""Journal transaccional de continuidad (ADR-018, componente C1; principio P8).

`escribir_journal` se invoca en la MISMA sesion/transaccion que la mutacion
de negocio que journaliza -- nunca en una conexion separada, o se pierde la
atomicidad que hace de C1 la base del mecanismo de continuidad: o se
confirman ambas escrituras, o ninguna.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from aerohub_kernel import generar_id
from sqlalchemy import JSON, BigInteger, Column, DateTime, MetaData, String, Table, insert
from sqlalchemy.engine import Connection

from .contexto import contexto_tenant_id

_metadata = MetaData()

journal_mutacion = Table(
    "journal_mutacion",
    _metadata,
    Column("lsn", BigInteger, primary_key=True),
    Column("esquema", String(30)),
    Column("tabla", String(50)),
    Column("operacion", String(15)),
    Column("clave_primaria", JSON),
    Column("payload", JSON),
    Column("tenant_id", BigInteger),
    Column("ocurrido_en", DateTime(timezone=True)),  # DEFAULT now() del motor
    Column("checksum_sha256", String(64)),
    schema="continuidad",
)


def _checksum(clave_primaria: dict[str, Any], payload: dict[str, Any]) -> str:
    canonico = json.dumps({"clave_primaria": clave_primaria, "payload": payload}, sort_keys=True)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def escribir_journal(
    conn: Connection,
    *,
    esquema: str,
    tabla: str,
    operacion: str,
    clave_primaria: dict[str, Any],
    payload: dict[str, Any],
    tenant_id: int | None = None,
) -> int:
    """Devuelve el `lsn` generado, por si el llamador quiere correlacionarlo
    (p. ej. en el propio registro de auditoria).

    `tenant_id`: por defecto se toma del contexto de la peticion (None si
    no hay uno, p. ej. bajo alcance_global). Pasar un valor explicito
    cuando la mutacion es DE un tenant que el contexto ambiente no conoce
    -- el caso tipico es CU-O18 (aprovisionar_tenant), donde quien ejecuta
    la operacion es role_platform_admin (sin tenant propio) pero la fila
    que se journaliza SI pertenece al tenant recien creado.
    """
    if operacion not in ("INSERT", "UPDATE", "DELETE_LOGICO", "DDL"):
        raise ValueError(f"operacion invalida para el journal: {operacion!r}")

    lsn = generar_id()
    tenant_id = tenant_id if tenant_id is not None else _tenant_id_opcional()

    conn.execute(
        insert(journal_mutacion).values(
            lsn=lsn,
            esquema=esquema,
            tabla=tabla,
            operacion=operacion,
            clave_primaria=clave_primaria,
            payload=payload,
            tenant_id=tenant_id,
            checksum_sha256=_checksum(clave_primaria, payload),
        )
    )
    return lsn


def _tenant_id_opcional() -> int | None:
    try:
        return contexto_tenant_id()
    except Exception:
        return None
