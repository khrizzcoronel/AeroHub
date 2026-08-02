-- Esquema support (D6) -- S1.8 Soporte y observabilidad (Plan Sec8.8;
-- SDD-DATA-001 Sec11). `id` generado por la aplicacion (ver 01_catalogo.sql,
-- cabecera). La observabilidad (uptime/error budget) NO agrega tablas aqui
-- -- se deriva de Prometheus en tiempo de consulta (research.md Decision 1
-- de specs/010-support-observability/).

-- Catalogo global.
CREATE TABLE support.categoria_ticket (
    id       BIGINT NOT NULL PRIMARY KEY,
    codigo   VARCHAR(30) NOT NULL,
    nombre   VARCHAR(100) NOT NULL,
    CONSTRAINT uq_categoria_ticket_codigo UNIQUE (codigo)
);

CREATE TABLE support.ticket (
    id                          BIGINT NOT NULL PRIMARY KEY,
    tenant_id                   BIGINT NOT NULL,
    categoria_id                BIGINT NOT NULL,
    creado_por_usuario_id       BIGINT NOT NULL,
    asignado_a_usuario_id       BIGINT,
    severidad                   VARCHAR(10) NOT NULL,
    estado                      VARCHAR(20) NOT NULL,
    asunto                      VARCHAR(200) NOT NULL,
    creado_en                   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    primera_respuesta_en        TIMESTAMP WITH TIME ZONE,
    resuelto_en                 TIMESTAMP WITH TIME ZONE,
    sla_objetivo_min            INTEGER NOT NULL,
    CONSTRAINT fk_ticket_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_ticket_categoria FOREIGN KEY (categoria_id) REFERENCES support.categoria_ticket (id),
    CONSTRAINT fk_ticket_creado_por FOREIGN KEY (creado_por_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT fk_ticket_asignado_a FOREIGN KEY (asignado_a_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_ticket_severidad CHECK (severidad IN ('baja', 'media', 'alta', 'critica')),
    CONSTRAINT chk_ticket_estado
        CHECK (estado IN ('abierto', 'en_progreso', 'esperando_cliente', 'resuelto', 'cerrado'))
);

CREATE INDEX idx_ticket_tenant ON support.ticket (tenant_id);

-- Sin tenant_id propio -- alcance 'interno', aislado transitivamente via
-- ticket_id -> ticket.tenant_id (mismo patron que compliance.post_mortem_accion,
-- S1.7; data-model.md Decision 4).
CREATE TABLE support.ticket_mensaje (
    id                  BIGINT NOT NULL PRIMARY KEY,
    ticket_id           BIGINT NOT NULL,
    autor_usuario_id    BIGINT NOT NULL,
    cuerpo              TEXT NOT NULL,
    enviado_en          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    es_interno          BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT fk_ticket_mensaje_ticket FOREIGN KEY (ticket_id) REFERENCES support.ticket (id),
    CONSTRAINT fk_ticket_mensaje_autor FOREIGN KEY (autor_usuario_id) REFERENCES tenants.usuario (id)
);

CREATE INDEX idx_ticket_mensaje_ticket ON support.ticket_mensaje (ticket_id);

-- Global (sin tenant_id, SDD Sec11.4) -- conocimiento compartido entre todos
-- los tenants. embedding_ref: puntero reservado para busqueda semantica
-- futura, no usado en S1.8 (research.md Decision 6).
CREATE TABLE support.articulo_kb (
    id                   BIGINT NOT NULL PRIMARY KEY,
    titulo               VARCHAR(200) NOT NULL,
    cuerpo               TEXT NOT NULL,
    version              INTEGER NOT NULL,
    estado               VARCHAR(20) NOT NULL,
    publicado_en         TIMESTAMP WITH TIME ZONE,
    autor_usuario_id     BIGINT NOT NULL,
    embedding_ref        VARCHAR(200),
    CONSTRAINT fk_articulo_kb_autor FOREIGN KEY (autor_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT uq_articulo_kb_titulo_version UNIQUE (titulo, version),
    CONSTRAINT chk_articulo_kb_estado CHECK (estado IN ('borrador', 'publicado', 'archivado'))
);

CREATE TABLE support.etiqueta (
    id       BIGINT NOT NULL PRIMARY KEY,
    nombre   VARCHAR(50) NOT NULL,
    CONSTRAINT uq_etiqueta_nombre UNIQUE (nombre)
);

CREATE TABLE support.articulo_kb_etiqueta (
    articulo_id   BIGINT NOT NULL,
    etiqueta_id   BIGINT NOT NULL,
    CONSTRAINT pk_articulo_kb_etiqueta PRIMARY KEY (articulo_id, etiqueta_id),
    CONSTRAINT fk_articulo_kb_etiqueta_articulo FOREIGN KEY (articulo_id) REFERENCES support.articulo_kb (id),
    CONSTRAINT fk_articulo_kb_etiqueta_etiqueta FOREIGN KEY (etiqueta_id) REFERENCES support.etiqueta (id)
);

CREATE TABLE support.changelog (
    id                   BIGINT NOT NULL PRIMARY KEY,
    version_producto     VARCHAR(20) NOT NULL,
    resumen              VARCHAR(500) NOT NULL,
    publicado_en         TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_changelog_version_producto UNIQUE (version_producto)
);

-- modulo_id referencia catalogo.modulo, redeclarada localmente en
-- aerohub_support/infrastructure/tablas.py (patron ya usado en
-- aerohub_gates/aerohub_ramp/aerohub_gateway) -- sin FK cruzado de esquema
-- aqui para modulo porque catalogo.modulo ya existe desde S0.1.
CREATE TABLE support.changelog_item (
    id             BIGINT NOT NULL PRIMARY KEY,
    changelog_id   BIGINT NOT NULL,
    modulo_id      BIGINT NOT NULL,
    tipo_cambio    VARCHAR(20) NOT NULL,
    descripcion    VARCHAR(500) NOT NULL,
    CONSTRAINT fk_changelog_item_changelog FOREIGN KEY (changelog_id) REFERENCES support.changelog (id),
    CONSTRAINT fk_changelog_item_modulo FOREIGN KEY (modulo_id) REFERENCES catalogo.modulo (id),
    CONSTRAINT chk_changelog_item_tipo_cambio
        CHECK (tipo_cambio IN ('nuevo', 'mejora', 'correccion', 'obsolescencia'))
);

CREATE INDEX idx_changelog_item_changelog ON support.changelog_item (changelog_id);
