"""PN-03 -- Rol sin privilegio sobre un esquema departamental ajeno
(RNF-S02, control ESTRUCTURAL de motor). Verificado contra MonetDB real:
el motor deniega, no la aplicacion.
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import OperationalError


@pytest.mark.parametrize(
    "rol",
    [
        # matriz 4.3.1 (Analisis v6.0 §4.3.1): estos roles no tienen NINGUN
        # privilegio sobre tenants en esta columna ('-').
        "role_operations_controller",
        "role_airline_coordinator",
        "role_ramp_agent",
        "role_billing_officer",
        "role_tenant_analyst",
        "role_regulatory_auditor",
        "role_ml_engineer",
    ],
)
def test_rol_sin_privilegio_es_denegado_por_el_motor(app_engine, set_role, rol):
    with app_engine.connect() as conn:
        set_role(conn, rol)
        with pytest.raises(OperationalError, match="access denied"):
            conn.exec_driver_sql("SELECT * FROM tenants.usuario")


def test_rol_con_privilegio_explicito_si_puede(app_engine, set_role):
    """Control positivo: el mecanismo de prueba en si mismo funciona --
    role_platform_admin SI tiene acceso a tenants (matriz 4.3.1: S,I,Up).
    """
    with app_engine.connect() as conn:
        set_role(conn, "role_platform_admin")
        resultado = conn.exec_driver_sql("SELECT COUNT(*) FROM tenants.usuario")
        assert resultado.scalar() is not None
