-- Los 16 roles de la matriz Rol x Esquema x Permiso (Analisis v6.0 §4.3.1).
--
-- Hallazgo empirico de S0.2 (ver docs/runbooks/monetdb.md): en MonetDB la
-- membresia de rol (GRANT rol TO usuario) NO activa el rol automaticamente
-- en la sesion -- cada conexion debe ejecutar SET ROLE <rol> antes de que
-- sus privilegios apliquen (packages/repository/base.py). Sin ese paso,
-- incluso un usuario con membresia correcta recibe "access denied".
--
-- role_elt_writer (identidad tecnica que escribe ambas bases ClickHouse)
-- NO aparece aqui: no figura en la matriz 4.3.1 (esa matriz es solo
-- MonetDB); es exclusivamente un rol de ClickHouse, se crea en S2.4/S3.1.

CREATE ROLE role_platform_admin;
CREATE ROLE role_sre;
CREATE ROLE role_data_engineer;
CREATE ROLE role_ml_engineer;
CREATE ROLE role_implementation;
CREATE ROLE role_support;
CREATE ROLE role_business_viewer;
CREATE ROLE role_tenant_admin;
CREATE ROLE role_operations_controller;
CREATE ROLE role_airline_coordinator;
CREATE ROLE role_ramp_agent;
CREATE ROLE role_billing_officer;
CREATE ROLE role_tenant_analyst;
CREATE ROLE role_regulatory_auditor;
CREATE ROLE role_people_viewer;
CREATE ROLE role_elt_reader;

-- role_data_engineer opera sobre ops/rampa/billing "via role_elt_reader"
-- (matriz 4.3.1): no recibe grants propios en esos esquemas, hereda los de
-- role_elt_reader por membresia. Sigue exigiendo su propio SET ROLE
-- role_elt_reader explicito en sesion (ver nota de cabecera).
GRANT role_elt_reader TO role_data_engineer;
