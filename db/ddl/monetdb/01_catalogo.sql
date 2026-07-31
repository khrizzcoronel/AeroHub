-- Catalogos globales de referencia, sin tenant_id (SDD-DATA-001 §5).
-- Datos de industria compartidos: duplicarlos por tenant introduciria
-- anomalias de actualizacion sin beneficio de aislamiento (SDD-001 §5).
--
-- Tipos conforme a SDD-DATA-001 §4. `id` como BIGINT **generado por la
-- aplicacion** (packages/kernel/aerohub_kernel/identificador.py), no por
-- secuencia del motor: `GENERATED ALWAYS AS IDENTITY` resulto incompatible
-- con el modelo de SET ROLE de este proyecto (ver packages/kernel/
-- aerohub_kernel/identificador.py, docstring, para el hallazgo empirico de
-- S0.2). Nunca reutilizado; no se expone como clave de negocio -- las
-- claves candidatas naturales (codigo_iata, etc.) llevan su propio UNIQUE.
--
-- Los `id` fijos 1..N de este archivo son la unica excepcion: filas de
-- referencia estaticas, sembradas por esta migracion (no por la app en
-- tiempo de ejecucion), sin riesgo de colision con los id de 60+ bits que
-- genera GeneradorId.

CREATE TABLE catalogo.pais (
    id          BIGINT NOT NULL PRIMARY KEY,
    codigo_iso2 CHAR(2) NOT NULL,
    codigo_iso3 CHAR(3) NOT NULL,
    nombre      VARCHAR(100) NOT NULL,
    CONSTRAINT uq_pais_codigo_iso2 UNIQUE (codigo_iso2),
    CONSTRAINT uq_pais_codigo_iso3 UNIQUE (codigo_iso3)
);

CREATE TABLE catalogo.aeropuerto (
    id            BIGINT NOT NULL PRIMARY KEY,
    codigo_iata   CHAR(3) NOT NULL,
    codigo_icao   CHAR(4) NOT NULL,
    nombre        VARCHAR(150) NOT NULL,
    pais_id       BIGINT NOT NULL,
    ciudad        VARCHAR(100) NOT NULL,
    zona_horaria  VARCHAR(50) NOT NULL,
    latitud       DECIMAL(9,6) NOT NULL,
    longitud      DECIMAL(9,6) NOT NULL,
    CONSTRAINT uq_aeropuerto_codigo_iata UNIQUE (codigo_iata),
    CONSTRAINT uq_aeropuerto_codigo_icao UNIQUE (codigo_icao),
    CONSTRAINT fk_aeropuerto_pais FOREIGN KEY (pais_id) REFERENCES catalogo.pais (id),
    CONSTRAINT chk_aeropuerto_latitud CHECK (latitud BETWEEN -90 AND 90),
    CONSTRAINT chk_aeropuerto_longitud CHECK (longitud BETWEEN -180 AND 180)
);

CREATE TABLE catalogo.aerolinea (
    id          BIGINT NOT NULL PRIMARY KEY,
    codigo_iata CHAR(2) NOT NULL,
    codigo_icao CHAR(3) NOT NULL,
    nombre      VARCHAR(150) NOT NULL,
    pais_id     BIGINT NOT NULL,
    CONSTRAINT uq_aerolinea_codigo_iata UNIQUE (codigo_iata),
    CONSTRAINT uq_aerolinea_codigo_icao UNIQUE (codigo_icao),
    CONSTRAINT fk_aerolinea_pais FOREIGN KEY (pais_id) REFERENCES catalogo.pais (id)
);

CREATE TABLE catalogo.modelo_aeronave (
    id                    BIGINT NOT NULL PRIMARY KEY,
    codigo_icao_tipo      VARCHAR(4) NOT NULL,
    fabricante            VARCHAR(100) NOT NULL,
    modelo                VARCHAR(100) NOT NULL,
    capacidad_pax_tipica  SMALLINT NOT NULL,
    envergadura_m         DECIMAL(5,2) NOT NULL,
    categoria_estela      CHAR(1) NOT NULL,
    CONSTRAINT uq_modelo_aeronave_codigo_icao_tipo UNIQUE (codigo_icao_tipo),
    CONSTRAINT chk_modelo_aeronave_capacidad_pax_tipica CHECK (capacidad_pax_tipica > 0),
    CONSTRAINT chk_modelo_aeronave_categoria_estela CHECK (categoria_estela IN ('L', 'M', 'H', 'J'))
);

CREATE TABLE catalogo.aeronave (
    id                  BIGINT NOT NULL PRIMARY KEY,
    matricula           VARCHAR(10) NOT NULL,
    modelo_aeronave_id  BIGINT NOT NULL,
    aerolinea_id        BIGINT NOT NULL,
    CONSTRAINT uq_aeronave_matricula UNIQUE (matricula),
    CONSTRAINT fk_aeronave_modelo_aeronave FOREIGN KEY (modelo_aeronave_id) REFERENCES catalogo.modelo_aeronave (id),
    CONSTRAINT fk_aeronave_aerolinea FOREIGN KEY (aerolinea_id) REFERENCES catalogo.aerolinea (id)
);

CREATE TABLE catalogo.tipo_vuelo (
    id           BIGINT NOT NULL PRIMARY KEY,
    codigo       VARCHAR(20) NOT NULL,
    descripcion  VARCHAR(100) NOT NULL,
    CONSTRAINT uq_tipo_vuelo_codigo UNIQUE (codigo),
    CONSTRAINT chk_tipo_vuelo_codigo CHECK (codigo IN ('comercial', 'carga', 'charter', 'aviacion_general', 'militar'))
);

CREATE TABLE catalogo.motivo_demora (
    id           BIGINT NOT NULL PRIMARY KEY,
    codigo_iata  CHAR(2) NOT NULL,
    descripcion  VARCHAR(200) NOT NULL,
    categoria    VARCHAR(50) NOT NULL,
    CONSTRAINT uq_motivo_demora_codigo_iata UNIQUE (codigo_iata)
);

CREATE TABLE catalogo.estado_vuelo_catalogo (
    id           BIGINT NOT NULL PRIMARY KEY,
    codigo       VARCHAR(20) NOT NULL,
    descripcion  VARCHAR(100) NOT NULL,
    es_terminal  BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT uq_estado_vuelo_catalogo_codigo UNIQUE (codigo)
);

CREATE TABLE catalogo.departamento (
    id      BIGINT NOT NULL PRIMARY KEY,
    codigo  CHAR(2) NOT NULL,
    nombre  VARCHAR(100) NOT NULL,
    CONSTRAINT uq_departamento_codigo UNIQUE (codigo)
);

CREATE TABLE catalogo.modulo (
    id                BIGINT NOT NULL PRIMARY KEY,
    codigo            VARCHAR(4) NOT NULL,
    nombre            VARCHAR(100) NOT NULL,
    departamento_id   BIGINT NOT NULL,
    CONSTRAINT uq_modulo_codigo UNIQUE (codigo),
    CONSTRAINT fk_modulo_departamento FOREIGN KEY (departamento_id) REFERENCES catalogo.departamento (id)
);

-- Departamentos D1-D6 (Analisis v6.0 §4.1) -- catalogo fijo, no sintetico.
INSERT INTO catalogo.departamento (id, codigo, nombre) VALUES
    (1, 'D1', 'Direccion de Operaciones Aeroportuarias'),
    (2, 'D2', 'Ground Operations (Rampa)'),
    (3, 'D3', 'Crecimiento Comercial y Finanzas'),
    (4, 'D4', 'Datos e Inteligencia Artificial'),
    (5, 'D5', 'Plataforma y Seguridad'),
    (6, 'D6', 'Soporte e Implementacion (DevRel)');

-- Modulos M1-M9 (SRS v2.0 §2.2) -- catalogo fijo, referenciado desde
-- tenants.plan_modulo y tenants.licencia (S0.2).
INSERT INTO catalogo.modulo (id, codigo, nombre, departamento_id) VALUES
    (1, 'M1', 'AODB', 1),
    (2, 'M2', 'FIDS Management', 1),
    (3, 'M3', 'Terminal & Gate Manager', 1),
    (4, 'M4', 'Ground Operations', 2),
    (5, 'M5', 'Revenue & Billing', 3),
    (6, 'M6', 'Passenger Experience', 1),
    (7, 'M7', 'ETL & Analytics', 4),
    (8, 'M8', 'Observability', 5),
    (9, 'M9', 'Compliance Hub', 5);

-- tipo_vuelo: dominio CERRADO por el propio CHECK de la tabla (SDD-001
-- §5.6) -- a diferencia de aeropuerto/aerolinea/aeronave (industria real,
-- se cargan por importacion, ver db/seeds/generate.py), estos 5 valores
-- son fijos y agotan el dominio; se siembran aqui, no en un seed aparte.
INSERT INTO catalogo.tipo_vuelo (id, codigo, descripcion) VALUES
    (1, 'comercial', 'Vuelo comercial de pasajeros'),
    (2, 'carga', 'Vuelo de carga'),
    (3, 'charter', 'Vuelo charter'),
    (4, 'aviacion_general', 'Aviacion general'),
    (5, 'militar', 'Vuelo militar');
