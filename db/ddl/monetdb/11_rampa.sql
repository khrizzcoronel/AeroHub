-- Esquema rampa (D2) -- M4 Ground Operations / turnaround (Sprint S1.5,
-- Plan §8.5; SDD-DATA-001 §8). `id` generado por la aplicacion (ver
-- 01_catalogo.sql, cabecera).

-- Catalogos globales del dominio de rampa (sin tenant_id): los tipos de
-- tarea e incidencia son estandar de industria, no configuracion por
-- tenant (mismo principio que catalogo.tipo_vuelo/aerolinea). Viven en el
-- esquema `rampa`, no en `catalogo`, porque asi los nombra el Plan §8.5 y
-- la SDD §8.1-8.2 -- son catalogos DE este modulo, no transversales a
-- todos los modulos.
CREATE TABLE rampa.tipo_tarea (
    id                      BIGINT NOT NULL PRIMARY KEY,
    codigo                  VARCHAR(20) NOT NULL,
    nombre                  VARCHAR(100) NOT NULL,
    duracion_estandar_min   SMALLINT NOT NULL,
    es_ruta_critica         BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_tipo_tarea_codigo UNIQUE (codigo),
    CONSTRAINT chk_tipo_tarea_duracion_estandar_min CHECK (duracion_estandar_min > 0)
);

CREATE TABLE rampa.tipo_incidencia_rampa (
    id            BIGINT NOT NULL PRIMARY KEY,
    codigo        VARCHAR(20) NOT NULL,
    descripcion   VARCHAR(150) NOT NULL,
    CONSTRAINT uq_tipo_incidencia_rampa_codigo UNIQUE (codigo)
);

-- Entidad nueva de v6.0 (SDD-DATA-001 §8.3): en v5.1 las tareas colgaban
-- directamente del vuelo, sin representar el emparejamiento llegada->salida
-- que define un turnaround; se inferia por convencion. Aqui es explicito y
-- verificable: cada turnaround empareja DOS filas de ops.vuelo (una con
-- sentido='L', otra con sentido='S') de la MISMA aeronave.
CREATE TABLE rampa.turnaround (
    id                  BIGINT NOT NULL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL,
    vuelo_llegada_id    BIGINT NOT NULL,
    vuelo_salida_id     BIGINT NOT NULL,
    aeronave_id         BIGINT NOT NULL,
    inicio_previsto     TIMESTAMP WITH TIME ZONE NOT NULL,
    fin_previsto        TIMESTAMP WITH TIME ZONE NOT NULL,
    inicio_real         TIMESTAMP WITH TIME ZONE,
    fin_real            TIMESTAMP WITH TIME ZONE,
    estado              VARCHAR(20) NOT NULL,
    CONSTRAINT fk_turnaround_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_turnaround_vuelo_llegada FOREIGN KEY (vuelo_llegada_id) REFERENCES ops.vuelo (id),
    CONSTRAINT fk_turnaround_vuelo_salida FOREIGN KEY (vuelo_salida_id) REFERENCES ops.vuelo (id),
    CONSTRAINT fk_turnaround_aeronave FOREIGN KEY (aeronave_id) REFERENCES catalogo.aeronave (id),
    CONSTRAINT uq_turnaround_tenant_vuelo_llegada UNIQUE (tenant_id, vuelo_llegada_id),
    CONSTRAINT chk_turnaround_vuelos_distintos CHECK (vuelo_llegada_id <> vuelo_salida_id),
    CONSTRAINT chk_turnaround_intervalo CHECK (fin_previsto > inicio_previsto),
    CONSTRAINT chk_turnaround_estado
        CHECK (estado IN ('planificado', 'en_curso', 'completado', 'interrumpido'))
);

-- La duracion de cada tarea se DERIVA de fin_real - inicio_real; no se
-- almacena (3NF, SDD-DATA-001 §8.4) -- aerohub_ramp.domain la calcula al
-- vuelo, nunca se persiste una columna de duracion.
--
-- agente_usuario_id es NOT NULL: a diferencia de asignacion_puerta (S1.4),
-- que existe INDEPENDIENTE de quien la crea, una fila de tarea_turnaround
-- SOLO se crea cuando un agente de rampa "marca inicio" (CU-O16, paso 2:
-- "el sistema registra el timestamp y el usuario") -- no hay tareas
-- pre-creadas sin agente esperando ser reclamadas en el alcance de S1.5.
CREATE TABLE rampa.tarea_turnaround (
    id                      BIGINT NOT NULL PRIMARY KEY,
    tenant_id               BIGINT NOT NULL,
    turnaround_id           BIGINT NOT NULL,
    tipo_tarea_id           BIGINT NOT NULL,
    agente_usuario_id       BIGINT NOT NULL,
    inicio_real             TIMESTAMP WITH TIME ZONE,
    fin_real                TIMESTAMP WITH TIME ZONE,
    estado                  VARCHAR(20) NOT NULL,
    CONSTRAINT fk_tarea_turnaround_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_tarea_turnaround_turnaround
        FOREIGN KEY (turnaround_id) REFERENCES rampa.turnaround (id),
    CONSTRAINT fk_tarea_turnaround_tipo_tarea
        FOREIGN KEY (tipo_tarea_id) REFERENCES rampa.tipo_tarea (id),
    CONSTRAINT fk_tarea_turnaround_agente FOREIGN KEY (agente_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_tarea_turnaround_estado
        CHECK (estado IN ('pendiente', 'en_curso', 'completada', 'omitida')),
    CONSTRAINT chk_tarea_turnaround_fin_real_posterior
        CHECK (fin_real IS NULL OR inicio_real IS NULL OR fin_real >= inicio_real)
);

CREATE INDEX idx_tarea_turnaround_tenant_turnaround
    ON rampa.tarea_turnaround (tenant_id, turnaround_id);

-- Sustenta RF-O16 y OP2b (SDD-DATA-001 §8.5). Sin columna numerica de
-- desviacion (minutos_desviacion): el SDD no la modela -- la magnitud
-- queda en `descripcion` (texto), igual que otros modulos guardan detalle
-- libre en vez de estructurarlo cuando el SDD no exige lo segundo.
CREATE TABLE rampa.incidencia_rampa (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    tarea_turnaround_id         BIGINT NOT NULL,
    tipo_incidencia_id          BIGINT NOT NULL,
    descripcion                 VARCHAR(300) NOT NULL,
    severidad                   VARCHAR(10) NOT NULL,
    detectada_en                TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    resuelta_en                 TIMESTAMP WITH TIME ZONE,
    resuelta_por_usuario_id     BIGINT,
    CONSTRAINT fk_incidencia_rampa_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_incidencia_rampa_tarea
        FOREIGN KEY (tarea_turnaround_id) REFERENCES rampa.tarea_turnaround (id),
    CONSTRAINT fk_incidencia_rampa_tipo
        FOREIGN KEY (tipo_incidencia_id) REFERENCES rampa.tipo_incidencia_rampa (id),
    CONSTRAINT fk_incidencia_rampa_resuelta_por
        FOREIGN KEY (resuelta_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_incidencia_rampa_severidad
        CHECK (severidad IN ('baja', 'media', 'alta', 'critica'))
);

CREATE INDEX idx_incidencia_rampa_tenant_tarea
    ON rampa.incidencia_rampa (tenant_id, tarea_turnaround_id);
