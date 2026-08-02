-- Esquema billing (D3, Tarifacion y Facturacion) -- M5 Revenue & Billing +
-- M6 Passenger Experience (Sprint S1.6, Plan Sec8.6; SDD-DATA-001 Sec9).
-- `id` generado por la aplicacion (ver 01_catalogo.sql, cabecera).

-- Catalogo global (sin tenant_id): los conceptos facturables (tasa de
-- aterrizaje, uso de manga, estacionamiento, tasa por pasajero) son
-- estandar de industria, no configuracion por tenant -- mismo principio
-- que catalogo.tipo_vuelo y rampa.tipo_tarea.
CREATE TABLE billing.concepto_cargo (
    id              BIGINT NOT NULL PRIMARY KEY,
    codigo          VARCHAR(30) NOT NULL,
    nombre          VARCHAR(150) NOT NULL,
    unidad_medida   VARCHAR(20) NOT NULL,
    base_calculo    VARCHAR(30) NOT NULL,
    CONSTRAINT uq_concepto_cargo_codigo UNIQUE (codigo),
    CONSTRAINT chk_concepto_cargo_base_calculo
        CHECK (base_calculo IN ('peso_mtow', 'pax', 'tiempo_estacionamiento', 'uso_pasarela', 'fijo'))
);

-- Cabecera de tarifario: vigencia y moneda separadas de los precios por
-- concepto (2NF respecto a v5.1, SDD-DATA-001 Sec9.2). "A lo sumo un
-- tarifario vigente por (tenant_id, moneda)" es una regla de dominio
-- validada en aerohub_billing.application, no expresable como CHECK/UNIQUE
-- de MonetDB (no soporta EXCLUDE, mismo hallazgo que S1.4).
CREATE TABLE billing.tarifario (
    id                      BIGINT NOT NULL PRIMARY KEY,
    tenant_id               BIGINT NOT NULL,
    nombre                  VARCHAR(100) NOT NULL,
    moneda                  CHAR(3) NOT NULL,
    vigente_desde           DATE NOT NULL,
    vigente_hasta           DATE,
    estado                  VARCHAR(20) NOT NULL,
    creado_por_usuario_id   BIGINT NOT NULL,
    CONSTRAINT fk_tarifario_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_tarifario_creado_por FOREIGN KEY (creado_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_tarifario_vigente_hasta
        CHECK (vigente_hasta IS NULL OR vigente_hasta >= vigente_desde),
    CONSTRAINT chk_tarifario_estado
        CHECK (estado IN ('borrador', 'vigente', 'expirado'))
);

-- Resuelve la relacion ternaria tarifario-concepto-precio en 5NF, sin
-- descomposicion adicional posible sin perdida (SDD-DATA-001 Sec9.3).
-- Habilita RF-T10 (tarifas configurables) sin desplegar codigo nuevo.
CREATE TABLE billing.tarifario_concepto (
    id                  BIGINT NOT NULL PRIMARY KEY,
    tarifario_id        BIGINT NOT NULL,
    concepto_cargo_id   BIGINT NOT NULL,
    tarifa_unitaria     DECIMAL(14,4) NOT NULL,
    monto_minimo        DECIMAL(14,2),
    monto_maximo        DECIMAL(14,2),
    CONSTRAINT fk_tarifario_concepto_tarifario FOREIGN KEY (tarifario_id) REFERENCES billing.tarifario (id),
    CONSTRAINT fk_tarifario_concepto_concepto FOREIGN KEY (concepto_cargo_id) REFERENCES billing.concepto_cargo (id),
    CONSTRAINT uq_tarifario_concepto_tarifario_concepto UNIQUE (tarifario_id, concepto_cargo_id),
    CONSTRAINT chk_tarifario_concepto_tarifa_unitaria CHECK (tarifa_unitaria >= 0),
    CONSTRAINT chk_tarifario_concepto_monto_maximo
        CHECK (monto_minimo IS NULL OR monto_maximo IS NULL OR monto_maximo >= monto_minimo)
);

-- Instantanea inmutable de un hecho facturable ya calculado (CU-O17).
-- tarifa_aplicada y monto_calculado son DENORMALIZACION DELIBERADA: no se
-- recalculan desde tarifario_concepto -- si la tarifa vigente cambia
-- despues, el cargo historico y la factura emitida no se alteran
-- (integridad financiera y de auditoria, ISO/IEC 27002 8.15,
-- SDD-DATA-001 Sec9.4).
CREATE TABLE billing.cargo_aeronautico (
    id                      BIGINT NOT NULL PRIMARY KEY,
    tenant_id               BIGINT NOT NULL,
    vuelo_id                BIGINT NOT NULL,
    concepto_cargo_id       BIGINT NOT NULL,
    tarifario_concepto_id   BIGINT NOT NULL,
    cantidad                DECIMAL(12,2) NOT NULL,
    tarifa_aplicada         DECIMAL(14,4) NOT NULL,
    monto_calculado         DECIMAL(14,2) NOT NULL,
    calculado_en            TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT fk_cargo_aeronautico_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_cargo_aeronautico_vuelo FOREIGN KEY (vuelo_id) REFERENCES ops.vuelo (id),
    CONSTRAINT fk_cargo_aeronautico_concepto FOREIGN KEY (concepto_cargo_id) REFERENCES billing.concepto_cargo (id),
    CONSTRAINT fk_cargo_aeronautico_tarifario_concepto
        FOREIGN KEY (tarifario_concepto_id) REFERENCES billing.tarifario_concepto (id),
    CONSTRAINT uq_cargo_aeronautico_vuelo_concepto UNIQUE (vuelo_id, concepto_cargo_id),
    CONSTRAINT chk_cargo_aeronautico_cantidad CHECK (cantidad > 0)
);

CREATE INDEX idx_cargo_aeronautico_tenant_vuelo ON billing.cargo_aeronautico (tenant_id, vuelo_id);

-- factura SIN columna total (3NF, SDD-DATA-001 Sec9.5): se obtiene por
-- agregacion de factura_linea en aerohub_billing.infrastructure.
CREATE TABLE billing.factura (
    id                  BIGINT NOT NULL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL,
    aerolinea_id        BIGINT NOT NULL,
    periodo_inicio      DATE NOT NULL,
    periodo_fin         DATE NOT NULL,
    moneda              CHAR(3) NOT NULL,
    estado              VARCHAR(20) NOT NULL,
    emitida_en          TIMESTAMP WITH TIME ZONE,
    vence_en            TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_factura_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_factura_aerolinea FOREIGN KEY (aerolinea_id) REFERENCES catalogo.aerolinea (id),
    CONSTRAINT uq_factura_tenant_aerolinea_periodo
        UNIQUE (tenant_id, aerolinea_id, periodo_inicio, periodo_fin),
    CONSTRAINT chk_factura_periodo_fin CHECK (periodo_fin >= periodo_inicio),
    CONSTRAINT chk_factura_estado
        CHECK (estado IN ('borrador', 'emitida', 'pagada', 'vencida', 'disputada'))
);

-- precio_unitario/monto: DENORMALIZACION DELIBERADA, evidencia contable
-- congelada -- copiados de cargo_aeronautico en el momento de facturar,
-- nunca derivados en lectura (SDD-DATA-001 Sec9.6).
CREATE TABLE billing.factura_linea (
    id                      BIGINT NOT NULL PRIMARY KEY,
    factura_id              BIGINT NOT NULL,
    cargo_aeronautico_id    BIGINT NOT NULL,
    descripcion             VARCHAR(200) NOT NULL,
    cantidad                DECIMAL(12,2) NOT NULL,
    precio_unitario         DECIMAL(14,4) NOT NULL,
    monto                   DECIMAL(14,2) NOT NULL,
    CONSTRAINT fk_factura_linea_factura FOREIGN KEY (factura_id) REFERENCES billing.factura (id),
    CONSTRAINT fk_factura_linea_cargo_aeronautico
        FOREIGN KEY (cargo_aeronautico_id) REFERENCES billing.cargo_aeronautico (id),
    -- Un cargo se factura una sola vez (edge case de spec.md: dos lineas
    -- no pueden referenciar el mismo cargo_aeronautico_id).
    CONSTRAINT uq_factura_linea_cargo_aeronautico UNIQUE (cargo_aeronautico_id)
);

CREATE INDEX idx_factura_linea_factura ON billing.factura_linea (factura_id);

-- conciliacion_pax SIN columna diferencia (3NF, SDD-DATA-001 Sec9.7):
-- derivada de pax_reportado_aerolinea - pax_registrado_sistema en
-- aerohub_billing.infrastructure.
CREATE TABLE billing.conciliacion_pax (
    id                              BIGINT NOT NULL PRIMARY KEY,
    tenant_id                       BIGINT NOT NULL,
    vuelo_id                        BIGINT NOT NULL,
    periodo                         VARCHAR(7) NOT NULL,
    pax_reportado_aerolinea         SMALLINT NOT NULL,
    pax_registrado_sistema          SMALLINT NOT NULL,
    fuente_reporte                  VARCHAR(50) NOT NULL,
    conciliado_en                   TIMESTAMP WITH TIME ZONE,
    conciliado_por_usuario_id       BIGINT,
    CONSTRAINT fk_conciliacion_pax_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_conciliacion_pax_vuelo FOREIGN KEY (vuelo_id) REFERENCES ops.vuelo (id),
    CONSTRAINT fk_conciliacion_pax_conciliado_por
        FOREIGN KEY (conciliado_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT uq_conciliacion_pax_tenant_vuelo_periodo UNIQUE (tenant_id, vuelo_id, periodo),
    CONSTRAINT chk_conciliacion_pax_reportado CHECK (pax_reportado_aerolinea >= 0),
    CONSTRAINT chk_conciliacion_pax_registrado CHECK (pax_registrado_sistema >= 0)
);

-- Modulo M6 (RF-O17) -- propiedad de aerohub_passenger, no de
-- aerohub_billing, aunque viva en este esquema SQL (ver
-- specs/008-billing-passenger-experience/research.md, Decision 3). SIN
-- ningun atributo que identifique a un pasajero (RNF-S05, verificado por
-- PN-11, SDD-DATA-001 Sec9.8).
CREATE TABLE billing.tiempo_espera_agregado (
    id                  BIGINT NOT NULL PRIMARY KEY,
    tenant_id           BIGINT NOT NULL,
    terminal_id         BIGINT NOT NULL,
    fecha               DATE NOT NULL,
    franja_inicio       TIME NOT NULL,
    franja_fin          TIME NOT NULL,
    minutos_estimados   DECIMAL(6,2) NOT NULL,
    muestra_n           INTEGER NOT NULL,
    calculado_en        TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT fk_tiempo_espera_agregado_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_tiempo_espera_agregado_terminal FOREIGN KEY (terminal_id) REFERENCES ops.terminal (id),
    CONSTRAINT uq_tiempo_espera_agregado_tenant_terminal_fecha_franja
        UNIQUE (tenant_id, terminal_id, fecha, franja_inicio),
    CONSTRAINT chk_tiempo_espera_agregado_franja_fin CHECK (franja_fin > franja_inicio),
    CONSTRAINT chk_tiempo_espera_agregado_minutos_estimados CHECK (minutos_estimados >= 0),
    CONSTRAINT chk_tiempo_espera_agregado_muestra_n CHECK (muestra_n >= 0)
);

CREATE INDEX idx_tiempo_espera_agregado_tenant_terminal_fecha
    ON billing.tiempo_espera_agregado (tenant_id, terminal_id, fecha);
