-- Esquema ops (D1) -- nucleo AODB (Sprint S1.1, Plan §8.1; SDD-DATA-001 §7).
-- `id` generado por la aplicacion (ver 01_catalogo.sql, cabecera).

CREATE TABLE ops.terminal (
    id         BIGINT NOT NULL PRIMARY KEY,
    tenant_id  BIGINT NOT NULL,
    codigo     VARCHAR(10) NOT NULL,
    nombre     VARCHAR(100) NOT NULL,
    CONSTRAINT fk_terminal_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT uq_terminal_tenant_codigo UNIQUE (tenant_id, codigo)
);

-- terminal_id corrige la dependencia transitiva 3NF de v5.1, donde la
-- terminal era texto libre en puerta (SDD-DATA-001 §7.2).
CREATE TABLE ops.puerta (
    id                  BIGINT NOT NULL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL,
    terminal_id         BIGINT NOT NULL,
    codigo              VARCHAR(10) NOT NULL,
    tipo                VARCHAR(20) NOT NULL,
    envergadura_max_m   DECIMAL(5,2) NOT NULL,
    tiene_pasarela      BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_puerta_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_puerta_terminal FOREIGN KEY (terminal_id) REFERENCES ops.terminal (id),
    CONSTRAINT uq_puerta_tenant_codigo UNIQUE (tenant_id, codigo),
    CONSTRAINT chk_puerta_tipo CHECK (tipo IN ('contacto', 'remota'))
);

-- Entidad nucleo del AODB. SIN estado_actual (el estado vigente se obtiene
-- de la vista v_vuelo_estado_actual sobre vuelo_estado, mas abajo) y SIN
-- ruta_id (origen-destino se deriva; solo se materializa como dimension
-- conformada en la capa analitica, SDD-DATA-002 dim_ruta) -- ambas
-- omisiones son 3NF deliberada, no un olvido (SDD-DATA-001 §7.3).
CREATE TABLE ops.vuelo (
    id                     BIGINT NOT NULL PRIMARY KEY,
    tenant_id              BIGINT NOT NULL,
    aerolinea_id           BIGINT NOT NULL,
    aeronave_id            BIGINT NOT NULL,
    numero_vuelo           VARCHAR(10) NOT NULL,
    tipo_vuelo_id          BIGINT NOT NULL,
    fecha_operacion        DATE NOT NULL,
    sentido                CHAR(1) NOT NULL,
    aeropuerto_origen_id   BIGINT NOT NULL,
    aeropuerto_destino_id  BIGINT NOT NULL,
    sta_utc                TIMESTAMP WITH TIME ZONE NOT NULL,
    std_utc                TIMESTAMP WITH TIME ZONE NOT NULL,
    eta_utc                TIMESTAMP WITH TIME ZONE,
    etd_utc                TIMESTAMP WITH TIME ZONE,
    ata_utc                TIMESTAMP WITH TIME ZONE,
    atd_utc                TIMESTAMP WITH TIME ZONE,
    pax_estimado           SMALLINT,
    creado_en              TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT fk_vuelo_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_vuelo_aerolinea FOREIGN KEY (aerolinea_id) REFERENCES catalogo.aerolinea (id),
    CONSTRAINT fk_vuelo_aeronave FOREIGN KEY (aeronave_id) REFERENCES catalogo.aeronave (id),
    CONSTRAINT fk_vuelo_tipo_vuelo FOREIGN KEY (tipo_vuelo_id) REFERENCES catalogo.tipo_vuelo (id),
    CONSTRAINT fk_vuelo_aeropuerto_origen FOREIGN KEY (aeropuerto_origen_id) REFERENCES catalogo.aeropuerto (id),
    CONSTRAINT fk_vuelo_aeropuerto_destino FOREIGN KEY (aeropuerto_destino_id) REFERENCES catalogo.aeropuerto (id),
    CONSTRAINT uq_vuelo_tenant_aerolinea_numero_fecha_sentido
        UNIQUE (tenant_id, aerolinea_id, numero_vuelo, fecha_operacion, sentido),
    CONSTRAINT chk_vuelo_sentido CHECK (sentido IN ('L', 'S')),
    CONSTRAINT chk_vuelo_aeropuertos_distintos CHECK (aeropuerto_origen_id <> aeropuerto_destino_id),
    CONSTRAINT chk_vuelo_pax_estimado CHECK (pax_estimado IS NULL OR pax_estimado >= 0)
);

CREATE INDEX idx_vuelo_tenant_fecha ON ops.vuelo (tenant_id, fecha_operacion);

-- Bitacora de eventos append-in-place (SDD-DATA-001 §7.4): el estado
-- vigente es el registro mas reciente por vuelo_id, resuelto por la vista
-- v_vuelo_estado_actual mas abajo -- nunca se hace UPDATE sobre una fila
-- existente de esta tabla.
CREATE TABLE ops.vuelo_estado (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    vuelo_id                    BIGINT NOT NULL,
    estado_id                   BIGINT NOT NULL,
    registrado_en               TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    registrado_por_usuario_id   BIGINT,
    origen_cambio               VARCHAR(20) NOT NULL,
    CONSTRAINT fk_vuelo_estado_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_vuelo_estado_vuelo FOREIGN KEY (vuelo_id) REFERENCES ops.vuelo (id),
    CONSTRAINT fk_vuelo_estado_estado FOREIGN KEY (estado_id) REFERENCES catalogo.estado_vuelo_catalogo (id),
    CONSTRAINT chk_vuelo_estado_origen_cambio CHECK (origen_cambio IN ('manual', 'api', 'automatico'))
);

-- MonetDB no acepta DESC en la lista de columnas de CREATE INDEX (motor
-- columnar: los indices son estructuras auxiliares -- imprints/zonemaps --
-- para el optimizador, no B-tree ordenados como en un motor de filas;
-- verificado empiricamente en S1.1). El nombre conserva "_desc" porque asi
-- lo fija SDD-DATA-001 §19 y documenta la intencion de consulta (mas
-- reciente primero), aunque el motor no imponga el orden fisico.
CREATE INDEX idx_vuelo_estado_tenant_vuelo_registrado_desc
    ON ops.vuelo_estado (tenant_id, vuelo_id, registrado_en);

-- 4NF (SDD-DATA-001 §7.6): un vuelo acumula motivos de demora
-- independientes de sus cambios de estado y de sus asignaciones de puerta;
-- se separan para evitar el producto cartesiano que produciria un modelo
-- plano.
CREATE TABLE ops.vuelo_demora (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    vuelo_id                    BIGINT NOT NULL,
    motivo_demora_id            BIGINT NOT NULL,
    minutos                     SMALLINT NOT NULL,
    registrado_en               TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    registrado_por_usuario_id   BIGINT,
    CONSTRAINT fk_vuelo_demora_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_vuelo_demora_vuelo FOREIGN KEY (vuelo_id) REFERENCES ops.vuelo (id),
    CONSTRAINT fk_vuelo_demora_motivo FOREIGN KEY (motivo_demora_id) REFERENCES catalogo.motivo_demora (id),
    CONSTRAINT chk_vuelo_demora_minutos CHECK (minutos > 0)
);

-- Estado vigente = registro mas reciente por vuelo_id (SDD-DATA-001 §7.3,
-- nota "Sin estado_actual"). MonetDB no soporta DISTINCT ON (extension de
-- Postgres); se resuelve con una subconsulta de maximo correlacionado,
-- portable a cualquier motor SQL estandar. `now()` en MonetDB tiene
-- precision de microsegundos (verificado en S1.1: dos filas insertadas en
-- la MISMA sentencia INSERT ya difieren en microsegundos), por lo que un
-- empate exacto en registrado_en es de probabilidad despreciable; no se
-- añade un desempate por id para no acoplar la vista al orden de
-- generacion de packages/kernel/identificador.py.
CREATE VIEW ops.v_vuelo_estado_actual AS
SELECT ve.tenant_id, ve.vuelo_id, ve.estado_id, ve.registrado_en,
       ve.registrado_por_usuario_id, ve.origen_cambio
FROM ops.vuelo_estado ve
WHERE ve.registrado_en = (
    SELECT MAX(ve2.registrado_en)
    FROM ops.vuelo_estado ve2
    WHERE ve2.vuelo_id = ve.vuelo_id
);
