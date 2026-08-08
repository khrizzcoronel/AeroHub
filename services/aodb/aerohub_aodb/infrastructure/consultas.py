"""Lecturas de ops.vuelo (Sprint S1.1). Mismo patron que
services/tenancy/aerohub_tenancy/infrastructure/consultas.py: toda
consulta filtra por tenant_id == contexto_tenant_id(), sin excepcion --
un id de otro tenant simplemente no aparece (0 filas), nunca una excepcion
que distinga "no existe" de "no es tuyo" (PN-01).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from aerohub_repository.contexto import (
    contexto_aerolinea_id,
    contexto_rol_actor,
    contexto_tenant_id,
)
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    MetaData,
    String,
    Table,
    func,
    select,
)
from sqlalchemy.engine import Connection, Row

from .tablas import vuelo, vuelo_estado

# Minimo privilegio dentro del propio tenant: la matriz 4.3.1 asigna a
# role_airline_coordinator U,S,I,Up sobre `ops` pero acotado a "solo sus
# itinerarios", y 96_grants_ops.sql delega ese recorte explicitamente a la
# capa de aplicacion (MonetDB no tiene RLS). Hasta la auditoria de la capa
# operativa (2026-08-08) el recorte no estaba implementado ni era
# representable -- `tenants.usuario` no tenia `aerolinea_id`. Mismo patron
# que `_ROL_CON_ACCESO_RESTRINGIDO` de aerohub_ramp (S1.5).
_ROL_CON_ACCESO_RESTRINGIDO = "role_airline_coordinator"


def filtro_aerolinea_del_actor(columna_aerolinea: Any = None) -> list[Any]:
    """Condicion extra que acota las filas a la aerolinea del actor.

    `columna_aerolinea` permite usar el mismo recorte sobre un alias de
    tabla (`vuelo.alias("v").c.aerolinea_id`), necesario en las consultas
    agrupadas por el hallazgo de MonetDB con columnas a 3 partes. Por
    defecto usa `ops.vuelo.aerolinea_id` sin alias.

    Lista vacia para todo rol que no sea el restringido -- no cambia nada
    para role_operations_controller, role_tenant_admin, etc.

    Para el rol restringido SIN aerolinea asignada devuelve una condicion
    imposible: fail-closed. Un coordinador cuyo usuario no tiene
    `aerolinea_id` configurada no ve NINGUN vuelo, nunca todos -- mismo
    criterio que el guardian G1/G2 (ante la duda, negar). Devolver todo
    seria exactamente el agujero que este filtro viene a cerrar.

    Hallazgo empirico (2026-08-08): el centinela NO puede ser
    `sqlalchemy.false()`. SQLAlchemy colapsa `A AND B AND false` a `false`
    y con ello DESAPARECE el filtro de tenant del WHERE compilado, asi que
    el guardian G2 (que inspecciona la whereclause buscando ese filtro)
    aborta la consulta con TenantScopeViolation. Se usa `IS NULL` sobre la
    propia columna, que en ambas tablas es NOT NULL (10_ops.sql:37,
    12_billing.sql:92) -- nunca coincide, y al ser un predicado real sobre
    una columna no colapsa el resto del WHERE.
    """
    if contexto_rol_actor() != _ROL_CON_ACCESO_RESTRINGIDO:
        return []
    columna = vuelo.c.aerolinea_id if columna_aerolinea is None else columna_aerolinea
    aerolinea_id = contexto_aerolinea_id()
    if aerolinea_id is None:
        return [columna.is_(None)]
    return [columna == aerolinea_id]

_metadata_catalogo = MetaData()

# catalogo.estado_vuelo_catalogo es alcance 'global' (packages/repository/
# alcances.py): el guardian no exige filtro de tenant para consultarla.
estado_vuelo_catalogo = Table(
    "estado_vuelo_catalogo",
    _metadata_catalogo,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(20)),
    Column("descripcion", String(100)),
    Column("es_terminal", Boolean),
    schema="catalogo",
)


def obtener_vuelo_por_id(conn: Connection, vuelo_id: int) -> Row | None:
    """Devuelve None -- y por lo tanto 404, nunca 403 (PN-01) -- si el vuelo
    es de otra aerolinea y el actor es role_airline_coordinator: no se
    confirma la existencia de un recurso que el actor no puede ver, mismo
    criterio que ya aplica entre tenants."""
    stmt = select(vuelo).where(
        vuelo.c.tenant_id == contexto_tenant_id(),
        vuelo.c.id == vuelo_id,
        *filtro_aerolinea_del_actor(),
    )
    return conn.execute(stmt).first()


def obtener_estado_vuelo_actual_por_id(conn: Connection, vuelo_id: int) -> Row | None:
    # No se usa ops.v_vuelo_estado_actual aqui: MonetDB falla al resolver una
    # referencia de columna calificada a 3 partes (schema.vista.columna) en
    # una clausula WHERE sobre una VISTA -- error "no such column", solo
    # reproducible contra vistas (verificado empiricamente; el mismo patron
    # de 3 partes funciona sin problema contra TABLAS reales como ops.vuelo).
    # SQLAlchemy siempre genera el nombre a 3 partes para una Table con
    # schema= al construir el WHERE, asi que se reimplementa aqui la misma
    # logica de "estado mas reciente" (MAX(registrado_en) correlacionado)
    # directamente sobre la tabla base ops.vuelo_estado -- la vista se deja
    # para consumidores que no filtran con columnas calificadas (reportes).
    ve2 = vuelo_estado.alias("ve2")
    mas_reciente = (
        select(func.max(ve2.c.registrado_en))
        .where(ve2.c.vuelo_id == vuelo_estado.c.vuelo_id)
        .scalar_subquery()
    )
    stmt = select(vuelo_estado).where(
        vuelo_estado.c.tenant_id == contexto_tenant_id(),
        vuelo_estado.c.vuelo_id == vuelo_id,
        vuelo_estado.c.registrado_en == mas_reciente,
    )
    return conn.execute(stmt).first()


def obtener_estado_catalogo_por_codigo(conn: Connection, codigo: str) -> Row | None:
    stmt = select(estado_vuelo_catalogo).where(estado_vuelo_catalogo.c.codigo == codigo)
    return conn.execute(stmt).first()


def listar_vuelos(
    conn: Connection, *, fecha_operacion: date | None = None, codigo_estado: str | None = None
) -> list[Row]:
    """Listado de vuelos del tenant con su estado actual (Fase 3 de
    docs/diseno/PLAN_CORRECCION_MODULOS.md, causa raiz D): sin esto la
    vista nucleo no podia mostrar nada al entrar, solo tras un evento de
    WebSocket. Reutiliza el mismo patron de subconsulta correlacionada de
    `obtener_estado_vuelo_actual_por_id` (MAX(registrado_en)) en vez de
    ops.v_vuelo_estado_actual -- esa vista falla con columnas calificadas
    a 3 partes en WHERE (hallazgo empirico ya documentado)."""
    ve2 = vuelo_estado.alias("ve2")
    mas_reciente = (
        select(func.max(ve2.c.registrado_en))
        .where(ve2.c.vuelo_id == vuelo_estado.c.vuelo_id)
        .scalar_subquery()
    )
    tenant_id = contexto_tenant_id()
    stmt = (
        select(vuelo, estado_vuelo_catalogo.c.codigo.label("codigo_estado"))
        .select_from(
            vuelo.outerjoin(
                vuelo_estado,
                (vuelo_estado.c.vuelo_id == vuelo.c.id)
                & (vuelo_estado.c.registrado_en == mas_reciente),
            ).outerjoin(
                estado_vuelo_catalogo, estado_vuelo_catalogo.c.id == vuelo_estado.c.estado_id
            )
        )
        .where(vuelo.c.tenant_id == tenant_id)
        # El guardian G2 exige el filtro de tenant en la clausula WHERE de
        # CADA tabla alcance='tenant' referenciada, no le basta con el ON
        # del JOIN (packages/repository/guard.py::verificar_sentencia solo
        # inspecciona whereclause) -- aunque logicamente redundante con el
        # ON de mas arriba, este filtro es el que satisface al guardian.
        .where((vuelo_estado.c.tenant_id == tenant_id) | (vuelo_estado.c.tenant_id.is_(None)))
        # Minimo privilegio dentro del tenant (hallazgo 3, 2026-08-08):
        # role_airline_coordinator solo ve los vuelos de SU aerolinea.
        .where(*filtro_aerolinea_del_actor())
    )
    if fecha_operacion is not None:
        stmt = stmt.where(vuelo.c.fecha_operacion == fecha_operacion)
    if codigo_estado is not None:
        stmt = stmt.where(estado_vuelo_catalogo.c.codigo == codigo_estado)
    stmt = stmt.order_by(vuelo.c.fecha_operacion.desc(), vuelo.c.std_utc.desc())
    return list(conn.execute(stmt))
