-- Esquemas de la base operacional (Sprint S0.2, Plan §7.2).
--
-- La SRS v2.0 §7.1 nombra 8 esquemas (tenants, ops, rampa, billing,
-- compliance, support, people, etl_control) y "los diez catalogos globales
-- de referencia sin tenant_id" como una categoria aparte, sin asignarles
-- nombre de esquema explicito. Decision de S0.2 (documentada, no implicita):
-- los catalogos viven en el esquema `catalogo`.
--
-- `continuidad` es una adicion de ADR-018 (C1, journal transaccional de
-- continuidad operacional); no proviene de la SRS.
--
-- Solo `catalogo`, `tenants`, `compliance` y `continuidad` reciben tablas en
-- este sprint. `ops`, `rampa`, `billing`, `support`, `people`, `etl_control`
-- se crean vacios: sus tablas llegan en las fases 1-3 (ver Plan §12).

CREATE SCHEMA catalogo;
CREATE SCHEMA tenants;
CREATE SCHEMA compliance;
CREATE SCHEMA continuidad;

CREATE SCHEMA ops;
CREATE SCHEMA rampa;
CREATE SCHEMA billing;
CREATE SCHEMA support;
CREATE SCHEMA people;
CREATE SCHEMA etl_control;
