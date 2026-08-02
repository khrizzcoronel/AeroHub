-- Privilegios sobre las tablas nuevas de continuidad (S1.9): snapshot_base,
-- shipper_checkpoint, prueba_restauracion. No provienen de la matriz 4.3.1
-- (ninguna es una tabla de negocio de un esquema departamental) -- son
-- infraestructura transversal de plataforma, misma categoria que
-- 94_grants_continuidad.sql.
--
-- role_platform_admin: unico escritor -- `continuidad-agente` corre bajo
-- este rol via alcance_global() (specs/011-continuidad-rto-rpo/research.md
-- Decision 3), tanto para catalogar snapshots como para actualizar el
-- checkpoint del shipper y registrar cada prueba de restauracion.
-- role_sre / role_data_engineer / role_elt_reader: SELECT de diagnostico,
-- mismo criterio que la lectura de journal_mutacion en
-- 94_grants_continuidad.sql.
--
-- EXCEPCION explicita a "nunca se otorga DELETE" (P5, valido para datos de
-- NEGOCIO): `journal_mutacion` tiene una ventana de retencion de 48h por
-- diseno desde su creacion (ADR-018, 04_continuidad.sql) -- sin una baja
-- fisica real, esa retencion nunca se cumpliria. Se otorga DELETE
-- UNICAMENTE a role_platform_admin (el rol bajo el cual corre el ciclo de
-- purga de `continuidad-agente`, alcance_global) y UNICAMENTE sobre esta
-- tabla -- ninguna otra tabla de este archivo ni de ningun otro esquema
-- recibe DELETE. `snapshot_base`/`shipper_checkpoint`/`prueba_restauracion`
-- no tienen mecanismo de borrado propio (prueba_restauracion es
-- append-only por diseno).

GRANT SELECT, INSERT, UPDATE ON continuidad.snapshot_base TO role_platform_admin;
GRANT SELECT, INSERT ON continuidad.shipper_checkpoint TO role_platform_admin;
GRANT UPDATE ON continuidad.shipper_checkpoint TO role_platform_admin;
GRANT SELECT, INSERT ON continuidad.prueba_restauracion TO role_platform_admin;
GRANT DELETE ON continuidad.journal_mutacion TO role_platform_admin;

GRANT SELECT ON continuidad.snapshot_base TO role_sre;
GRANT SELECT ON continuidad.shipper_checkpoint TO role_sre;
GRANT SELECT ON continuidad.prueba_restauracion TO role_sre;

GRANT SELECT ON continuidad.snapshot_base TO role_data_engineer;
GRANT SELECT ON continuidad.shipper_checkpoint TO role_data_engineer;
GRANT SELECT ON continuidad.prueba_restauracion TO role_data_engineer;

GRANT SELECT ON continuidad.snapshot_base TO role_elt_reader;
GRANT SELECT ON continuidad.shipper_checkpoint TO role_elt_reader;
GRANT SELECT ON continuidad.prueba_restauracion TO role_elt_reader;
