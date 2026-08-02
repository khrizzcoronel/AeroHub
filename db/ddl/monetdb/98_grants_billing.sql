-- Privilegios sobre billing.* -- matriz 4.3.1 (Analisis v6.0), columna
-- `billing`. U=USAGE se traduce como "sin grant adicional" (ver
-- 92_grants_tenants.sql). Nunca se otorga DELETE (SRS Sec2.6, P5): toda
-- baja es logica, gestionada por la aplicacion, no por el motor.
--
-- Solo 5 roles tienen ALGUN acceso a `billing` en la matriz 4.3.1: el
-- resto -- incluido role_support explicitamente -- tiene '-' en la
-- columna `billing` (segregacion de funciones, FR-008, compuerta de
-- pruebas obligatoria del sprint: NINGUNA linea de este archivo otorga
-- nada a role_support).
--
-- role_platform_admin: U,S.
-- role_tenant_admin: U,S (facturas propias) -- sin distincion adicional
--   de "propias" a nivel de motor (MonetDB no tiene RLS); se aplica en
--   aerohub_billing.infrastructure, mismo patron que role_ramp_agent en
--   S1.5.
-- role_airline_coordinator: U,S (sus cargos) -- idem, filtro en
--   infrastructure/.
-- role_operations_controller: U,S,I,Up sobre tiempo_espera_agregado
--   unicamente (M6, CU-O19 -- "Sistema" invoca el recalculo bajo este
--   rol, que por eso necesita escritura ahi; no participa de
--   facturacion, ver research.md Decision 4 de aerohub_passenger).
-- role_billing_officer: U,S,Up (disputas) -- UNICO rol con escritura
--   real sobre billing (INSERT via el motor de facturacion, que corre
--   como "Sistema" pero se autentica igual con un token de este rol;
--   UPDATE limitado a la transicion de disputa, aplicado en
--   aerohub_billing.application.disputar_factura, no en el motor).
-- role_elt_reader: U,S (tecnico, Airflow).

GRANT SELECT ON billing.concepto_cargo TO role_platform_admin;
GRANT SELECT ON billing.tarifario TO role_platform_admin;
GRANT SELECT ON billing.tarifario_concepto TO role_platform_admin;
GRANT SELECT ON billing.cargo_aeronautico TO role_platform_admin;
GRANT SELECT ON billing.factura TO role_platform_admin;
GRANT SELECT ON billing.factura_linea TO role_platform_admin;
GRANT SELECT ON billing.conciliacion_pax TO role_platform_admin;
GRANT SELECT ON billing.tiempo_espera_agregado TO role_platform_admin;

GRANT SELECT ON billing.concepto_cargo TO role_tenant_admin;
GRANT SELECT ON billing.tarifario TO role_tenant_admin;
GRANT SELECT ON billing.tarifario_concepto TO role_tenant_admin;
GRANT SELECT ON billing.cargo_aeronautico TO role_tenant_admin;
GRANT SELECT ON billing.factura TO role_tenant_admin;
GRANT SELECT ON billing.factura_linea TO role_tenant_admin;
GRANT SELECT ON billing.conciliacion_pax TO role_tenant_admin;

GRANT SELECT ON billing.concepto_cargo TO role_airline_coordinator;
GRANT SELECT ON billing.tarifario TO role_airline_coordinator;
GRANT SELECT ON billing.tarifario_concepto TO role_airline_coordinator;
GRANT SELECT ON billing.cargo_aeronautico TO role_airline_coordinator;
GRANT SELECT ON billing.factura TO role_airline_coordinator;
GRANT SELECT ON billing.factura_linea TO role_airline_coordinator;

GRANT SELECT, INSERT, UPDATE ON billing.tiempo_espera_agregado TO role_operations_controller;

GRANT SELECT ON billing.concepto_cargo TO role_billing_officer;
GRANT SELECT, INSERT, UPDATE ON billing.tarifario TO role_billing_officer;
GRANT SELECT, INSERT, UPDATE ON billing.tarifario_concepto TO role_billing_officer;
GRANT SELECT, INSERT ON billing.cargo_aeronautico TO role_billing_officer;
GRANT SELECT, INSERT, UPDATE ON billing.factura TO role_billing_officer;
GRANT SELECT, INSERT ON billing.factura_linea TO role_billing_officer;
GRANT SELECT, INSERT, UPDATE ON billing.conciliacion_pax TO role_billing_officer;

GRANT SELECT ON billing.concepto_cargo TO role_elt_reader;
GRANT SELECT ON billing.tarifario TO role_elt_reader;
GRANT SELECT ON billing.tarifario_concepto TO role_elt_reader;
GRANT SELECT ON billing.cargo_aeronautico TO role_elt_reader;
GRANT SELECT ON billing.factura TO role_elt_reader;
GRANT SELECT ON billing.factura_linea TO role_elt_reader;
GRANT SELECT ON billing.conciliacion_pax TO role_elt_reader;
GRANT SELECT ON billing.tiempo_espera_agregado TO role_elt_reader;

-- role_ramp_agent escribe rampa.turnaround, cuya duracion real alimenta
-- CU-O19 (tiempo de espera) -- pero NO participa de la escritura de
-- tiempo_espera_agregado (eso es "Sistema" via role_operations_controller
-- o role_platform_admin); solo necesita, si acaso, lectura de su propio
-- modulo, ya cubierta por 97_grants_rampa.sql -- sin grant nuevo aqui.
