-- Privilegios sobre compliance.log_auditoria -- unica tabla existente en
-- este sprint (03_compliance_auditoria.sql). Matriz 4.3.1, columna
-- `compliance`, aplicable al subconjunto que ya existe:
--
--   role_platform_admin      U,S (la excepcion de escritura por break-glass
--                             es un procedimiento auditado, no un GRANT de
--                             motor -- se implementa cuando exista el resto
--                             de compliance, S1.7; conceder Up aqui violaria
--                             P5 para el caso comun)
--   role_sre                 U,S (el desglose especial de evidencia_soc2 y
--                             post_mortem/post_mortem_accion no aplica: esas
--                             tablas no existen hasta S1.7)
--   role_data_engineer       U,S (directo, NO via role_elt_reader -- la
--                             matriz lo lista aparte en esta columna)
--   role_regulatory_auditor  U,S
--   role_elt_reader          U,S (parte de "toda la base operacional")
--
-- INSERT sobre log_auditoria se resuelve aparte en 94_grants_continuidad.sql
-- (mismo problema, misma solucion, ver esa cabecera): todo rol que puede
-- mutar datos de negocio necesita poder escribir su propio evento de
-- auditoria en la misma transaccion, sin que eso implique poder LEER la
-- auditoria de otros ni, sobre todo, jamas UPDATE/DELETE (P5, RNF-S04).

GRANT SELECT ON compliance.log_auditoria TO role_platform_admin;
GRANT SELECT ON compliance.log_auditoria TO role_sre;
GRANT SELECT ON compliance.log_auditoria TO role_data_engineer;
GRANT SELECT ON compliance.log_auditoria TO role_regulatory_auditor;
GRANT SELECT ON compliance.log_auditoria TO role_elt_reader;

-- Fase 3 de docs/diseno/PLAN_CORRECCION_MODULOS.md (2026-08-07, item 8):
-- trazabilidad de tickets D6 -- "el hilo muestra mensajes, pero no los
-- cambios de estado ni quien los hizo". El dato ya existe aqui
-- (cambiar_estado_ticket registra cada transicion via registrar_auditoria);
-- faltaba el GRANT para poder leerlo. Se limita a los 2 roles que hoy
-- tienen el scope de aplicacion `support:leer` fuera de los roles de
-- plataforma ya otorgados arriba (role_tenant_admin, role_support) --
-- decision explicita del usuario (no ampliar a los 5 roles operativos que
-- carecen de support:leer, ver packages/contracts/aerohub_contracts/
-- roles_modulos.py). La consulta que lo usa
-- (aerohub_support.infrastructure.consultas::listar_transiciones_estado_ticket)
-- siempre filtra por esquema='support' AND tabla='ticket' AND
-- registro_id=<ticket puntual> -- el GRANT es table-wide (MonetDB no
-- tiene seguridad a nivel de fila), pero la aplicacion nunca ejecuta una
-- consulta mas amplia que esa contra esta tabla.
GRANT SELECT ON compliance.log_auditoria TO role_tenant_admin;
GRANT SELECT ON compliance.log_auditoria TO role_support;
