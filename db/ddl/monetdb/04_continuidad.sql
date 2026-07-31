-- Esquema continuidad -- journal transaccional de continuidad operacional
-- (ADR-018, componente C1). No proviene de la SRS ni de los SDD; es la
-- respuesta de este proyecto a RNF-R01 (MonetDB sin PITR nativo).
--
-- `lsn` es la secuencia monotona de orden total (Log Sequence Number); la
-- entrada se escribe en la MISMA transaccion que la mutacion de negocio
-- (packages/repository/journal.py, principio P8) -- la atomicidad la
-- garantiza el motor: o se confirman ambas escrituras o ninguna.
--
-- Retencion 48h (ADR-018): el journal es el delta continuo entre snapshots
-- (componente C2), no el registro de auditoria de negocio -- esa
-- responsabilidad es de compliance.log_auditoria, con su propio ciclo de
-- vida y politica de retencion, deliberadamente desacoplado (ver ADR-018,
-- seccion "Por que un journal propio y no compliance.log_auditoria").
--
-- `lsn` generado por la aplicacion (packages/kernel/aerohub_kernel/
-- identificador.py), no por IDENTITY del motor -- mismo hallazgo empirico
-- de S0.2 que en 01_catalogo.sql/03_compliance_auditoria.sql. Con un unico
-- escritor (packages/repository es el unico emisor de SQL, P1), el orden
-- de generacion de GeneradorId coincide con el orden real de aplicacion;
-- ver el docstring de GeneradorId para el limite de esta garantia si algun
-- dia hubiera mas de un escritor concurrente.

CREATE TABLE continuidad.journal_mutacion (
    lsn               BIGINT NOT NULL PRIMARY KEY,
    esquema           VARCHAR(30) NOT NULL,
    tabla             VARCHAR(50) NOT NULL,
    operacion         VARCHAR(15) NOT NULL,
    clave_primaria    JSON NOT NULL,
    payload           JSON NOT NULL,
    tenant_id         BIGINT,
    ocurrido_en       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    checksum_sha256   CHAR(64) NOT NULL,
    CONSTRAINT chk_journal_mutacion_operacion CHECK (operacion IN ('INSERT', 'UPDATE', 'DELETE_LOGICO', 'DDL'))
);

-- Sin indice adicional sobre lsn: ya es la clave primaria (ADR-018 pide
-- "IDX (lsn)", redundante con la PK en un motor que ya indexa su PK).
