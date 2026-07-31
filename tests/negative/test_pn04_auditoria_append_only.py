"""PN-04 -- Intento de UPDATE/DELETE sobre compliance.log_auditoria (P5,
RNF-S04). Al carecer MonetDB de triggers equivalentes a los de un motor con
soporte nativo, la inmutabilidad se verifica por AUSENCIA de privilegio en
el motor: ningun rol, ni siquiera role_platform_admin, recibe GRANT UPDATE
ni GRANT DELETE sobre esta tabla (93_grants_compliance.sql,
94_grants_continuidad.sql no otorgan ninguno de los dos).
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

# Todos los roles con algun privilegio sobre log_auditoria (SELECT y/o
# INSERT) -- ninguno debe poder UPDATE ni DELETE.
_TODOS_LOS_ROLES = [
    "role_platform_admin",
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
    "role_people_viewer",
    "role_elt_reader",
]


@pytest.mark.parametrize("rol", _TODOS_LOS_ROLES)
def test_ningun_rol_puede_update_log_auditoria(app_engine, set_role, rol):
    with app_engine.connect() as conn:
        set_role(conn, rol)
        with pytest.raises(OperationalError, match="access denied|UPDATE"):
            conn.exec_driver_sql("UPDATE compliance.log_auditoria SET esquema = 'x' WHERE id = 1")


@pytest.mark.parametrize("rol", _TODOS_LOS_ROLES)
def test_ningun_rol_puede_delete_log_auditoria(app_engine, set_role, rol):
    with app_engine.connect() as conn:
        set_role(conn, rol)
        with pytest.raises(OperationalError, match="access denied|DELETE"):
            conn.exec_driver_sql("DELETE FROM compliance.log_auditoria WHERE id = 1")


def test_catalogo_de_privilegios_no_registra_update_ni_delete_sobre_log_auditoria(admin_engine):
    """Verificacion directa del catalogo del motor (sys.privileges), no solo
    del comportamiento observado: si algun GRANT UPDATE/DELETE existiera,
    esta consulta lo revelaria aunque el rol probado arriba no lo ejerciera.
    """
    with admin_engine.connect() as conn:
        filas = conn.execute(
            text(
                """
                SELECT a.name, pc.privilege_code_name
                FROM sys.privileges p
                JOIN sys.auths a ON p.auth_id = a.id
                JOIN sys._tables t ON p.obj_id = t.id
                JOIN sys.schemas s ON t.schema_id = s.id
                JOIN sys.privilege_codes pc ON p.privileges = pc.privilege_code_id
                WHERE s.name = 'compliance' AND t.name = 'log_auditoria'
                  AND (pc.privilege_code_name LIKE '%UPDATE%'
                       OR pc.privilege_code_name LIKE '%DELETE%')
                """
            )
        ).fetchall()
    assert filas == [], f"GRANT UPDATE/DELETE inesperado sobre log_auditoria: {filas}"
