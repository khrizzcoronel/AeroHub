-- Privilegios sobre compliance.log_auditoria (INSERT) y
-- continuidad.journal_mutacion -- no provienen de la matriz 4.3.1 (ninguna
-- de las dos es una tabla de negocio de un esquema departamental); son
-- infraestructura transversal que P8 exige desde el primer commit.
--
-- Problema real de diseno (hallazgo de S0.2, ver ADR-018): SET ROLE en
-- MonetDB activa un unico rol por sesion (verificado empiricamente). Una
-- mutacion de negocio corre bajo el rol especifico del actor (p. ej.
-- role_operations_controller insertando en ops.vuelo); packages/repository
-- escribe el journal y la auditoria en la MISMA transaccion (P8), bajo esa
-- misma sesion -- por tanto CADA rol que puede mutar cualquier dato de
-- negocio, presente o futuro, necesita poder escribir (INSERT, nunca
-- SELECT/UPDATE/DELETE) su propia entrada de auditoria y de journal. Negarlo
-- no evita la escritura de datos de negocio: solo produce una mutacion sin
-- rastro de auditoria, el peor resultado posible bajo RNF-S04.
--
-- Se otorga a los 16 roles (incluso los que hoy no mutan nada, como
-- role_tenant_analyst) porque la alternativa -- ampliar este archivo en
-- cada sprint que le da escritura nueva a un rol -- multiplica el riesgo de
-- olvidar uno y dejar un hueco de auditoria silencioso.
--
-- SELECT sobre continuidad.journal_mutacion es OTRA decision: el journal no
-- tiene el filtro de tenant del guardian aplicado en lectura (no es una
-- vista de negocio, es el outbox interno de ADR-018) y su payload cruza
-- tenants sin acotar. Ampliar su lectura a roles de alcance tenant
-- (role_tenant_admin, role_billing_officer, etc.) filtrarian datos de otros
-- tenants por una via que el guardian no cubre. Se restringe a los roles de
-- plataforma con responsabilidad de diagnostico.

GRANT INSERT ON compliance.log_auditoria TO role_platform_admin;
GRANT INSERT ON compliance.log_auditoria TO role_sre;
GRANT INSERT ON compliance.log_auditoria TO role_data_engineer;
GRANT INSERT ON compliance.log_auditoria TO role_ml_engineer;
GRANT INSERT ON compliance.log_auditoria TO role_implementation;
GRANT INSERT ON compliance.log_auditoria TO role_support;
GRANT INSERT ON compliance.log_auditoria TO role_business_viewer;
GRANT INSERT ON compliance.log_auditoria TO role_tenant_admin;
GRANT INSERT ON compliance.log_auditoria TO role_operations_controller;
GRANT INSERT ON compliance.log_auditoria TO role_airline_coordinator;
GRANT INSERT ON compliance.log_auditoria TO role_ramp_agent;
GRANT INSERT ON compliance.log_auditoria TO role_billing_officer;
GRANT INSERT ON compliance.log_auditoria TO role_tenant_analyst;
GRANT INSERT ON compliance.log_auditoria TO role_regulatory_auditor;
GRANT INSERT ON compliance.log_auditoria TO role_people_viewer;
GRANT INSERT ON compliance.log_auditoria TO role_elt_reader;

GRANT INSERT ON continuidad.journal_mutacion TO role_platform_admin;
GRANT INSERT ON continuidad.journal_mutacion TO role_sre;
GRANT INSERT ON continuidad.journal_mutacion TO role_data_engineer;
GRANT INSERT ON continuidad.journal_mutacion TO role_ml_engineer;
GRANT INSERT ON continuidad.journal_mutacion TO role_implementation;
GRANT INSERT ON continuidad.journal_mutacion TO role_support;
GRANT INSERT ON continuidad.journal_mutacion TO role_business_viewer;
GRANT INSERT ON continuidad.journal_mutacion TO role_tenant_admin;
GRANT INSERT ON continuidad.journal_mutacion TO role_operations_controller;
GRANT INSERT ON continuidad.journal_mutacion TO role_airline_coordinator;
GRANT INSERT ON continuidad.journal_mutacion TO role_ramp_agent;
GRANT INSERT ON continuidad.journal_mutacion TO role_billing_officer;
GRANT INSERT ON continuidad.journal_mutacion TO role_tenant_analyst;
GRANT INSERT ON continuidad.journal_mutacion TO role_regulatory_auditor;
GRANT INSERT ON continuidad.journal_mutacion TO role_people_viewer;
GRANT INSERT ON continuidad.journal_mutacion TO role_elt_reader;

-- SELECT restringido a diagnostico de plataforma.
GRANT SELECT ON continuidad.journal_mutacion TO role_platform_admin;
GRANT SELECT ON continuidad.journal_mutacion TO role_sre;
