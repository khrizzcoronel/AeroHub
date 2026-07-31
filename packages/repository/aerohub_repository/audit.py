"""Escritura de compliance.log_auditoria (RNF-S04, P5).

Igual que journal.py: se invoca en la MISMA sesion/transaccion que la
mutacion de negocio (P8). Append-only por diseno -- este modulo no expone
ninguna funcion de actualizacion ni borrado, y ningun rol tiene ese
privilegio en el motor (93_grants_compliance.sql).

`usuario_id` SIN FOREIGN KEY hacia tenants.usuario en el motor (ver
db/ddl/monetdb/03_compliance_auditoria.sql para el hallazgo empirico que lo
justifica); su integridad depende de que el valor provenga siempre de
contexto.py, poblado a partir del JWT ya validado.
"""

from __future__ import annotations

from typing import Any

from aerohub_kernel import generar_id
from sqlalchemy import JSON, BigInteger, Column, DateTime, MetaData, String, Table, insert
from sqlalchemy.engine import Connection

from .contexto import contexto_tenant_id, contexto_usuario_id, rol_activo_de_sesion

_metadata = MetaData()

log_auditoria = Table(
    "log_auditoria",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tenant_id", BigInteger),
    Column("esquema", String(30)),
    Column("tabla", String(50)),
    Column("registro_id", BigInteger),
    Column("operacion", String(10)),
    Column("usuario_id", BigInteger),
    Column("rol_codigo", String(50)),
    Column("ocurrido_en", DateTime(timezone=True)),  # DEFAULT now() del motor
    Column("valores_anteriores", JSON),
    Column("valores_nuevos", JSON),
    Column("ip_origen", String(45)),
    schema="compliance",
)

_OPERACIONES_VALIDAS = ("INSERT", "UPDATE", "DELETE", "DENEGADO")


def registrar_auditoria(
    conn: Connection,
    *,
    esquema: str,
    tabla: str,
    registro_id: int,
    operacion: str,
    valores_anteriores: dict[str, Any] | None = None,
    valores_nuevos: dict[str, Any] | None = None,
    ip_origen: str | None = None,
    tenant_id: int | None = None,
) -> int:
    """`tenant_id`: ver la nota equivalente en journal.escribir_journal --
    por defecto se toma del contexto ambiente; pasar un valor explicito
    cuando la fila auditada pertenece a un tenant distinto del contexto
    (p. ej. CU-O18 bajo alcance_global).
    """
    if operacion not in _OPERACIONES_VALIDAS:
        raise ValueError(f"operacion invalida para auditoria: {operacion!r}")

    id_registro = generar_id()
    tenant_id_final = tenant_id if tenant_id is not None else _tenant_id_opcional()

    conn.execute(
        insert(log_auditoria).values(
            id=id_registro,
            tenant_id=tenant_id_final,
            esquema=esquema,
            tabla=tabla,
            registro_id=registro_id,
            operacion=operacion,
            usuario_id=contexto_usuario_id(),
            rol_codigo=rol_activo_de_sesion(),
            valores_anteriores=valores_anteriores,
            valores_nuevos=valores_nuevos,
            ip_origen=ip_origen,
        )
    )
    return id_registro


def _tenant_id_opcional() -> int | None:
    try:
        return contexto_tenant_id()
    except Exception:
        return None
