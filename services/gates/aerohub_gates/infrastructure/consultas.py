"""Lecturas de ops.puerta / ops.vuelo / ops.asignacion_puerta y del
catalogo transversal de aeronaves (Sprint S1.4). Mismo patron que
aerohub_aodb.infrastructure.consultas: toda consulta sobre una tabla
alcance='tenant' filtra por `contexto_tenant_id()`, sin excepcion (PN-01).
"""

from __future__ import annotations

from aerohub_repository.contexto import contexto_tenant_id
from sqlalchemy import BigInteger, Column, MetaData, Numeric, String, Table, select
from sqlalchemy.engine import Connection, Row

from .tablas import asignacion_puerta, puerta, vuelo

_metadata_catalogo = MetaData()

# catalogo.* es alcance 'global' (packages/repository/alcances.py): el
# guardian no exige filtro de tenant para consultarlas.
aeronave = Table(
    "aeronave",
    _metadata_catalogo,
    Column("id", BigInteger, primary_key=True),
    Column("matricula", String(10)),
    Column("modelo_aeronave_id", BigInteger),
    Column("aerolinea_id", BigInteger),
    schema="catalogo",
)

modelo_aeronave = Table(
    "modelo_aeronave",
    _metadata_catalogo,
    Column("id", BigInteger, primary_key=True),
    Column("codigo_icao_tipo", String(4)),
    Column("envergadura_m", Numeric(5, 2)),
    schema="catalogo",
)

_ESTADOS_QUE_OCUPAN = ("planificada", "activa")


def obtener_puerta_por_id(conn: Connection, puerta_id: int) -> Row | None:
    stmt = select(puerta).where(
        puerta.c.tenant_id == contexto_tenant_id(), puerta.c.id == puerta_id
    )
    return conn.execute(stmt).first()


def obtener_asignacion_por_id(conn: Connection, asignacion_id: int) -> Row | None:
    stmt = select(asignacion_puerta).where(
        asignacion_puerta.c.tenant_id == contexto_tenant_id(),
        asignacion_puerta.c.id == asignacion_id,
    )
    return conn.execute(stmt).first()


def listar_puertas(conn: Connection) -> list[Row]:
    stmt = select(puerta).where(puerta.c.tenant_id == contexto_tenant_id())
    return list(conn.execute(stmt))


def listar_asignaciones_que_ocupan_puerta(conn: Connection, *, puerta_id: int) -> list[Row]:
    """Asignaciones 'planificada'/'activa' de esta puerta -- las unicas que
    reservan el recurso (ver domain.puerta_ocupa_intervalo) y por lo tanto
    las unicas relevantes para el chequeo de no solapamiento (PN-05)."""
    stmt = select(asignacion_puerta).where(
        asignacion_puerta.c.tenant_id == contexto_tenant_id(),
        asignacion_puerta.c.puerta_id == puerta_id,
        asignacion_puerta.c.estado.in_(_ESTADOS_QUE_OCUPAN),
    )
    return list(conn.execute(stmt))


def obtener_vuelo_con_envergadura(conn: Connection, vuelo_id: int) -> Row | None:
    stmt = (
        select(
            vuelo.c.id,
            vuelo.c.tenant_id,
            vuelo.c.numero_vuelo,
            vuelo.c.sta_utc,
            vuelo.c.std_utc,
            modelo_aeronave.c.envergadura_m,
        )
        .select_from(
            vuelo.join(aeronave, aeronave.c.id == vuelo.c.aeronave_id).join(
                modelo_aeronave, modelo_aeronave.c.id == aeronave.c.modelo_aeronave_id
            )
        )
        .where(vuelo.c.tenant_id == contexto_tenant_id(), vuelo.c.id == vuelo_id)
    )
    return conn.execute(stmt).first()


def listar_vuelos_sin_asignacion_con_envergadura(conn: Connection) -> list[Row]:
    """Vuelos del tenant que todavia no tienen una asignacion de puerta
    'planificada'/'activa' -- entrada del asignador automatico (PuLP)."""
    # vuelo_id es un id Snowflake globalmente unico (packages/kernel):
    # aunque el guardian G2 no recorre subconsultas correlacionadas (mismo
    # limite documentado en aerohub_aodb.infrastructure.consultas, riesgo
    # R-11), filtrar tambien aqui por tenant_id es correcto por intencion,
    # no solo por aislamiento -- nunca podria colisionar con el vuelo_id de
    # otro tenant de todas formas.
    subconsulta_ya_asignados = (
        select(asignacion_puerta.c.vuelo_id)
        .where(
            asignacion_puerta.c.tenant_id == contexto_tenant_id(),
            asignacion_puerta.c.estado.in_(_ESTADOS_QUE_OCUPAN),
        )
        .scalar_subquery()
    )
    stmt = (
        select(
            vuelo.c.id,
            vuelo.c.tenant_id,
            vuelo.c.numero_vuelo,
            vuelo.c.sta_utc,
            vuelo.c.std_utc,
            modelo_aeronave.c.envergadura_m,
        )
        .select_from(
            vuelo.join(aeronave, aeronave.c.id == vuelo.c.aeronave_id).join(
                modelo_aeronave, modelo_aeronave.c.id == aeronave.c.modelo_aeronave_id
            )
        )
        .where(
            vuelo.c.tenant_id == contexto_tenant_id(),
            vuelo.c.id.not_in(subconsulta_ya_asignados),
        )
    )
    return list(conn.execute(stmt))


def listar_asignaciones(conn: Connection) -> list[Row]:
    """Tablero de puertas (Plan §8.4): asignaciones del tenant con el
    codigo de puerta y numero de vuelo ya resueltos, para no obligar al
    cliente HTTP a hacer N+1 consultas."""
    stmt = (
        select(
            asignacion_puerta.c.id,
            asignacion_puerta.c.puerta_id,
            puerta.c.codigo.label("puerta_codigo"),
            asignacion_puerta.c.vuelo_id,
            vuelo.c.numero_vuelo,
            asignacion_puerta.c.inicio_previsto,
            asignacion_puerta.c.fin_previsto,
            asignacion_puerta.c.estado,
        )
        .select_from(
            asignacion_puerta.join(puerta, puerta.c.id == asignacion_puerta.c.puerta_id).join(
                vuelo, vuelo.c.id == asignacion_puerta.c.vuelo_id
            )
        )
        .where(
            asignacion_puerta.c.tenant_id == contexto_tenant_id(),
            puerta.c.tenant_id == contexto_tenant_id(),
            vuelo.c.tenant_id == contexto_tenant_id(),
        )
    )
    return list(conn.execute(stmt))
