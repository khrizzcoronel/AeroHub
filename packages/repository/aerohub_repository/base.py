"""Unico punto de conexion hacia MonetDB (P1, ADR-014).

Cada sesion:
  1. Abre una conexion y una transaccion.
  2. Ejecuta `SET ROLE <rol_activo_de_sesion()>` -- hallazgo empirico de
     S0.2 (docs/runbooks/monetdb.md): la membresia de rol NO se activa sola
     en MonetDB, hace falta este paso en CADA sesion o incluso un usuario
     con privilegio correcto recibe "access denied" en todo.
  3. Registra `guard.verificar_sentencia` como oyente de `before_execute`
     del motor -- toda sentencia posterior de esa conexion pasa por el
     guardian de tenant (ADR-019 G2) antes de llegar a MonetDB.
  4. El llamador ejecuta su mutacion de negocio Y, en la MISMA transaccion,
     el journal de continuidad (P8, ADR-018) y la auditoria (RNF-S04) --
     ver journal.py y audit.py.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import Connection

from . import guard
from .contexto import rol_activo_de_sesion

_DSN_POR_DEFECTO = "monetdb://aerohub_app:aerohub_app_dev_password@localhost:50000/aerohub"

_engine: Engine | None = None


def _dsn() -> str:
    return os.environ.get("AEROHUB_DB_DSN", _DSN_POR_DEFECTO)


def obtener_engine() -> Engine:
    """Engine de proceso unico (pool de conexiones), creado perezosamente.

    No se crea un Engine por peticion: SQLAlchemy ya gestiona el pool. El
    guardian se registra una sola vez, en la creacion del Engine, no por
    sesion -- `before_execute` es un evento del Engine, no de la Connection.
    """
    global _engine
    if _engine is None:
        # pool_pre_ping=True no basta por si solo -- hallazgo empirico
        # (2026-08-05): pymonetdb puede dejar un socket ya cerrado del
        # lado del servidor sin que el "ping" de SQLAlchemy lo detecte a
        # tiempo (el `assert self.sock` de pymonetdb/mapi.py salta recien
        # al ejecutar la consulta real, no durante el pre-ping), lo que
        # se manifiesta como un 500 en el endpoint -- que ademas el
        # navegador reporta como bloqueado por CORS (ver
        # AutenticacionJWTMiddleware, que ahora convierte cualquier
        # excepcion no prevista en una Response antes de propagarla, para
        # que CORSMiddleware si le agregue los headers). pool_recycle
        # fuerza descartar y reabrir cualquier conexion mas vieja que el
        # umbral, reduciendo drasticamente la ventana en la que un socket
        # puede quedar obsoleto en el pool.
        _engine = create_engine(_dsn(), pool_pre_ping=True, pool_recycle=180)
        event.listens_for(_engine, "before_execute", retval=True)(_antes_de_ejecutar)
    return _engine


def _antes_de_ejecutar(conn, clauseelement, multiparams, params, execution_options):
    guard.verificar_sentencia(clauseelement, multiparams, params)
    return clauseelement, multiparams, params


@contextmanager
def sesion() -> Iterator[Connection]:
    """Unidad de transaccion para un caso de uso completo (application/).

    `infrastructure/` de cada modulo es el unico subpaquete que puede
    invocar esto (ADR-017 §5.4, verificado por import-linter). Una
    excepcion dentro del bloque revierte la transaccion completa --
    incluida cualquier escritura de journal/auditoria ya emitida en la
    misma sesion, preservando la atomicidad de P8.
    """
    engine = obtener_engine()
    rol = rol_activo_de_sesion()  # lanza ContextoTenantAusente si falta (P2)
    if not rol.replace("_", "").isalnum():
        # rol proviene de contexto.py (JWT validado / alcance_global), nunca
        # de entrada de usuario -- esta validacion es defensa en profundidad
        # contra construir la sentencia con f-string, no el control primario.
        raise ValueError(f"rol_actor con caracteres inesperados: {rol!r}")
    with engine.begin() as conn:
        # exec_driver_sql, no execute(text(...)): SET ROLE es configuracion
        # de sesion, no acceso a datos de tenant -- no debe pasar por el
        # guardian (guard.verificar_sentencia rechaza todo TextClause por
        # diseno). exec_driver_sql no dispara el evento before_execute,
        # verificado empiricamente en S0.2.
        conn.exec_driver_sql(f'SET ROLE "{rol}"')
        yield conn
