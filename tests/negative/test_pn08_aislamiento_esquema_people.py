"""PN-08 -- Cualquier rol != role_people_viewer que consulte el esquema
`people` es denegado por el motor, incluso role_platform_admin (SDD-001
§12: "acceso exclusivo role_people_viewer... denegado incluso a
role_platform_admin").

`people` no tiene tablas hasta S3.3 (Plan §10.3) -- este test crea una
tabla temporal propia, otorgada SOLO a role_people_viewer, para verificar
el mecanismo de aislamiento a nivel de esquema con contenido real, en vez
de una consulta vacia sobre un catalogo sin filas que probar todavia.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

_TODOS_MENOS_PEOPLE_VIEWER = [
    "role_platform_admin",  # SDD-001 §12: denegado incluso a este rol
    "role_sre",
    "role_data_engineer",
    "role_ml_engineer",
    "role_implementation",
    "role_support",
    "role_business_viewer",
    "role_tenant_admin",
    "role_operations_controller",
    "role_airline_coordinator",
    "role_ramp_agent",
    "role_billing_officer",
    "role_tenant_analyst",
    "role_regulatory_auditor",
    "role_elt_reader",
]


@pytest.fixture()
def tabla_people_temporal(admin_engine):
    with admin_engine.begin() as conn:
        conn.execute(text("CREATE TABLE people.pn08_temporal (id BIGINT PRIMARY KEY)"))
        conn.execute(text("INSERT INTO people.pn08_temporal VALUES (1)"))
        conn.execute(text("GRANT SELECT ON people.pn08_temporal TO role_people_viewer"))
    yield
    with admin_engine.begin() as conn:
        conn.execute(text("DROP TABLE people.pn08_temporal"))


@pytest.mark.parametrize("rol", _TODOS_MENOS_PEOPLE_VIEWER)
def test_ningun_otro_rol_accede_a_people(app_engine, set_role, tabla_people_temporal, rol):
    with app_engine.connect() as conn:
        set_role(conn, rol)
        with pytest.raises(OperationalError, match="access denied"):
            conn.exec_driver_sql("SELECT * FROM people.pn08_temporal")


def test_role_people_viewer_si_accede(app_engine, set_role, tabla_people_temporal):
    with app_engine.connect() as conn:
        set_role(conn, "role_people_viewer")
        resultado = conn.exec_driver_sql("SELECT COUNT(*) FROM people.pn08_temporal")
        assert resultado.scalar() == 1
