-- Privilegios sobre las tablas nuevas de compliance (S1.7) -- matriz
-- 4.3.1, columna `compliance`: "role_sre: U,S; U,S,I sobre evidencia_soc2;
-- U,S,I,Up sobre post_mortem y post_mortem_accion" -- unico rol con
-- escritura real en la matriz para este esquema (role_platform_admin
-- solo por break-glass auditado, procedimiento fuera de alcance de este
-- sprint, ver 93_grants_compliance.sql). role_data_engineer,
-- role_regulatory_auditor, role_elt_reader: U,S.
--
-- Los catalogos (tipo_incidente, tipo_reporte_regulatorio, control_soc2)
-- y las tablas append-only sin escritor explicito en la matriz
-- (incidente_seguridad, reporte_dgac, acceso_auditor) reciben INSERT de
-- role_platform_admin y role_sre -- ambos roles de plataforma con
-- responsabilidad operativa sobre compliance; ningun otro rol escribe
-- aqui (segregacion de funciones, mismo criterio que billing en S1.6).
-- Nunca se otorga DELETE (P5) ni UPDATE fuera de post_mortem/
-- post_mortem_accion (append-only, PN-04 reforzada).

GRANT SELECT ON compliance.tipo_incidente TO role_platform_admin;
GRANT SELECT ON compliance.incidente_seguridad TO role_platform_admin;
GRANT SELECT ON compliance.tipo_reporte_regulatorio TO role_platform_admin;
GRANT SELECT ON compliance.reporte_dgac TO role_platform_admin;
GRANT SELECT ON compliance.acceso_auditor TO role_platform_admin;
GRANT SELECT ON compliance.post_mortem TO role_platform_admin;
GRANT SELECT ON compliance.post_mortem_accion TO role_platform_admin;
GRANT SELECT ON compliance.control_soc2 TO role_platform_admin;
GRANT SELECT ON compliance.evidencia_soc2 TO role_platform_admin;
GRANT INSERT ON compliance.tipo_incidente TO role_platform_admin;
GRANT INSERT ON compliance.incidente_seguridad TO role_platform_admin;
GRANT INSERT ON compliance.tipo_reporte_regulatorio TO role_platform_admin;
GRANT INSERT ON compliance.reporte_dgac TO role_platform_admin;
GRANT INSERT ON compliance.acceso_auditor TO role_platform_admin;
GRANT INSERT ON compliance.control_soc2 TO role_platform_admin;

GRANT SELECT ON compliance.tipo_incidente TO role_sre;
GRANT SELECT ON compliance.incidente_seguridad TO role_sre;
GRANT SELECT ON compliance.tipo_reporte_regulatorio TO role_sre;
GRANT SELECT ON compliance.reporte_dgac TO role_sre;
GRANT SELECT ON compliance.acceso_auditor TO role_sre;
GRANT SELECT ON compliance.post_mortem TO role_sre;
GRANT SELECT ON compliance.post_mortem_accion TO role_sre;
GRANT SELECT ON compliance.control_soc2 TO role_sre;
GRANT SELECT ON compliance.evidencia_soc2 TO role_sre;
GRANT INSERT ON compliance.tipo_incidente TO role_sre;
GRANT INSERT ON compliance.incidente_seguridad TO role_sre;
GRANT INSERT ON compliance.tipo_reporte_regulatorio TO role_sre;
GRANT INSERT ON compliance.reporte_dgac TO role_sre;
GRANT INSERT ON compliance.acceso_auditor TO role_sre;
GRANT INSERT ON compliance.control_soc2 TO role_sre;
GRANT INSERT ON compliance.evidencia_soc2 TO role_sre;
-- Unica excepcion de mutabilidad del esquema (ADR-009) -- aplicada
-- ademas en aerohub_compliance.application (exclusivo role_sre en
-- codigo, este GRANT es la contraparte de motor).
GRANT INSERT, UPDATE ON compliance.post_mortem TO role_sre;
GRANT INSERT, UPDATE ON compliance.post_mortem_accion TO role_sre;

GRANT SELECT ON compliance.tipo_incidente TO role_data_engineer;
GRANT SELECT ON compliance.incidente_seguridad TO role_data_engineer;
GRANT SELECT ON compliance.tipo_reporte_regulatorio TO role_data_engineer;
GRANT SELECT ON compliance.reporte_dgac TO role_data_engineer;
GRANT SELECT ON compliance.acceso_auditor TO role_data_engineer;
GRANT SELECT ON compliance.post_mortem TO role_data_engineer;
GRANT SELECT ON compliance.post_mortem_accion TO role_data_engineer;
GRANT SELECT ON compliance.control_soc2 TO role_data_engineer;
GRANT SELECT ON compliance.evidencia_soc2 TO role_data_engineer;

GRANT SELECT ON compliance.tipo_incidente TO role_regulatory_auditor;
GRANT SELECT ON compliance.incidente_seguridad TO role_regulatory_auditor;
GRANT SELECT ON compliance.tipo_reporte_regulatorio TO role_regulatory_auditor;
GRANT SELECT ON compliance.reporte_dgac TO role_regulatory_auditor;
GRANT SELECT ON compliance.acceso_auditor TO role_regulatory_auditor;
GRANT SELECT ON compliance.post_mortem TO role_regulatory_auditor;
GRANT SELECT ON compliance.post_mortem_accion TO role_regulatory_auditor;
GRANT SELECT ON compliance.control_soc2 TO role_regulatory_auditor;
GRANT SELECT ON compliance.evidencia_soc2 TO role_regulatory_auditor;

GRANT SELECT ON compliance.tipo_incidente TO role_elt_reader;
GRANT SELECT ON compliance.incidente_seguridad TO role_elt_reader;
GRANT SELECT ON compliance.tipo_reporte_regulatorio TO role_elt_reader;
GRANT SELECT ON compliance.reporte_dgac TO role_elt_reader;
GRANT SELECT ON compliance.acceso_auditor TO role_elt_reader;
GRANT SELECT ON compliance.post_mortem TO role_elt_reader;
GRANT SELECT ON compliance.post_mortem_accion TO role_elt_reader;
GRANT SELECT ON compliance.control_soc2 TO role_elt_reader;
GRANT SELECT ON compliance.evidencia_soc2 TO role_elt_reader;

-- role_support: sin acceso a compliance en la matriz (segregacion de
-- funciones, mismo tratamiento que billing en S1.6) -- sin GRANT alguno.
--
-- catalogo.modulo: NO necesita grants nuevos aqui -- 91_grants_catalogo.sql
-- ya otorga SELECT a los 16 roles (parte del SELECT amplio sobre todo
-- `catalogo.*` decidido en S0.2).
