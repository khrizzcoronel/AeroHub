"""Catalogo de aerolineas/aeronaves/tipos de vuelo para el formulario de
alta de vuelo (Sprint S1.15, PLAN v3.0 §8-bis.1). `catalogo.aerolinea`,
`catalogo.aeronave`, `catalogo.modelo_aeronave` y `catalogo.tipo_vuelo` se
redeclaran localmente de solo lectura -- mismo patron que
`aerohub_tenancy/infrastructure/consultas_catalogo.py` sobre
`catalogo.aeropuerto` (independencia de modulos, ADR-017 §5.4): son tablas
globales sin dueno claro entre los modulos de negocio, ya registradas como
alcance 'global' en `packages/repository/aerohub_repository/alcances.py`
(no hace falta volver a registrarlas aqui).
"""

from __future__ import annotations

from sqlalchemy import (
    CHAR,
    BigInteger,
    Column,
    MetaData,
    Numeric,
    SmallInteger,
    String,
    Table,
    select,
)
from sqlalchemy.engine import Connection, Row

_metadata = MetaData()

aerolinea = Table(
    "aerolinea",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo_iata", CHAR(2)),
    Column("codigo_icao", CHAR(3)),
    Column("nombre", String(150)),
    Column("pais_id", BigInteger),
    schema="catalogo",
)

modelo_aeronave = Table(
    "modelo_aeronave",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo_icao_tipo", String(4)),
    Column("fabricante", String(100)),
    Column("modelo", String(100)),
    Column("capacidad_pax_tipica", SmallInteger),
    Column("envergadura_m", Numeric(5, 2)),
    Column("categoria_estela", CHAR(1)),
    schema="catalogo",
)

aeronave = Table(
    "aeronave",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("matricula", String(10)),
    Column("modelo_aeronave_id", BigInteger),
    Column("aerolinea_id", BigInteger),
    schema="catalogo",
)

tipo_vuelo = Table(
    "tipo_vuelo",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo", String(20)),
    Column("descripcion", String(100)),
    schema="catalogo",
)

# Redeclarada tambien aqui (ademas de aerohub_tenancy) -- hallazgo empirico
# verificando en navegador real: GET /catalogo/aeropuertos de tenancy exige
# el scope "tenants:crear" (solo role_platform_admin), asi que un rol
# operativo (role_tenant_admin, role_operations_controller) recibia 403 al
# poblar el select de origen/destino, y el interceptor lo traducia en un
# logout forzado. research.md Decision 2 asumio sin verificar que era
# reutilizable "desde cualquier vista" -- no lo era.
aeropuerto = Table(
    "aeropuerto",
    _metadata,
    Column("id", BigInteger, primary_key=True),
    Column("codigo_iata", CHAR(3)),
    Column("codigo_icao", CHAR(4)),
    Column("nombre", String(150)),
    Column("ciudad", String(100)),
    schema="catalogo",
)


def listar_aerolineas(conn: Connection) -> list[Row]:
    stmt = select(aerolinea).order_by(aerolinea.c.nombre)
    return list(conn.execute(stmt))


def listar_aeronaves(conn: Connection) -> list[Row]:
    stmt = (
        select(
            aeronave.c.id,
            aeronave.c.matricula,
            aeronave.c.aerolinea_id,
            modelo_aeronave.c.fabricante,
            modelo_aeronave.c.modelo,
        )
        .select_from(
            aeronave.join(modelo_aeronave, modelo_aeronave.c.id == aeronave.c.modelo_aeronave_id)
        )
        .order_by(aeronave.c.matricula)
    )
    return list(conn.execute(stmt))


def listar_tipos_vuelo(conn: Connection) -> list[Row]:
    stmt = select(tipo_vuelo).order_by(tipo_vuelo.c.codigo)
    return list(conn.execute(stmt))


def listar_aeropuertos(conn: Connection) -> list[Row]:
    stmt = select(aeropuerto).order_by(aeropuerto.c.codigo_iata)
    return list(conn.execute(stmt))
