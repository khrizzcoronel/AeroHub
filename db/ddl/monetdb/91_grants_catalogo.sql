-- Privilegios sobre catalogo.* -- SOLO SELECT, para los 16 roles.
--
-- Decision de S0.2: los catalogos son "Publico / interno; sin tenant_id;
-- no sujetos a control de aislamiento" (SDD-DATA-001 §18). La matriz 4.3.1
-- no lista una columna "catalogo" (solo cubre los 8 esquemas de la SRS);
-- dado que casi cualquier tabla operacional referencia un catalogo por FK
-- (aeropuerto, aerolinea, modelo_aeronave...), se otorga SELECT amplio a
-- los 16 roles en vez de replicar la logica de FK de cada esquema futuro
-- aqui. Sin riesgo de aislamiento: son datos de referencia, no de negocio
-- por tenant. Nunca se otorga INSERT/UPDATE/DELETE via rol -- los catalogos
-- se mantienen por migracion versionada (db/ddl), no por escritura en
-- tiempo de ejecucion de ningun actor.

GRANT SELECT ON catalogo.pais TO role_platform_admin;
GRANT SELECT ON catalogo.pais TO role_sre;
GRANT SELECT ON catalogo.pais TO role_data_engineer;
GRANT SELECT ON catalogo.pais TO role_ml_engineer;
GRANT SELECT ON catalogo.pais TO role_implementation;
GRANT SELECT ON catalogo.pais TO role_support;
GRANT SELECT ON catalogo.pais TO role_business_viewer;
GRANT SELECT ON catalogo.pais TO role_tenant_admin;
GRANT SELECT ON catalogo.pais TO role_operations_controller;
GRANT SELECT ON catalogo.pais TO role_airline_coordinator;
GRANT SELECT ON catalogo.pais TO role_ramp_agent;
GRANT SELECT ON catalogo.pais TO role_billing_officer;
GRANT SELECT ON catalogo.pais TO role_tenant_analyst;
GRANT SELECT ON catalogo.pais TO role_regulatory_auditor;
GRANT SELECT ON catalogo.pais TO role_people_viewer;
GRANT SELECT ON catalogo.pais TO role_elt_reader;

GRANT SELECT ON catalogo.aeropuerto TO role_platform_admin;
GRANT SELECT ON catalogo.aeropuerto TO role_sre;
GRANT SELECT ON catalogo.aeropuerto TO role_data_engineer;
GRANT SELECT ON catalogo.aeropuerto TO role_ml_engineer;
GRANT SELECT ON catalogo.aeropuerto TO role_implementation;
GRANT SELECT ON catalogo.aeropuerto TO role_support;
GRANT SELECT ON catalogo.aeropuerto TO role_business_viewer;
GRANT SELECT ON catalogo.aeropuerto TO role_tenant_admin;
GRANT SELECT ON catalogo.aeropuerto TO role_operations_controller;
GRANT SELECT ON catalogo.aeropuerto TO role_airline_coordinator;
GRANT SELECT ON catalogo.aeropuerto TO role_ramp_agent;
GRANT SELECT ON catalogo.aeropuerto TO role_billing_officer;
GRANT SELECT ON catalogo.aeropuerto TO role_tenant_analyst;
GRANT SELECT ON catalogo.aeropuerto TO role_regulatory_auditor;
GRANT SELECT ON catalogo.aeropuerto TO role_people_viewer;
GRANT SELECT ON catalogo.aeropuerto TO role_elt_reader;

GRANT SELECT ON catalogo.aerolinea TO role_platform_admin;
GRANT SELECT ON catalogo.aerolinea TO role_sre;
GRANT SELECT ON catalogo.aerolinea TO role_data_engineer;
GRANT SELECT ON catalogo.aerolinea TO role_ml_engineer;
GRANT SELECT ON catalogo.aerolinea TO role_implementation;
GRANT SELECT ON catalogo.aerolinea TO role_support;
GRANT SELECT ON catalogo.aerolinea TO role_business_viewer;
GRANT SELECT ON catalogo.aerolinea TO role_tenant_admin;
GRANT SELECT ON catalogo.aerolinea TO role_operations_controller;
GRANT SELECT ON catalogo.aerolinea TO role_airline_coordinator;
GRANT SELECT ON catalogo.aerolinea TO role_ramp_agent;
GRANT SELECT ON catalogo.aerolinea TO role_billing_officer;
GRANT SELECT ON catalogo.aerolinea TO role_tenant_analyst;
GRANT SELECT ON catalogo.aerolinea TO role_regulatory_auditor;
GRANT SELECT ON catalogo.aerolinea TO role_people_viewer;
GRANT SELECT ON catalogo.aerolinea TO role_elt_reader;

GRANT SELECT ON catalogo.modelo_aeronave TO role_platform_admin;
GRANT SELECT ON catalogo.modelo_aeronave TO role_sre;
GRANT SELECT ON catalogo.modelo_aeronave TO role_data_engineer;
GRANT SELECT ON catalogo.modelo_aeronave TO role_ml_engineer;
GRANT SELECT ON catalogo.modelo_aeronave TO role_implementation;
GRANT SELECT ON catalogo.modelo_aeronave TO role_support;
GRANT SELECT ON catalogo.modelo_aeronave TO role_business_viewer;
GRANT SELECT ON catalogo.modelo_aeronave TO role_tenant_admin;
GRANT SELECT ON catalogo.modelo_aeronave TO role_operations_controller;
GRANT SELECT ON catalogo.modelo_aeronave TO role_airline_coordinator;
GRANT SELECT ON catalogo.modelo_aeronave TO role_ramp_agent;
GRANT SELECT ON catalogo.modelo_aeronave TO role_billing_officer;
GRANT SELECT ON catalogo.modelo_aeronave TO role_tenant_analyst;
GRANT SELECT ON catalogo.modelo_aeronave TO role_regulatory_auditor;
GRANT SELECT ON catalogo.modelo_aeronave TO role_people_viewer;
GRANT SELECT ON catalogo.modelo_aeronave TO role_elt_reader;

GRANT SELECT ON catalogo.aeronave TO role_platform_admin;
GRANT SELECT ON catalogo.aeronave TO role_sre;
GRANT SELECT ON catalogo.aeronave TO role_data_engineer;
GRANT SELECT ON catalogo.aeronave TO role_ml_engineer;
GRANT SELECT ON catalogo.aeronave TO role_implementation;
GRANT SELECT ON catalogo.aeronave TO role_support;
GRANT SELECT ON catalogo.aeronave TO role_business_viewer;
GRANT SELECT ON catalogo.aeronave TO role_tenant_admin;
GRANT SELECT ON catalogo.aeronave TO role_operations_controller;
GRANT SELECT ON catalogo.aeronave TO role_airline_coordinator;
GRANT SELECT ON catalogo.aeronave TO role_ramp_agent;
GRANT SELECT ON catalogo.aeronave TO role_billing_officer;
GRANT SELECT ON catalogo.aeronave TO role_tenant_analyst;
GRANT SELECT ON catalogo.aeronave TO role_regulatory_auditor;
GRANT SELECT ON catalogo.aeronave TO role_people_viewer;
GRANT SELECT ON catalogo.aeronave TO role_elt_reader;

GRANT SELECT ON catalogo.tipo_vuelo TO role_platform_admin;
GRANT SELECT ON catalogo.tipo_vuelo TO role_sre;
GRANT SELECT ON catalogo.tipo_vuelo TO role_data_engineer;
GRANT SELECT ON catalogo.tipo_vuelo TO role_ml_engineer;
GRANT SELECT ON catalogo.tipo_vuelo TO role_implementation;
GRANT SELECT ON catalogo.tipo_vuelo TO role_support;
GRANT SELECT ON catalogo.tipo_vuelo TO role_business_viewer;
GRANT SELECT ON catalogo.tipo_vuelo TO role_tenant_admin;
GRANT SELECT ON catalogo.tipo_vuelo TO role_operations_controller;
GRANT SELECT ON catalogo.tipo_vuelo TO role_airline_coordinator;
GRANT SELECT ON catalogo.tipo_vuelo TO role_ramp_agent;
GRANT SELECT ON catalogo.tipo_vuelo TO role_billing_officer;
GRANT SELECT ON catalogo.tipo_vuelo TO role_tenant_analyst;
GRANT SELECT ON catalogo.tipo_vuelo TO role_regulatory_auditor;
GRANT SELECT ON catalogo.tipo_vuelo TO role_people_viewer;
GRANT SELECT ON catalogo.tipo_vuelo TO role_elt_reader;

GRANT SELECT ON catalogo.motivo_demora TO role_platform_admin;
GRANT SELECT ON catalogo.motivo_demora TO role_sre;
GRANT SELECT ON catalogo.motivo_demora TO role_data_engineer;
GRANT SELECT ON catalogo.motivo_demora TO role_ml_engineer;
GRANT SELECT ON catalogo.motivo_demora TO role_implementation;
GRANT SELECT ON catalogo.motivo_demora TO role_support;
GRANT SELECT ON catalogo.motivo_demora TO role_business_viewer;
GRANT SELECT ON catalogo.motivo_demora TO role_tenant_admin;
GRANT SELECT ON catalogo.motivo_demora TO role_operations_controller;
GRANT SELECT ON catalogo.motivo_demora TO role_airline_coordinator;
GRANT SELECT ON catalogo.motivo_demora TO role_ramp_agent;
GRANT SELECT ON catalogo.motivo_demora TO role_billing_officer;
GRANT SELECT ON catalogo.motivo_demora TO role_tenant_analyst;
GRANT SELECT ON catalogo.motivo_demora TO role_regulatory_auditor;
GRANT SELECT ON catalogo.motivo_demora TO role_people_viewer;
GRANT SELECT ON catalogo.motivo_demora TO role_elt_reader;

GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_platform_admin;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_sre;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_data_engineer;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_ml_engineer;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_implementation;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_support;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_business_viewer;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_tenant_admin;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_operations_controller;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_airline_coordinator;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_ramp_agent;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_billing_officer;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_tenant_analyst;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_regulatory_auditor;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_people_viewer;
GRANT SELECT ON catalogo.estado_vuelo_catalogo TO role_elt_reader;

GRANT SELECT ON catalogo.departamento TO role_platform_admin;
GRANT SELECT ON catalogo.departamento TO role_sre;
GRANT SELECT ON catalogo.departamento TO role_data_engineer;
GRANT SELECT ON catalogo.departamento TO role_ml_engineer;
GRANT SELECT ON catalogo.departamento TO role_implementation;
GRANT SELECT ON catalogo.departamento TO role_support;
GRANT SELECT ON catalogo.departamento TO role_business_viewer;
GRANT SELECT ON catalogo.departamento TO role_tenant_admin;
GRANT SELECT ON catalogo.departamento TO role_operations_controller;
GRANT SELECT ON catalogo.departamento TO role_airline_coordinator;
GRANT SELECT ON catalogo.departamento TO role_ramp_agent;
GRANT SELECT ON catalogo.departamento TO role_billing_officer;
GRANT SELECT ON catalogo.departamento TO role_tenant_analyst;
GRANT SELECT ON catalogo.departamento TO role_regulatory_auditor;
GRANT SELECT ON catalogo.departamento TO role_people_viewer;
GRANT SELECT ON catalogo.departamento TO role_elt_reader;

GRANT SELECT ON catalogo.modulo TO role_platform_admin;
GRANT SELECT ON catalogo.modulo TO role_sre;
GRANT SELECT ON catalogo.modulo TO role_data_engineer;
GRANT SELECT ON catalogo.modulo TO role_ml_engineer;
GRANT SELECT ON catalogo.modulo TO role_implementation;
GRANT SELECT ON catalogo.modulo TO role_support;
GRANT SELECT ON catalogo.modulo TO role_business_viewer;
GRANT SELECT ON catalogo.modulo TO role_tenant_admin;
GRANT SELECT ON catalogo.modulo TO role_operations_controller;
GRANT SELECT ON catalogo.modulo TO role_airline_coordinator;
GRANT SELECT ON catalogo.modulo TO role_ramp_agent;
GRANT SELECT ON catalogo.modulo TO role_billing_officer;
GRANT SELECT ON catalogo.modulo TO role_tenant_analyst;
GRANT SELECT ON catalogo.modulo TO role_regulatory_auditor;
GRANT SELECT ON catalogo.modulo TO role_people_viewer;
GRANT SELECT ON catalogo.modulo TO role_elt_reader;
