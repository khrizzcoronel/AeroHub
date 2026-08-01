-- Privilegios sobre ops.* -- matriz 4.3.1 (Analisis v6.0), columna `ops`.
-- U=USAGE se traduce como "sin grant adicional" (ver 92_grants_tenants.sql).
-- Nunca se otorga DELETE (SRS §2.6, P5): toda baja de ops.vuelo/puerta/etc.
-- es logica, gestionada por la aplicacion, no por el motor.

-- role_platform_admin: U,S (matriz 4.3.1); sobre pantalla_fids especificamente
-- tambien recibe UPDATE (S1.3) -- el monitor de sin-senal (RNF-R04) corre
-- como proceso de plataforma sin tenant ambiente (ADR-019 G3, alcance_global)
-- bajo este rol, y necesita poder transicionar pantalla_fids.estado; la
-- matriz no modela procesos automatizados de sistema, solo actores humanos.
-- role_implementation: U,S,I,Up ('temporal por tenant' -- lo temporal
-- es del lado de usuario_rol.expira_en, no del GRANT).
-- role_support: U,S ('configuracion').
-- role_tenant_admin: U,S,Up ('configuracion FIDS') sobre el resto de ops;
-- sobre plantilla_fids/pantalla_fids especificamente tambien recibe INSERT
-- (S1.3) -- "configuracion FIDS" en la matriz 4.3.1 implica publicar
-- plantillas nuevas y registrar pantallas nuevas, no solo actualizar las
-- existentes; sin INSERT el rol no podria ejercer la responsabilidad que
-- la propia matriz le asigna.
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
GRANT SELECT ON ops.plantilla_fids TO role_platform_admin;
GRANT SELECT, UPDATE ON ops.pantalla_fids TO role_platform_admin;

GRANT SELECT, INSERT, UPDATE ON ops.terminal TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.puerta TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_estado TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_demora TO role_implementation;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.plantilla_fids TO role_implementation;
GRANT SELECT, INSERT, UPDATE ON ops.pantalla_fids TO role_implementation;

GRANT SELECT ON ops.terminal TO role_support;
GRANT SELECT ON ops.puerta TO role_support;
GRANT SELECT ON ops.vuelo TO role_support;
GRANT SELECT ON ops.vuelo_estado TO role_support;
GRANT SELECT ON ops.vuelo_demora TO role_support;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_support;
GRANT SELECT ON ops.plantilla_fids TO role_support;
GRANT SELECT ON ops.pantalla_fids TO role_support;

GRANT SELECT, UPDATE ON ops.terminal TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.puerta TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.vuelo TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.vuelo_estado TO role_tenant_admin;
GRANT SELECT, UPDATE ON ops.vuelo_demora TO role_tenant_admin;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_tenant_admin;
GRANT SELECT, INSERT, UPDATE ON ops.plantilla_fids TO role_tenant_admin;
GRANT SELECT, INSERT, UPDATE ON ops.pantalla_fids TO role_tenant_admin;

GRANT SELECT, INSERT, UPDATE ON ops.terminal TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.puerta TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_estado TO role_operations_controller;
GRANT SELECT, INSERT, UPDATE ON ops.vuelo_demora TO role_operations_controller;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_operations_controller;
GRANT SELECT ON ops.plantilla_fids TO role_operations_controller;
GRANT SELECT ON ops.pantalla_fids TO role_operations_controller;

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
GRANT SELECT ON ops.plantilla_fids TO role_elt_reader;
GRANT SELECT ON ops.pantalla_fids TO role_elt_reader;
GRANT SELECT ON ops.v_vuelo_estado_actual TO role_elt_reader;
