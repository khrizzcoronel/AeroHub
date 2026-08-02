-- Privilegios sobre support.* (S1.8, Plan Sec8.8). Nunca se otorga DELETE
-- (SRS Sec2.6, P5): toda baja es logica, gestionada por la aplicacion, no
-- por el motor. role_support explicitamente SIN acceso a `billing`
-- (98_grants_billing.sql ya lo excluye) -- segregacion de funciones D6
-- vigente desde S1.6, sin cambios aqui.
--
-- role_platform_admin: U,S en todo el esquema (mismo patron que
-- compliance/billing) + I sobre changelog/changelog_item (unico rol que
-- publica changelog, FR-015).
-- role_support: U,S,I,Up sobre ticket/ticket_mensaje (atiende tickets
-- cross-tenant via alcance_global, research.md Decision 5) y sobre
-- articulo_kb/etiqueta/articulo_kb_etiqueta (publica/versiona KB, FR-012).
-- Resto de roles de tenant (todo usuario que puede reportar un problema
-- operativo): U,S,I sobre ticket/ticket_mensaje propios (filtrado por
-- tenant_id via el guardian G2, PN-01) + U,S sobre los catalogos globales
-- (categoria_ticket, articulo_kb, etiqueta, articulo_kb_etiqueta, changelog,
-- changelog_item) -- FR-016: el changelog es visible sin condicionar a
-- licencia de modulo.
-- role_elt_reader: U,S sobre todo el esquema (tecnico, Airflow), mismo
-- patron que el resto de esquemas desde S0.2.

GRANT SELECT ON support.categoria_ticket TO role_platform_admin;
GRANT SELECT ON support.ticket TO role_platform_admin;
GRANT SELECT ON support.ticket_mensaje TO role_platform_admin;
GRANT SELECT ON support.articulo_kb TO role_platform_admin;
GRANT SELECT ON support.etiqueta TO role_platform_admin;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_platform_admin;
GRANT SELECT ON support.changelog TO role_platform_admin;
GRANT SELECT ON support.changelog_item TO role_platform_admin;
GRANT INSERT ON support.changelog TO role_platform_admin;
GRANT INSERT ON support.changelog_item TO role_platform_admin;

GRANT SELECT, INSERT, UPDATE ON support.ticket TO role_support;
GRANT SELECT, INSERT, UPDATE ON support.ticket_mensaje TO role_support;
GRANT SELECT, INSERT, UPDATE ON support.articulo_kb TO role_support;
GRANT SELECT, INSERT, UPDATE ON support.etiqueta TO role_support;
GRANT SELECT, INSERT, UPDATE ON support.articulo_kb_etiqueta TO role_support;
GRANT SELECT ON support.categoria_ticket TO role_support;
GRANT SELECT ON support.changelog TO role_support;
GRANT SELECT ON support.changelog_item TO role_support;

GRANT SELECT ON support.categoria_ticket TO role_tenant_admin;
GRANT SELECT, INSERT ON support.ticket TO role_tenant_admin;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_tenant_admin;
GRANT SELECT ON support.articulo_kb TO role_tenant_admin;
GRANT SELECT ON support.etiqueta TO role_tenant_admin;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_tenant_admin;
GRANT SELECT ON support.changelog TO role_tenant_admin;
GRANT SELECT ON support.changelog_item TO role_tenant_admin;

GRANT SELECT ON support.categoria_ticket TO role_operations_controller;
GRANT SELECT, INSERT ON support.ticket TO role_operations_controller;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_operations_controller;
GRANT SELECT ON support.articulo_kb TO role_operations_controller;
GRANT SELECT ON support.etiqueta TO role_operations_controller;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_operations_controller;
GRANT SELECT ON support.changelog TO role_operations_controller;
GRANT SELECT ON support.changelog_item TO role_operations_controller;

GRANT SELECT ON support.categoria_ticket TO role_airline_coordinator;
GRANT SELECT, INSERT ON support.ticket TO role_airline_coordinator;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_airline_coordinator;
GRANT SELECT ON support.articulo_kb TO role_airline_coordinator;
GRANT SELECT ON support.etiqueta TO role_airline_coordinator;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_airline_coordinator;
GRANT SELECT ON support.changelog TO role_airline_coordinator;
GRANT SELECT ON support.changelog_item TO role_airline_coordinator;

GRANT SELECT ON support.categoria_ticket TO role_ramp_agent;
GRANT SELECT, INSERT ON support.ticket TO role_ramp_agent;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_ramp_agent;
GRANT SELECT ON support.articulo_kb TO role_ramp_agent;
GRANT SELECT ON support.etiqueta TO role_ramp_agent;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_ramp_agent;
GRANT SELECT ON support.changelog TO role_ramp_agent;
GRANT SELECT ON support.changelog_item TO role_ramp_agent;

GRANT SELECT ON support.categoria_ticket TO role_billing_officer;
GRANT SELECT, INSERT ON support.ticket TO role_billing_officer;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_billing_officer;
GRANT SELECT ON support.articulo_kb TO role_billing_officer;
GRANT SELECT ON support.etiqueta TO role_billing_officer;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_billing_officer;
GRANT SELECT ON support.changelog TO role_billing_officer;
GRANT SELECT ON support.changelog_item TO role_billing_officer;

GRANT SELECT ON support.categoria_ticket TO role_business_viewer;
GRANT SELECT, INSERT ON support.ticket TO role_business_viewer;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_business_viewer;
GRANT SELECT ON support.articulo_kb TO role_business_viewer;
GRANT SELECT ON support.etiqueta TO role_business_viewer;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_business_viewer;
GRANT SELECT ON support.changelog TO role_business_viewer;
GRANT SELECT ON support.changelog_item TO role_business_viewer;

GRANT SELECT ON support.categoria_ticket TO role_tenant_analyst;
GRANT SELECT, INSERT ON support.ticket TO role_tenant_analyst;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_tenant_analyst;
GRANT SELECT ON support.articulo_kb TO role_tenant_analyst;
GRANT SELECT ON support.etiqueta TO role_tenant_analyst;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_tenant_analyst;
GRANT SELECT ON support.changelog TO role_tenant_analyst;
GRANT SELECT ON support.changelog_item TO role_tenant_analyst;

GRANT SELECT ON support.categoria_ticket TO role_regulatory_auditor;
GRANT SELECT, INSERT ON support.ticket TO role_regulatory_auditor;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_regulatory_auditor;
GRANT SELECT ON support.articulo_kb TO role_regulatory_auditor;
GRANT SELECT ON support.etiqueta TO role_regulatory_auditor;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_regulatory_auditor;
GRANT SELECT ON support.changelog TO role_regulatory_auditor;
GRANT SELECT ON support.changelog_item TO role_regulatory_auditor;

GRANT SELECT ON support.categoria_ticket TO role_people_viewer;
GRANT SELECT, INSERT ON support.ticket TO role_people_viewer;
GRANT SELECT, INSERT ON support.ticket_mensaje TO role_people_viewer;
GRANT SELECT ON support.articulo_kb TO role_people_viewer;
GRANT SELECT ON support.etiqueta TO role_people_viewer;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_people_viewer;
GRANT SELECT ON support.changelog TO role_people_viewer;
GRANT SELECT ON support.changelog_item TO role_people_viewer;

GRANT SELECT ON support.categoria_ticket TO role_elt_reader;
GRANT SELECT ON support.ticket TO role_elt_reader;
GRANT SELECT ON support.ticket_mensaje TO role_elt_reader;
GRANT SELECT ON support.articulo_kb TO role_elt_reader;
GRANT SELECT ON support.etiqueta TO role_elt_reader;
GRANT SELECT ON support.articulo_kb_etiqueta TO role_elt_reader;
GRANT SELECT ON support.changelog TO role_elt_reader;
GRANT SELECT ON support.changelog_item TO role_elt_reader;

-- catalogo.modulo: sin grants nuevos aqui -- 91_grants_catalogo.sql ya
-- otorga SELECT a los 16 roles.
