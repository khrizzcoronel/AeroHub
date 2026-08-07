"""Lecturas de ops.vuelo (Sprint S1.1). Mismo patron que
services/tenancy/aerohub_tenancy/infrastructure/consultas.py: toda
consulta filtra por tenant_id == contexto_tenant_id(), sin excepcion --
un id de otro tenant simplemente no aparece (0 filas), nunca una excepcion
que distinga "no existe" de "no es tuyo" (PN-01).
"""

from __future__ import annotations

from datetime import date

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import BigInteger, Boolean, Column, MetaData, String, Table, func, select
from sqlalchemy.engine import Connection, Row

from .tablas import vuelo, vuelo_estado

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
    stmt = select(vuelo).where(
        vuelo.c.tenant_id == contexto_tenant_id(), vuelo.c.id == vuelo_id
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
    )
    if fecha_operacion is not None:
        stmt = stmt.where(vuelo.c.fecha_operacion == fecha_operacion)
    if codigo_estado is not None:
        stmt = stmt.where(estado_vuelo_catalogo.c.codigo == codigo_estado)
    stmt = stmt.order_by(vuelo.c.fecha_operacion.desc(), vuelo.c.std_utc.desc())
    return list(conn.execute(stmt))
