-- Esquema compliance (D5) -- S1.7 Licenciamiento, credenciales y
-- Compliance Hub (Plan Sec8.7; SDD-DATA-001 Sec10.2-10.10).
-- compliance.log_auditoria YA EXISTE desde S0.2 (03_compliance_auditoria.sql)
-- -- este archivo agrega el resto del esquema. `id` generado por la
-- aplicacion (ver 01_catalogo.sql, cabecera).

-- Catalogo global (sin tenant_id).
CREATE TABLE compliance.tipo_incidente (
    id            BIGINT NOT NULL PRIMARY KEY,
    codigo        VARCHAR(30) NOT NULL,
    descripcion   VARCHAR(200) NOT NULL,
    categoria     VARCHAR(50) NOT NULL,
    CONSTRAINT uq_tipo_incidente_codigo UNIQUE (codigo)
);

-- Append-only (PN-04 reforzada) -- sin metodo de UPDATE/DELETE expuesto
-- por aerohub_compliance.infrastructure.
CREATE TABLE compliance.incidente_seguridad (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    tipo_incidente_id           BIGINT NOT NULL,
    descripcion                 VARCHAR(500) NOT NULL,
    severidad                   VARCHAR(10) NOT NULL,
    detectado_en                TIMESTAMP WITH TIME ZONE NOT NULL,
    reportado_por_usuario_id    BIGINT NOT NULL,
    estado                      VARCHAR(20) NOT NULL,
    CONSTRAINT fk_incidente_seguridad_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_incidente_seguridad_tipo FOREIGN KEY (tipo_incidente_id) REFERENCES compliance.tipo_incidente (id),
    CONSTRAINT fk_incidente_seguridad_reportado_por FOREIGN KEY (reportado_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_incidente_seguridad_severidad
        CHECK (severidad IN ('baja', 'media', 'alta', 'critica')),
    CONSTRAINT chk_incidente_seguridad_estado
        CHECK (estado IN ('abierto', 'en_investigacion', 'contenido', 'cerrado'))
);

CREATE INDEX idx_incidente_seguridad_tenant ON compliance.incidente_seguridad (tenant_id);

-- Catalogo global.
CREATE TABLE compliance.tipo_reporte_regulatorio (
    id             BIGINT NOT NULL PRIMARY KEY,
    codigo         VARCHAR(30) NOT NULL,
    nombre         VARCHAR(150) NOT NULL,
    periodicidad   VARCHAR(20) NOT NULL,
    autoridad      VARCHAR(20) NOT NULL,
    CONSTRAINT uq_tipo_reporte_regulatorio_codigo UNIQUE (codigo),
    CONSTRAINT chk_tipo_reporte_regulatorio_autoridad CHECK (autoridad IN ('DGAC', 'OACI'))
);

-- Append-only.
CREATE TABLE compliance.reporte_dgac (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    tipo_reporte_id             BIGINT NOT NULL,
    periodo_inicio               DATE NOT NULL,
    periodo_fin                  DATE NOT NULL,
    contenido_ref                VARCHAR(500) NOT NULL,
    hash_contenido                CHAR(64) NOT NULL,
    emitido_por_usuario_id        BIGINT NOT NULL,
    emitido_en                    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT fk_reporte_dgac_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_reporte_dgac_tipo FOREIGN KEY (tipo_reporte_id) REFERENCES compliance.tipo_reporte_regulatorio (id),
    CONSTRAINT fk_reporte_dgac_emitido_por FOREIGN KEY (emitido_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_reporte_dgac_periodo_fin CHECK (periodo_fin >= periodo_inicio)
);

CREATE INDEX idx_reporte_dgac_tenant ON compliance.reporte_dgac (tenant_id);

-- Append-only.
CREATE TABLE compliance.acceso_auditor (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    auditor_usuario_id          BIGINT NOT NULL,
    otorgado_por_usuario_id     BIGINT NOT NULL,
    inicio                       TIMESTAMP WITH TIME ZONE NOT NULL,
    fin                          TIMESTAMP WITH TIME ZONE NOT NULL,
    alcance_json                 JSON NOT NULL,
    motivo                       VARCHAR(300) NOT NULL,
    CONSTRAINT fk_acceso_auditor_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_acceso_auditor_auditor FOREIGN KEY (auditor_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT fk_acceso_auditor_otorgado_por FOREIGN KEY (otorgado_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_acceso_auditor_fin CHECK (fin > inicio)
);

CREATE INDEX idx_acceso_auditor_tenant ON compliance.acceso_auditor (tenant_id);

-- Unica tabla del esquema con UPDATE permitido -- excepcion controlada
-- (ADR-009), exclusiva de role_sre, aplicada en application/ (MonetDB no
-- tiene RLS). Toda edicion de causa_raiz/estado queda tambien en
-- compliance.log_auditoria (FR-007).
CREATE TABLE compliance.post_mortem (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT,
    incidente_ref                VARCHAR(100) NOT NULL,
    severidad                    VARCHAR(10) NOT NULL,
    causa_raiz                   TEXT,
    estado                       VARCHAR(20) NOT NULL,
    iniciado_en                   TIMESTAMP WITH TIME ZONE NOT NULL,
    publicado_en                  TIMESTAMP WITH TIME ZONE,
    tiempo_resolucion_min         INTEGER,
    CONSTRAINT fk_post_mortem_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT chk_post_mortem_severidad
        CHECK (severidad IN ('baja', 'media', 'alta', 'critica')),
    CONSTRAINT chk_post_mortem_estado CHECK (estado IN ('en_progreso', 'publicado')),
    CONSTRAINT chk_post_mortem_tiempo_resolucion CHECK (tiempo_resolucion_min IS NULL OR tiempo_resolucion_min >= 0)
);

-- Corrige 1NF respecto a v5.1 (las acciones de remediacion eran un
-- atributo de texto no atomico) -- permite consultar acciones vencidas
-- sin analisis de texto.
CREATE TABLE compliance.post_mortem_accion (
    id                          BIGINT NOT NULL PRIMARY KEY,
    post_mortem_id               BIGINT NOT NULL,
    descripcion                  VARCHAR(300) NOT NULL,
    responsable_usuario_id        BIGINT NOT NULL,
    ticket_ref                    VARCHAR(50),
    estado                        VARCHAR(20) NOT NULL,
    vence_en                      TIMESTAMP WITH TIME ZONE NOT NULL,
    completada_en                 TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_post_mortem_accion_post_mortem FOREIGN KEY (post_mortem_id) REFERENCES compliance.post_mortem (id),
    CONSTRAINT fk_post_mortem_accion_responsable FOREIGN KEY (responsable_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_post_mortem_accion_estado
        CHECK (estado IN ('pendiente', 'en_progreso', 'completada', 'vencida'))
);

CREATE INDEX idx_post_mortem_accion_post_mortem ON compliance.post_mortem_accion (post_mortem_id);

-- Catalogo global.
CREATE TABLE compliance.control_soc2 (
    id               BIGINT NOT NULL PRIMARY KEY,
    codigo_control    VARCHAR(20) NOT NULL,
    nombre            VARCHAR(200) NOT NULL,
    categoria         VARCHAR(50) NOT NULL,
    CONSTRAINT uq_control_soc2_codigo UNIQUE (codigo_control)
);

-- Append-only (RF-T11).
CREATE TABLE compliance.evidencia_soc2 (
    id                     BIGINT NOT NULL PRIMARY KEY,
    control_soc2_id         BIGINT NOT NULL,
    tenant_id                BIGINT,
    periodo_inicio            DATE NOT NULL,
    periodo_fin               DATE NOT NULL,
    referencia_log_id         BIGINT,
    ruta_artefacto             VARCHAR(500) NOT NULL,
    hash_artefacto             CHAR(64) NOT NULL,
    generado_en                TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT fk_evidencia_soc2_control FOREIGN KEY (control_soc2_id) REFERENCES compliance.control_soc2 (id),
    CONSTRAINT fk_evidencia_soc2_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_evidencia_soc2_log FOREIGN KEY (referencia_log_id) REFERENCES compliance.log_auditoria (id)
);

CREATE INDEX idx_evidencia_soc2_control ON compliance.evidencia_soc2 (control_soc2_id);
