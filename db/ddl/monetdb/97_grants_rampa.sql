-- Privilegios sobre rampa.* -- matriz 4.3.1 (Analisis v6.0), columna
-- `rampa`. U=USAGE se traduce como "sin grant adicional" (ver
-- 92_grants_tenants.sql). Nunca se otorga DELETE (SRS §2.6, P5): toda baja
-- es logica, gestionada por la aplicacion, no por el motor.
--
-- Solo 5 roles tienen ALGUN acceso a `rampa` en la matriz 4.3.1: el resto
-- (role_sre, role_ml_engineer, role_implementation, role_support,
-- role_business_viewer, role_airline_coordinator, role_billing_officer,
-- role_tenant_analyst, role_regulatory_auditor, role_people_viewer) tiene
-- '-' en la columna `rampa` -- sin acceso.
--
-- role_platform_admin: U,S.
-- role_tenant_admin: U,S.
-- role_operations_controller: U,S.
-- role_elt_reader: U,S (tecnico, Airflow).
-- role_ramp_agent: U,S,I,Up -- el UNICO rol con escritura en `rampa` segun
-- la matriz. La matriz no distingue "crear turnaround" de "registrar
-- tiempos de tarea" como responsabilidades separadas (no existe un CU-O15
-- o equivalente de "crear turnaround" en el catalogo de casos de uso,
-- SRS/Analisis v6.0) -- sin otro rol con I/Up sobre `rampa.turnaround`,
-- role_ramp_agent tambien crea el turnaround, ademas de registrar sus
-- tareas (CU-O16) y las incidencias que estas generan automaticamente
-- (RF-O16, sincronico dentro de la misma transaccion de
-- aerohub_ramp.application.finalizar_tarea).
--
-- Los catalogos tipo_tarea/tipo_incidencia_rampa (datos de referencia,
-- estandar de industria, ver 11_rampa.sql) son de solo lectura para
-- role_ramp_agent -- ningun caso de uso de S1.5 los modifica en tiempo de
-- ejecucion; su mantenimiento queda para role_platform_admin (via consola
-- administrativa fuera de alcance de este sprint, mismo tratamiento que
-- catalogo.tipo_vuelo).

GRANT SELECT ON rampa.tipo_tarea TO role_platform_admin;
GRANT SELECT ON rampa.tipo_incidencia_rampa TO role_platform_admin;
GRANT SELECT ON rampa.turnaround TO role_platform_admin;
GRANT SELECT ON rampa.tarea_turnaround TO role_platform_admin;
GRANT SELECT ON rampa.incidencia_rampa TO role_platform_admin;

GRANT SELECT ON rampa.tipo_tarea TO role_tenant_admin;
GRANT SELECT ON rampa.tipo_incidencia_rampa TO role_tenant_admin;
GRANT SELECT ON rampa.turnaround TO role_tenant_admin;
GRANT SELECT ON rampa.tarea_turnaround TO role_tenant_admin;
GRANT SELECT ON rampa.incidencia_rampa TO role_tenant_admin;

GRANT SELECT ON rampa.tipo_tarea TO role_operations_controller;
GRANT SELECT ON rampa.tipo_incidencia_rampa TO role_operations_controller;
GRANT SELECT ON rampa.turnaround TO role_operations_controller;
GRANT SELECT ON rampa.tarea_turnaround TO role_operations_controller;
GRANT SELECT ON rampa.incidencia_rampa TO role_operations_controller;

GRANT SELECT ON rampa.tipo_tarea TO role_elt_reader;
GRANT SELECT ON rampa.tipo_incidencia_rampa TO role_elt_reader;
GRANT SELECT ON rampa.turnaround TO role_elt_reader;
GRANT SELECT ON rampa.tarea_turnaround TO role_elt_reader;
GRANT SELECT ON rampa.incidencia_rampa TO role_elt_reader;

GRANT SELECT ON rampa.tipo_tarea TO role_ramp_agent;
GRANT SELECT ON rampa.tipo_incidencia_rampa TO role_ramp_agent;
GRANT SELECT, INSERT, UPDATE ON rampa.turnaround TO role_ramp_agent;
GRANT SELECT, INSERT, UPDATE ON rampa.tarea_turnaround TO role_ramp_agent;
GRANT SELECT, INSERT, UPDATE ON rampa.incidencia_rampa TO role_ramp_agent;
