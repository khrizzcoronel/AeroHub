-- Esquema compliance (D5) -- SOLO log_auditoria en este sprint.
--
-- Decision de S0.2: adelantar exclusivamente log_auditoria desde su sprint
-- normativo (S1.7, Plan §8.7) porque P8 (journal en la misma transaccion
-- que la mutacion) y audit.py exigen una tabla de auditoria funcionando
-- desde el primer commit de codigo de negocio -- de lo contrario ninguna
-- mutacion de las fases 1-3 tendria cobertura de auditoria retroactiva.
-- El resto de compliance (incidente_seguridad, reporte_dgac, acceso_auditor,
-- post_mortem, post_mortem_accion, control_soc2, evidencia_soc2) permanece
-- en S1.7 (SDD-DATA-001 §10).
--
-- Append-only por diseno (P5, RNF-S04): ningun rol recibe UPDATE ni DELETE
-- sobre esta tabla (ver 93_grants_compliance.sql / 94_grants_continuidad.sql).
-- Al carecer MonetDB de triggers equivalentes a los de un motor con soporte
-- nativo, la garantia de invariancia depende del guardian de
-- packages/repository, no del motor.
--
-- `usuario_id` SIN FOREIGN KEY a tenants.usuario -- desviacion deliberada
-- de SDD-DATA-001 §10.1, que si declara esa FK. Hallazgo empirico de S0.2:
-- esta tabla se escribe bajo CUALQUIERA de los 16 roles activados por
-- SET ROLE (94_grants_continuidad.sql); una FK hacia un esquema (`tenants`)
-- al que la mayoria de esos roles no tiene acceso hace fallar el INSERT
-- para TODOS ellos, incluso el mas privilegiado -- MonetDB deniega el
-- acceso a la fila referenciada durante la validacion de la FK sin
-- respetar el rol activo de la sesion (ver packages/kernel/aerohub_kernel/
-- identificador.py para el hallazgo relacionado sobre secuencias bajo
-- SET ROLE; docs/runbooks/monetdb.md documenta ambos). La integridad de
-- `usuario_id` se verifica en la aplicacion: el valor proviene siempre del
-- JWT ya validado por el Gateway, no de entrada arbitraria.

-- 'DENEGADO' se agrego en S1.2 (PN-06): un intento de autenticacion con
-- API Key revocada o expirada no es una mutacion de datos (INSERT/UPDATE/
-- DELETE sobre la fila de negocio), pero SI debe quedar auditado -- es el
-- unico caso de esta tabla donde `registro_id` apunta a la fila cuyo
-- ACCESO se denego, no a una fila que se escribio.
CREATE TABLE compliance.log_auditoria (
    id                   BIGINT NOT NULL PRIMARY KEY,
    tenant_id            BIGINT,
    esquema              VARCHAR(30) NOT NULL,
    tabla                VARCHAR(50) NOT NULL,
    registro_id          BIGINT NOT NULL,
    operacion            VARCHAR(10) NOT NULL,
    usuario_id           BIGINT,
    rol_codigo           VARCHAR(50) NOT NULL,
    ocurrido_en          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    valores_anteriores   JSON,
    valores_nuevos       JSON,
    ip_origen            VARCHAR(45),
    CONSTRAINT chk_log_auditoria_operacion
        CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE', 'DENEGADO'))
);

CREATE INDEX idx_log_auditoria_tenant_ocurrido ON compliance.log_auditoria (tenant_id, ocurrido_en);
