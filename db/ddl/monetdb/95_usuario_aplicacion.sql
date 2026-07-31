-- Usuario tecnico de conexion para packages/repository (P1: unico emisor
-- de SQL hacia MonetDB).
--
-- Diseno (S0.2): un unico login de aplicacion, miembro de los 16 roles,
-- que activa el rol correcto por sesion via SET ROLE segun el rol_actor del
-- contexto de la peticion (verificado por el JWT del Gateway, nunca elegido
-- libremente por el cliente). El aislamiento departamental NO depende de
-- login separados por rol -- depende de que SET ROLE se ejecute siempre y
-- de que el guardian (ADR-019) audite/bloquee su ausencia u omision.
--
-- La contrasena de bootstrap de este archivo es SOLO para desarrollo local
-- (coherente con las credenciales de docker-compose.yml). Un entorno real
-- debe rotarla inmediatamente tras el aprovisionamiento -- no se disena
-- aqui un mecanismo de inyeccion de secretos externo: es responsabilidad
-- de la infraestructura de despliegue (fuera de alcance de S0.2).

CREATE USER "aerohub_app" WITH PASSWORD 'aerohub_app_dev_password' NAME 'AeroHub — usuario tecnico de aplicacion' SCHEMA catalogo;

GRANT role_platform_admin TO "aerohub_app";
GRANT role_sre TO "aerohub_app";
GRANT role_data_engineer TO "aerohub_app";
GRANT role_ml_engineer TO "aerohub_app";
GRANT role_implementation TO "aerohub_app";
GRANT role_support TO "aerohub_app";
GRANT role_business_viewer TO "aerohub_app";
GRANT role_tenant_admin TO "aerohub_app";
GRANT role_operations_controller TO "aerohub_app";
GRANT role_airline_coordinator TO "aerohub_app";
GRANT role_ramp_agent TO "aerohub_app";
GRANT role_billing_officer TO "aerohub_app";
GRANT role_tenant_analyst TO "aerohub_app";
GRANT role_regulatory_auditor TO "aerohub_app";
GRANT role_people_viewer TO "aerohub_app";
GRANT role_elt_reader TO "aerohub_app";
