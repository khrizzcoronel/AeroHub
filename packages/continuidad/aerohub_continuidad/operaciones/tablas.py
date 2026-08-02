"""Objetos Table de SQLAlchemy Core para las 3 tablas nuevas de
`continuidad` (Sprint S1.9). Usadas SOLO para catalogar/consultar via
`aerohub_repository.sesion()` -- nunca para el *replay* generico del
*shipper* sobre el standby (eso usa SQL crudo por `pymonetdb`, ver
`shipper.py`, research.md Decision 3).
"""

from __future__ import annotations

from sqlalchemy import BigInteger, Column, DateTime, Integer, MetaData, String, Table, Text

metadata = MetaData()

snapshot_base = Table(
    "snapshot_base",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("tipo", String(20)),
    Column("lsn_corte", BigInteger),
    Column("generado_en", DateTime(timezone=True)),
    Column("ruta_artefacto", String(500)),
    Column("hash_artefacto", String(64)),
    Column("estado", String(20)),
    Column("verificado_en", DateTime(timezone=True)),
    schema="continuidad",
)

shipper_checkpoint = Table(
    "shipper_checkpoint",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("standby_nombre", String(50)),
    Column("ultimo_lsn_aplicado", BigInteger),
    Column("actualizado_en", DateTime(timezone=True)),
    schema="continuidad",
)

prueba_restauracion = Table(
    "prueba_restauracion",
    metadata,
    Column("id", BigInteger, primary_key=True),
    Column("snapshot_id", BigInteger),
    Column("ejecutado_en", DateTime(timezone=True)),
    Column("rto_observado_segundos", Integer),
    Column("rpo_observado_segundos", Integer),
    Column("resultado", String(20)),
    Column("detalle", String(500)),
    schema="continuidad",
)

# journal_mutacion ya vive en aerohub_repository.journal (S0.2) -- se
# redeclara aqui SOLO para poder construir SELECT tipados de lectura
# (shipper.py, purga.py) sin importar el modulo interno de otro paquete;
# aerohub_repository ya registra su alcance G1, no hace falta repetirlo.
journal_mutacion = Table(
    "journal_mutacion",
    metadata,
    Column("lsn", BigInteger, primary_key=True),
    Column("esquema", String(30)),
    Column("tabla", String(50)),
    Column("operacion", String(15)),
    # Column("clave_primaria")/("payload") deliberadamente SIN tipo JSON de
    # SQLAlchemy: el dialecto sqlalchemy-monetdb ya deserializa columnas
    # JSON del motor a dict/list de Python en el resultado -- declarar
    # ademas `JSON` aqui hace que SQLAlchemy re-intente `json.loads()`
    # sobre un dict ya deserializado y falle (hallazgo empirico de S1.9,
    # ver docs/runbooks/monetdb.md). `Text` deja pasar el valor tal como
    # lo entrega el dialecto, se maneje como dict o como str en
    # shipper.py/purga.py.
    Column("clave_primaria", Text),
    Column("payload", Text),
    Column("tenant_id", BigInteger),
    Column("ocurrido_en", DateTime(timezone=True)),
    Column("checksum_sha256", String(64)),
    schema="continuidad",
)
