-- Esquema tenants (D5) -- identidad, acceso y licenciamiento (SDD-DATA-001 §6).
-- `id` generado por la aplicacion (ver 01_catalogo.sql, cabecera, y
-- packages/kernel/aerohub_kernel/identificador.py).

CREATE TABLE tenants.plan (
    id                    BIGINT NOT NULL PRIMARY KEY,
    codigo                VARCHAR(30) NOT NULL,
    nombre                VARCHAR(100) NOT NULL,
    tarifa_base_mensual   DECIMAL(12,2) NOT NULL,
    moneda                CHAR(3) NOT NULL,
    activo                BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT uq_plan_codigo UNIQUE (codigo),
    CONSTRAINT chk_plan_tarifa_base_mensual CHECK (tarifa_base_mensual >= 0)
);

CREATE TABLE tenants.plan_modulo (
    plan_id    BIGINT NOT NULL,
    modulo_id  BIGINT NOT NULL,
    CONSTRAINT pk_plan_modulo PRIMARY KEY (plan_id, modulo_id),
    CONSTRAINT fk_plan_modulo_plan FOREIGN KEY (plan_id) REFERENCES tenants.plan (id),
    CONSTRAINT fk_plan_modulo_modulo FOREIGN KEY (modulo_id) REFERENCES catalogo.modulo (id)
);

CREATE TABLE tenants.tenant (
    id             BIGINT NOT NULL PRIMARY KEY,
    codigo         VARCHAR(30) NOT NULL,
    razon_social   VARCHAR(200) NOT NULL,
    aeropuerto_id  BIGINT NOT NULL,
    plan_id        BIGINT NOT NULL,
    es_sandbox     BOOLEAN NOT NULL DEFAULT FALSE,
    estado         VARCHAR(20) NOT NULL,
    creado_en      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT uq_tenant_codigo UNIQUE (codigo),
    CONSTRAINT fk_tenant_aeropuerto FOREIGN KEY (aeropuerto_id) REFERENCES catalogo.aeropuerto (id),
    CONSTRAINT fk_tenant_plan FOREIGN KEY (plan_id) REFERENCES tenants.plan (id),
    CONSTRAINT chk_tenant_estado CHECK (estado IN ('activo', 'suspendido', 'en_onboarding', 'dado_de_baja'))
);

CREATE TABLE tenants.licencia (
    id             BIGINT NOT NULL PRIMARY KEY,
    tenant_id      BIGINT NOT NULL,
    modulo_id      BIGINT NOT NULL,
    activa_desde   TIMESTAMP WITH TIME ZONE NOT NULL,
    activa_hasta   TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_licencia_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_licencia_modulo FOREIGN KEY (modulo_id) REFERENCES catalogo.modulo (id),
    CONSTRAINT uq_licencia_tenant_modulo_desde UNIQUE (tenant_id, modulo_id, activa_desde)
);

-- hash_credencial: Argon2id, generado por packages/kernel/aerohub_kernel/credenciales.py
-- (cierra SDD-DATA-001 M-07). Nunca se almacena la contrasena en claro.
CREATE TABLE tenants.usuario (
    id                 BIGINT NOT NULL PRIMARY KEY,
    tenant_id          BIGINT,
    email              VARCHAR(254) NOT NULL,
    hash_credencial    VARCHAR(255) NOT NULL,
    nombre             VARCHAR(150) NOT NULL,
    -- VARCHAR(30), no 20: el propio CHECK de abajo permite
    -- 'eliminado_logicamente' (21 caracteres) -- hallazgo empirico
    -- 2026-08-05, la columna nunca pudo contener su propio valor valido
    -- mas largo desde S1.1 (chk_usuario_estado ya lo declaraba permitido).
    estado             VARCHAR(30) NOT NULL,
    mfa_habilitado     BOOLEAN NOT NULL DEFAULT FALSE,
    -- Aerolinea a la que pertenece el usuario, NULL para la gran mayoria
    -- (personal del aeropuerto, no de una aerolinea). Existe para hacer
    -- REPRESENTABLE la restriccion "solo sus itinerarios" / "sus cargos"
    -- que la matriz 4.3.1 asigna a role_airline_coordinator y que
    -- 96_grants_ops.sql / 98_grants_billing.sql delegan explicitamente a
    -- la capa de aplicacion (MonetDB no tiene RLS). Antes de esta columna
    -- la restriccion no era un pendiente de implementacion: era
    -- imposible de expresar -- ninguna tabla asociaba un usuario a una
    -- aerolinea (hallazgo 3 de la auditoria de la capa operativa,
    -- 2026-08-08). El filtro se aplica en infrastructure/ de aodb y
    -- billing, mismo patron que `_ROL_CON_ACCESO_RESTRINGIDO` de
    -- aerohub_ramp (S1.5).
    aerolinea_id       BIGINT,
    creado_en          TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    ultimo_acceso_en   TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_usuario_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT fk_usuario_aerolinea FOREIGN KEY (aerolinea_id) REFERENCES catalogo.aerolinea (id),
    CONSTRAINT uq_usuario_tenant_email UNIQUE (tenant_id, email),
    CONSTRAINT chk_usuario_estado CHECK (estado IN ('activo', 'suspendido', 'eliminado_logicamente'))
);

CREATE TABLE tenants.rol (
    id      BIGINT NOT NULL PRIMARY KEY,
    codigo  VARCHAR(50) NOT NULL,
    nombre  VARCHAR(100) NOT NULL,
    alcance VARCHAR(20) NOT NULL,
    CONSTRAINT uq_rol_codigo UNIQUE (codigo),
    CONSTRAINT chk_rol_alcance CHECK (alcance IN ('plataforma', 'tenant'))
);

CREATE TABLE tenants.usuario_rol (
    usuario_id     BIGINT NOT NULL,
    rol_id         BIGINT NOT NULL,
    otorgado_por   BIGINT NOT NULL,
    otorgado_en    TIMESTAMP WITH TIME ZONE NOT NULL,
    expira_en      TIMESTAMP WITH TIME ZONE,
    CONSTRAINT pk_usuario_rol PRIMARY KEY (usuario_id, rol_id),
    CONSTRAINT fk_usuario_rol_usuario FOREIGN KEY (usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT fk_usuario_rol_rol FOREIGN KEY (rol_id) REFERENCES tenants.rol (id),
    CONSTRAINT fk_usuario_rol_otorgado_por FOREIGN KEY (otorgado_por) REFERENCES tenants.usuario (id)
);

-- hash_secreto: mismo mecanismo Argon2id que hash_credencial. El secreto en
-- claro se muestra una unica vez al emitirse (RF-O12) y nunca se persiste.
CREATE TABLE tenants.api_key (
    id             BIGINT NOT NULL PRIMARY KEY,
    tenant_id      BIGINT NOT NULL,
    prefijo        VARCHAR(12) NOT NULL,
    hash_secreto   VARCHAR(255) NOT NULL,
    creada_en      TIMESTAMP WITH TIME ZONE NOT NULL,
    rotada_en      TIMESTAMP WITH TIME ZONE,
    expira_en      TIMESTAMP WITH TIME ZONE,
    estado         VARCHAR(20) NOT NULL,
    CONSTRAINT fk_api_key_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant (id),
    CONSTRAINT uq_api_key_prefijo UNIQUE (prefijo),
    CONSTRAINT chk_api_key_estado CHECK (estado IN ('activa', 'revocada', 'expirada'))
);

CREATE TABLE tenants.okr (
    id                       BIGINT NOT NULL PRIMARY KEY,
    departamento_id          BIGINT NOT NULL,
    periodo                  VARCHAR(7) NOT NULL,
    objetivo_descripcion     VARCHAR(500) NOT NULL,
    responsable_usuario_id   BIGINT NOT NULL,
    estado                   VARCHAR(20) NOT NULL,
    CONSTRAINT fk_okr_departamento FOREIGN KEY (departamento_id) REFERENCES catalogo.departamento (id),
    CONSTRAINT fk_okr_responsable_usuario FOREIGN KEY (responsable_usuario_id) REFERENCES tenants.usuario (id),
    CONSTRAINT chk_okr_estado CHECK (estado IN ('planificado', 'en_progreso', 'cumplido', 'no_cumplido'))
);

CREATE TABLE tenants.okr_resultado_clave (
    id             BIGINT NOT NULL PRIMARY KEY,
    okr_id         BIGINT NOT NULL,
    descripcion    VARCHAR(300) NOT NULL,
    valor_inicial  DECIMAL(14,2) NOT NULL,
    valor_objetivo DECIMAL(14,2) NOT NULL,
    valor_actual   DECIMAL(14,2) NOT NULL DEFAULT 0,
    unidad         VARCHAR(20) NOT NULL,
    CONSTRAINT fk_okr_resultado_clave_okr FOREIGN KEY (okr_id) REFERENCES tenants.okr (id)
);

-- Los 16 roles RBAC de la matriz 4.3.1 (Analisis v6.0 §4.3), como catalogo
-- de referencia de la aplicacion. Distinto de los objetos CREATE ROLE del
-- motor (db/ddl/monetdb/90_roles.sql): esta tabla es metadata de negocio
-- (que se muestra en el portal de administracion al asignar un rol a un
-- usuario); los CREATE ROLE son los principals que el motor evalua en
-- SET ROLE. Ambos deben mantenerse sincronizados por codigo. `id` fijo
-- 1..16, misma logica que los catalogos de 01_catalogo.sql.
INSERT INTO tenants.rol (id, codigo, nombre, alcance) VALUES
    (1, 'role_platform_admin', 'Administrador de Plataforma', 'plataforma'),
    (2, 'role_sre', 'SRE / Operaciones Cloud', 'plataforma'),
    (3, 'role_data_engineer', 'Data Engineer', 'plataforma'),
    (4, 'role_ml_engineer', 'ML Engineer', 'plataforma'),
    (5, 'role_implementation', 'Especialista de Implementacion', 'plataforma'),
    (6, 'role_support', 'Especialista DevRel', 'plataforma'),
    (7, 'role_business_viewer', 'Visor de Negocio', 'plataforma'),
    (8, 'role_people_viewer', 'Visor de Talento', 'plataforma'),
    (9, 'role_elt_reader', 'Identidad tecnica ELT (lectura)', 'plataforma'),
    (10, 'role_tenant_admin', 'Administrador del Tenant', 'tenant'),
    (11, 'role_operations_controller', 'Controlador de Operaciones', 'tenant'),
    (12, 'role_airline_coordinator', 'Aerolinea Coordinadora', 'tenant'),
    (13, 'role_ramp_agent', 'Agente de Rampa', 'tenant'),
    (14, 'role_billing_officer', 'Operador de Facturacion', 'tenant'),
    (15, 'role_tenant_analyst', 'Analista del Tenant', 'tenant'),
    (16, 'role_regulatory_auditor', 'Auditor de Regulacion Aerea', 'tenant');
