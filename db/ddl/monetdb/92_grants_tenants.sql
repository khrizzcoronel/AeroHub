-- Privilegios sobre tenants.* -- matriz 4.3.1 (Analisis v6.0), columna
-- `tenants`. U=USAGE se traduce como "sin grant adicional": en MonetDB no
-- existe un privilegio de uso de esquema separado del privilegio sobre el
-- objeto -- conceder SELECT/INSERT/UPDATE en una tabla ya implica poder
-- resolverla dentro de su esquema. Nunca se otorga DELETE (SRS §2.6, P5).

-- role_platform_admin: S,I,Up en todo el esquema (matriz 4.3.1).
GRANT SELECT, INSERT, UPDATE ON tenants.plan TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.plan_modulo TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.tenant TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.licencia TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.usuario TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.rol TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.usuario_rol TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.api_key TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.okr TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.okr_resultado_clave TO role_platform_admin;

-- role_sre: S en todo el esquema.
GRANT SELECT ON tenants.plan TO role_sre;
GRANT SELECT ON tenants.plan_modulo TO role_sre;
GRANT SELECT ON tenants.tenant TO role_sre;
GRANT SELECT ON tenants.licencia TO role_sre;
GRANT SELECT ON tenants.usuario TO role_sre;
GRANT SELECT ON tenants.rol TO role_sre;
GRANT SELECT ON tenants.usuario_rol TO role_sre;
GRANT SELECT ON tenants.api_key TO role_sre;
GRANT SELECT ON tenants.okr TO role_sre;
GRANT SELECT ON tenants.okr_resultado_clave TO role_sre;

-- role_elt_reader: S en todo el esquema (identidad tecnica, lectura completa).
GRANT SELECT ON tenants.plan TO role_elt_reader;
GRANT SELECT ON tenants.plan_modulo TO role_elt_reader;
GRANT SELECT ON tenants.tenant TO role_elt_reader;
GRANT SELECT ON tenants.licencia TO role_elt_reader;
GRANT SELECT ON tenants.usuario TO role_elt_reader;
GRANT SELECT ON tenants.rol TO role_elt_reader;
GRANT SELECT ON tenants.usuario_rol TO role_elt_reader;
GRANT SELECT ON tenants.api_key TO role_elt_reader;
GRANT SELECT ON tenants.okr TO role_elt_reader;
GRANT SELECT ON tenants.okr_resultado_clave TO role_elt_reader;

-- role_data_engineer: sin grant directo -- hereda role_elt_reader (90_roles.sql).

-- role_ml_engineer: sin acceso a tenants (matriz 4.3.1: '-').

-- role_implementation: S,I en todo el esquema ('alta de tenant'), sin Up.
GRANT SELECT, INSERT ON tenants.plan TO role_implementation;
GRANT SELECT, INSERT ON tenants.plan_modulo TO role_implementation;
GRANT SELECT, INSERT ON tenants.tenant TO role_implementation;
GRANT SELECT, INSERT ON tenants.licencia TO role_implementation;
GRANT SELECT, INSERT ON tenants.usuario TO role_implementation;
GRANT SELECT, INSERT ON tenants.rol TO role_implementation;
GRANT SELECT, INSERT ON tenants.usuario_rol TO role_implementation;
GRANT SELECT, INSERT ON tenants.api_key TO role_implementation;
GRANT SELECT, INSERT ON tenants.okr TO role_implementation;
GRANT SELECT, INSERT ON tenants.okr_resultado_clave TO role_implementation;

-- role_support: S en todo el esquema.
GRANT SELECT ON tenants.plan TO role_support;
GRANT SELECT ON tenants.plan_modulo TO role_support;
GRANT SELECT ON tenants.tenant TO role_support;
GRANT SELECT ON tenants.licencia TO role_support;
GRANT SELECT ON tenants.usuario TO role_support;
GRANT SELECT ON tenants.rol TO role_support;
GRANT SELECT ON tenants.usuario_rol TO role_support;
GRANT SELECT ON tenants.api_key TO role_support;
GRANT SELECT ON tenants.okr TO role_support;
GRANT SELECT ON tenants.okr_resultado_clave TO role_support;

-- role_business_viewer: S,I,Up SOLO en okr y okr_resultado_clave (matriz 4.3.1,
-- acotacion explicita entre parentesis). Sin acceso al resto de tenants.
GRANT SELECT, INSERT, UPDATE ON tenants.okr TO role_business_viewer;
GRANT SELECT, INSERT, UPDATE ON tenants.okr_resultado_clave TO role_business_viewer;

-- role_tenant_admin: 'usuarios propios' (matriz 4.3.1) -- S,I,Up sobre las
-- tablas que administra directamente; S sobre su propio contexto comercial
-- (tenant/licencia/plan), sin escritura sobre esas tres -- interpretacion de
-- ingenieria que desarrolla el parentesis del origen (SRS §3.2: 'CRUD de
-- usuarios locales, API Keys, licencias... de su tenant' incluye LEER licencias,
-- no solo escribir usuarios). Sin acceso a plan_modulo, rol, okr*.
GRANT SELECT, INSERT, UPDATE ON tenants.usuario TO role_tenant_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.usuario_rol TO role_tenant_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.api_key TO role_tenant_admin;
GRANT SELECT ON tenants.tenant TO role_tenant_admin;
GRANT SELECT ON tenants.licencia TO role_tenant_admin;
GRANT SELECT ON tenants.plan TO role_tenant_admin;

-- role_operations_controller, role_airline_coordinator, role_ramp_agent,
-- role_billing_officer, role_tenant_analyst, role_regulatory_auditor,
-- role_people_viewer: sin acceso a tenants (matriz 4.3.1: '-' en esta columna).