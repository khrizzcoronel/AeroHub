-- Migra tenants.usuario de unicidad de correo POR TENANT a unicidad
-- GLOBAL (Sprint S1.10, research.md Decision 2): una persona existe en un
-- unico tenant; el login no pide codigo de tenant.
--
-- Verificado empiricamente contra MonetDB real antes de escribir el plan:
-- ALTER TABLE ... DROP CONSTRAINT y ALTER TABLE ... ADD CONSTRAINT ...
-- UNIQUE funcionan (aplica igual sobre la base nueva creada por
-- 02_tenants.sql con la restriccion vieja, y sobre una base existente con
-- datos reales).
--
-- Salvaguarda (Principio V -- migracion destructiva sobre datos reales):
-- si existiera algun correo duplicado entre tenants, el ADD CONSTRAINT de
-- abajo fallaria con el error crudo del motor a mitad de aplicar el
-- archivo. `tools/verificar_colisiones_email.py` DEBE correr antes y
-- abortar con un informe legible si encuentra alguna, en vez de dejar que
-- este archivo falle a ciegas.

ALTER TABLE tenants.usuario DROP CONSTRAINT uq_usuario_tenant_email;
ALTER TABLE tenants.usuario ADD CONSTRAINT uq_usuario_email UNIQUE (email);
