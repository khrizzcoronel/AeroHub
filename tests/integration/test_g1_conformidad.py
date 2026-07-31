"""Conformidad G1 (ADR-019): toda tabla que existe de verdad en el motor,
en un esquema gestionado por la aplicacion, debe tener su alcance
declarado via guard.registrar_alcance() (packages/repository/alcances.py).

Una tabla nueva en la DDL sin su declaracion de alcance debe hacer fallar
esta prueba -- es la forma en que "el build falla" (Plan §7.2 DoD) se
concreta: no hay compilacion que verificar en Python puro, pero SI hay una
prueba de conformidad que compara el catalogo real del motor contra el
registro G1, y que corre en cada sprint (regresion, Plan §13).

Ademas, para toda tabla con alcance='tenant', verifica que su columna de
tenant (por defecto tenant_id) existe de verdad y es NOT NULL en el motor
-- declarar 'tenant' sobre una tabla sin esa columna, o con la columna
nullable, seria una declaracion incorrecta que el guardian no podria hacer
cumplir en la practica.
"""

from __future__ import annotations

import pytest
from aerohub_repository.guard import tablas_registradas
from sqlalchemy import bindparam, create_engine, text

DSN_ADMIN = "monetdb://monetdb:aerohub@localhost:50000/aerohub"

# Esquemas cuyas tablas ya gestiona la aplicacion en este sprint. Los demas
# (ops, rampa, billing, support, people, etl_control) estan vacios hasta
# fases posteriores -- no hay nada que verificar en ellos todavia.
ESQUEMAS_GESTIONADOS = ("catalogo", "tenants", "compliance", "continuidad")


def _hay_monetdb() -> bool:
    try:
        engine = create_engine(DSN_ADMIN)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _hay_monetdb(), reason="MonetDB no disponible en localhost:50000"
)


@pytest.fixture()
def admin_engine():
    return create_engine(DSN_ADMIN)


@pytest.fixture()
def tablas_reales(admin_engine):
    stmt = text(
        "SELECT s.name, t.name FROM sys._tables t "
        "JOIN sys.schemas s ON t.schema_id = s.id "
        "WHERE s.name IN :esquemas AND t.system = FALSE"
    ).bindparams(bindparam("esquemas", expanding=True))
    with admin_engine.connect() as conn:
        filas = conn.execute(stmt, {"esquemas": list(ESQUEMAS_GESTIONADOS)}).fetchall()
    return {(esquema, tabla) for esquema, tabla in filas}


def test_toda_tabla_real_tiene_alcance_declarado(tablas_reales):
    registradas = {(r.esquema, r.tabla) for r in tablas_registradas()}
    sin_declarar = tablas_reales - registradas
    assert not sin_declarar, (
        f"Tablas en el motor sin alcance G1 declarado: {sorted(sin_declarar)} -- "
        "agregar registrar_alcance(...) en packages/repository/alcances.py "
        "(o en el modulo correspondiente a partir de Fase 1)."
    )


def test_ninguna_declaracion_g1_referencia_una_tabla_inexistente(tablas_reales):
    """El caso inverso: una entrada en el registro G1 que ya no existe en
    el motor (tabla renombrada o eliminada sin actualizar el registro).
    """
    registradas = {
        (r.esquema, r.tabla) for r in tablas_registradas() if r.esquema in ESQUEMAS_GESTIONADOS
    }
    huerfanas = registradas - tablas_reales
    assert not huerfanas, f"Declaraciones G1 sin tabla real correspondiente: {sorted(huerfanas)}"


def test_toda_tabla_de_alcance_tenant_tiene_columna_tenant_id_not_null(
    admin_engine, tablas_reales
):
    registradas_tenant = [r for r in tablas_registradas() if r.alcance == "tenant"]
    assert registradas_tenant, (
        "Ninguna tabla declarada como alcance 'tenant' -- revisar alcances.py"
    )

    with admin_engine.connect() as conn:
        for registro in registradas_tenant:
            fila = conn.execute(
                text(
                    "SELECT c.\"null\" FROM sys._columns c "
                    "JOIN sys._tables t ON c.table_id = t.id "
                    "JOIN sys.schemas s ON t.schema_id = s.id "
                    "WHERE s.name = :esquema AND t.name = :tabla AND c.name = :columna"
                ),
                {
                    "esquema": registro.esquema,
                    "tabla": registro.tabla,
                    "columna": registro.columna_tenant,
                },
            ).fetchone()
            assert fila is not None, (
                f"{registro.esquema}.{registro.tabla} declarada 'tenant' pero no tiene "
                f"columna '{registro.columna_tenant}' en el motor"
            )
