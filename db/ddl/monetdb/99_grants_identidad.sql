-- Privilegios sobre las 4 tablas nuevas de identidad (Sprint S1.10).
-- `sesion`/`token_acceso`/`intento_acceso` son alcance G1 'interno': los
-- flujos que las tocan (login, invitacion, verificacion, recuperacion)
-- corren bajo alcance_global(rol="role_platform_admin") por no existir
-- tenant en contexto todavia (research.md Decision 3) -- ese es el unico
-- rol que necesita escribirlas. `invitacion` es alcance 'tenant': la crea
-- y consulta un role_tenant_admin ya autenticado dentro de su propio
-- tenant.
--
-- Ningun rol recibe DELETE -- ninguna de las 4 tablas tiene mecanismo de
-- purga fisica en este sprint (P5: nunca se otorga DELETE salvo
-- excepcion documentada, y esta no aplica aqui).

GRANT SELECT, INSERT, UPDATE ON tenants.sesion TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.token_acceso TO role_platform_admin;
GRANT SELECT, INSERT ON tenants.intento_acceso TO role_platform_admin;

GRANT SELECT, INSERT, UPDATE ON tenants.invitacion TO role_platform_admin;
GRANT SELECT, INSERT, UPDATE ON tenants.invitacion TO role_tenant_admin;

-- Diagnostico de soporte/SRE sobre intentos de acceso, mismo criterio que
-- la lectura de journal_mutacion (94_grants_continuidad.sql).
GRANT SELECT ON tenants.intento_acceso TO role_sre;
GRANT SELECT ON tenants.intento_acceso TO role_support;
