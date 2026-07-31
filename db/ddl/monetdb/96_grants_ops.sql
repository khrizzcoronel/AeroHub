-- Privilegios sobre ops.* -- matriz 4.3.1 (Analisis v6.0), columna `ops`.
-- U=USAGE se traduce como "sin grant adicional" (ver 92_grants_tenants.sql).
-- Nunca se otorga DELETE (SRS §2.6, P5): toda baja de ops.vuelo/puerta/etc.
-- es logica, gestionada por la aplicacion, no por el motor.

-- role_platform_admin: U,S (matriz 4.3.1).
-- role_implementation: U,S,I,Up ('temporal por tenant' -- lo temporal
-- es del lado de usuario_rol.expira_en, no del GRANT).
-- role_support: U,S ('configuracion').
-- role_tenant_admin: U,S,Up ('configuracion FIDS' -- ese detalle llega
-- con plantilla_fids/pantalla_fids en S1.3; aqui se aplica al resto de ops.)
-- role_operations_controller: U,S,I,Up.
-- role_airline_coordinator: U,S,I,Up ('solo sus itinerarios' -- restriccion
-- por aerolinea_id, aplicacion, MonetDB no soporta RLS).
-- role_ramp_agent: U,S ('vuelos asignados' -- idem, por aplicacion).
-- role_elt_reader: U,S (parte de 'toda la base operacional').
--
-- role_sre, role_ml_engineer, role_business_viewer, role_billing_officer,
-- role_tenant_analyst, role_regulatory_auditor, role_people_viewer:
-- sin acceso a ops (matriz 4.3.1: '-').

GRANT SELECT ON ops.terminal TO role_platform_admin;
GRANT SELECT ON ops.puerta TO role_platform_admin;
GRANT SELECT ON ops.vuelo TO role_platform_admin;
GRANT SELECT ON ops.vuelo_estado TO role_platform_admin;
GRANT SELECT ON ops.vuelo_demora TO role_platform_admin;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_platform_admin;

GRANT SELECT, INSERT, UPDATE ON ops.terminal TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.puerta TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_estado TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_demora TO role_implementation;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_implementation;

GRANT SELECT ON ops.terminal TO role_support;
GRANT SELECT ON ops.puerta TO role_support;
GRANT SELECT ON ops.vuelo TO role_support;
GRANT SELECT ON ops.vuelo_estado TO role_support;
GRANT SELECT ON ops.vuelo_demora TO role_support;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_support;

GRANT SELECT, UPDATE ON ops.terminal TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.puerta TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.vuelo TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.vuelo_estado TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.vuelo_demora TO role_tenant_admin;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_tenant_admin;

GRANT SELECT, INSERT, UPDATE ON ops.terminal TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.puerta TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_estado TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_demora TO role_operations_controller;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_operations_controller;

GRANT SELECT, INSERT, UPDATE ON ops.terminal TO role_airline_coordinator;
GRANT SELECT, INSERT, UPDATE ON ops.puerta TO role_airline_coordinator;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo TO role_airline_coordinator;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_estado TO role_airline_coordinator;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_demora TO role_airline_coordinator;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_airline_coordinator;

GRANT SELECT ON ops.terminal TO role_ramp_agent;
GRANT SELECT ON ops.puerta TO role_ramp_agent;
GRANT SELECT ON ops.vuelo TO role_ramp_agent;
GRANT SELECT ON ops.vuelo_estado TO role_ramp_agent;
GRANT SELECT ON ops.vuelo_demora TO role_ramp_agent;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_ramp_agent;

GRANT SELECT ON ops.terminal TO role_elt_reader;
GRANT SELECT ON ops.puerta TO role_elt_reader;
GRANT SELECT ON ops.vuelo TO role_elt_reader;
GRANT SELECT ON ops.vuelo_estado TO role_elt_reader;
GRANT SELECT ON ops.vuelo_demora TO role_elt_reader;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_elt_reader;
