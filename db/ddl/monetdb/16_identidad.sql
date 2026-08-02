-- Esquema de identidad y acceso (Sprint S1.10, ADR-020,
-- specs/012-identidad-y-acceso/data-model.md). Amplia tenants.usuario con
-- el ciclo de vida real de la credencial y agrega 4 tablas nuevas para
-- sesiones revocables, tokens de un solo uso, invitaciones e intentos de
-- acceso.
--
-- No migra la unicidad del correo aqui -- eso vive en
-- 17_migracion_email_unico.sql, un archivo separado para que aplique
-- igual sobre una base nueva (crea con la restriccion vieja, la migra
-- acto seguido) y sobre una base ya existente con datos reales
-- (research.md Decision 2).

-- `ultimo_acceso_en` ya existe desde S0.2 (columna sin usar hasta este
-- sprint) -- no se vuelve a agregar aqui, solo empieza a escribirse.
ALTER TABLE tenants.usuario ADD COLUMN email_verificado_en TIMESTAMP WITH TIME ZONE;
ALTER TABLE tenants.usuario ADD COLUMN debe_cambiar_password BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE tenants.usuario ADD COLUMN bloqueado_hasta TIMESTAMP WITH TIME ZONE;

-- Sesiones activas revocables (alcance G1 'interno' -- se consulta en
-- cada peticion autenticada, incluidas las de un usuario de plataforma
-- sin tenant_id; research.md Decision 9).
CREATE TABLE tenants.sesion (
    id BIGINT NOT NULL PRIMARY KEY,
    usuario_id BIGINT NOT NULL,
    emitida_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expira_en TIMESTAMP WITH TIME ZONE NOT NULL,
    revocada_en TIMESTAMP WITH TIME ZONE,
    motivo_revocacion VARCHAR(30)
        CHECK (motivo_revocacion IN ('cierre_sesion', 'restablecer_password', 'revocacion_admin')),
    ip_origen VARCHAR(45),
    CONSTRAINT fk_sesion_usuario FOREIGN KEY (usuario_id) REFERENCES tenants.usuario(id)
);

-- Tokens de un solo uso (verificacion, invitacion, recuperacion). El
-- token nunca se guarda en claro -- solo su hash Argon2id (research.md
-- Decision 8, mismo mecanismo que tenants.api_key.hash_secreto).
CREATE TABLE tenants.token_acceso (
    id BIGINT NOT NULL PRIMARY KEY,
    usuario_id BIGINT,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('verificacion', 'invitacion', 'recuperacion')),
    hash_token VARCHAR(255) NOT NULL,
    emitido_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    expira_en TIMESTAMP WITH TIME ZONE NOT NULL,
    consumido_en TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_token_acceso_usuario FOREIGN KEY (usuario_id) REFERENCES tenants.usuario(id)
);

-- Invitaciones (alcance G1 'tenant' -- siempre las crea un admin ya
-- autenticado dentro de su propio tenant, research.md Decision 9).
CREATE TABLE tenants.invitacion (
    id BIGINT NOT NULL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    email VARCHAR(254) NOT NULL,
    rol_id BIGINT NOT NULL,
    invitado_por_usuario_id BIGINT NOT NULL,
    token_acceso_id BIGINT NOT NULL,
    estado VARCHAR(20) NOT NULL
        CHECK (estado IN ('pendiente', 'aceptada', 'caducada', 'revocada')),
    creada_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    aceptada_en TIMESTAMP WITH TIME ZONE,
    CONSTRAINT fk_invitacion_tenant FOREIGN KEY (tenant_id) REFERENCES tenants.tenant(id),
    CONSTRAINT fk_invitacion_rol FOREIGN KEY (rol_id) REFERENCES tenants.rol(id),
    CONSTRAINT fk_invitacion_invitador FOREIGN KEY (invitado_por_usuario_id) REFERENCES tenants.usuario(id),
    CONSTRAINT fk_invitacion_token FOREIGN KEY (token_acceso_id) REFERENCES tenants.token_acceso(id)
);

-- Intentos de acceso (alcance G1 'interno', append-only). Base del
-- bloqueo por intentos fallidos y evidencia de RNF-S04. `resultado`
-- distingue el motivo real EN el registro interno; la respuesta HTTP al
-- cliente es identica en todos los casos de fallo (FR-003).
CREATE TABLE tenants.intento_acceso (
    id BIGINT NOT NULL PRIMARY KEY,
    email_intentado VARCHAR(254) NOT NULL,
    usuario_id BIGINT,
    resultado VARCHAR(20) NOT NULL
        CHECK (resultado IN (
            'exitoso', 'credencial_invalida', 'cuenta_bloqueada',
            'cuenta_inactiva', 'sin_rol_vigente'
        )),
    ocurrido_en TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    ip_origen VARCHAR(45),
    CONSTRAINT fk_intento_acceso_usuario FOREIGN KEY (usuario_id) REFERENCES tenants.usuario(id)
);
