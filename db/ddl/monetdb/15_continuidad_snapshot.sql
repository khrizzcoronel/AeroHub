-- Esquema continuidad (ampliacion) -- snapshot programado, checkpoint del
-- shipper y prueba de restauracion (ADR-018, componentes C2/C3/C4;
-- Sprint S1.9). continuidad.journal_mutacion YA EXISTE desde S0.2
-- (04_continuidad.sql) -- este archivo agrega el resto del esquema. `id`
-- generado por la aplicacion (ver 01_catalogo.sql, cabecera). Se aplica
-- IDENTICO al primario, al standby y al contenedor de prueba de
-- restauracion (specs/011-continuidad-rto-rpo/research.md Decision 5).

CREATE TABLE continuidad.snapshot_base (
    id                BIGINT NOT NULL PRIMARY KEY,
    tipo              VARCHAR(20) NOT NULL,
    lsn_corte         BIGINT NOT NULL,
    generado_en       TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    ruta_artefacto    VARCHAR(500) NOT NULL,
    hash_artefacto    CHAR(64) NOT NULL,
    estado            VARCHAR(20) NOT NULL,
    verificado_en     TIMESTAMP WITH TIME ZONE,
    CONSTRAINT chk_snapshot_base_tipo CHECK (tipo IN ('programado', 'volcado_diario')),
    CONSTRAINT chk_snapshot_base_estado CHECK (estado IN ('generado', 'verificado', 'corrupto'))
);

CREATE INDEX idx_snapshot_base_generado_en ON continuidad.snapshot_base (generado_en);

-- Una fila logica por replica de respaldo (hoy, una sola: el standby) --
-- UPDATE en cada ciclo exitoso del shipper, no INSERT-only (a diferencia
-- del resto del esquema).
CREATE TABLE continuidad.shipper_checkpoint (
    id                    BIGINT NOT NULL PRIMARY KEY,
    standby_nombre        VARCHAR(50) NOT NULL,
    ultimo_lsn_aplicado    BIGINT NOT NULL DEFAULT 0,
    actualizado_en         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_shipper_checkpoint_standby UNIQUE (standby_nombre)
);

-- Append-only -- evidencia acumulada de cada ejecucion semanal (RF-O09,
-- spec.md SC-004). Nunca se actualiza ni se borra.
CREATE TABLE continuidad.prueba_restauracion (
    id                          BIGINT NOT NULL PRIMARY KEY,
    snapshot_id                 BIGINT NOT NULL,
    ejecutado_en                 TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    rto_observado_segundos        INTEGER NOT NULL,
    rpo_observado_segundos        INTEGER NOT NULL,
    resultado                     VARCHAR(20) NOT NULL,
    detalle                       VARCHAR(500),
    CONSTRAINT fk_prueba_restauracion_snapshot FOREIGN KEY (snapshot_id) REFERENCES continuidad.snapshot_base (id),
    CONSTRAINT chk_prueba_restauracion_resultado CHECK (resultado IN ('exitosa', 'fallida')),
    CONSTRAINT chk_prueba_restauracion_rto CHECK (rto_observado_segundos >= 0),
    CONSTRAINT chk_prueba_restauracion_rpo CHECK (rpo_observado_segundos >= 0)
);

CREATE INDEX idx_prueba_restauracion_ejecutado_en ON continuidad.prueba_restauracion (ejecutado_en);
