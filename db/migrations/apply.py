"""Aplica el DDL de db/ddl/monetdb/*.sql, en orden lexicografico de archivo.

No usa Alembic: MonetDB no tiene un dialecto de migraciones maduro (el
proyecto ya encontro, en S0.2, que ni siquiera el dialecto SQLAlchemy basico
requiere parches de dependencias — ver packages/repository/pyproject.toml).
En su lugar, cada archivo .sql es la unidad de versionado; el prefijo
numerico (00_, 01_, 90_...) fija el orden de aplicacion.

Uso:
    uv run python -m db.migrations.apply
    uv run python -m db.migrations.apply --host clickhouse-no --dsn monetdb://...

Se aplica al mismo host para primario Y standby (ADR-018, regla derivada de
S1.9): este script no distingue cual es cual, el llamador decide el DSN.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymonetdb

DDL_DIR = Path(__file__).resolve().parents[1] / "ddl" / "monetdb"


def _archivos_ddl() -> list[Path]:
    return sorted(DDL_DIR.glob("*.sql"))


def aplicar(
    *,
    hostname: str,
    port: int,
    database: str,
    username: str,
    password: str,
) -> None:
    archivos = _archivos_ddl()
    if not archivos:
        print(f"Sin archivos .sql en {DDL_DIR}", file=sys.stderr)
        sys.exit(1)

    conn = pymonetdb.connect(
        hostname=hostname, port=port, database=database, username=username, password=password
    )
    try:
        cur = conn.cursor()
        for archivo in archivos:
            sql = archivo.read_text(encoding="utf-8")
            print(f"Aplicando {archivo.name}...")
            cur.execute(sql)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    print(f"DDL aplicado: {len(archivos)} archivo(s).")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=50000)
    parser.add_argument("--database", default="aerohub")
    parser.add_argument("--username", default="monetdb")
    parser.add_argument("--password", default="aerohub")
    args = parser.parse_args()

    aplicar(
        hostname=args.host,
        port=args.port,
        database=args.database,
        username=args.username,
        password=args.password,
    )


if __name__ == "__main__":
    main()
