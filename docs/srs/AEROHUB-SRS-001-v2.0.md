# Especificación de Requisitos de Software (SRS)
## Plataforma AeroHub — Sistema Integral de Gestión Operativa y Comercial Aeroportuaria

| Campo | Contenido |
|:---|:---|
| **Identificador de documento** | AEROHUB-SRS-001 |
| **Versión** | 2.0 — **supersede a la v1.0** |
| **Basado en** | AeroHub — Análisis Documental Estratégico v6.0 |
| **Trazabilidad de cambio** | AEROHUB-SRS-CR-006 (plan de actualización), AEROHUB-ADR-INTERNO-001 (resolución de inconsistencias I1–I5, confirmada por el propietario del producto) |
| **Metodología** | Specification-Driven Development (SDD) |
| **Marco normativo de referencia** | ISO/IEC/IEEE 29148:2018 (estructura de este SRS) · IEEE 1016 (SDD derivado, Sección 12) · ISO/IEC/IEEE 42010 (descripción de arquitectura) · ISO/IEC 25010 (modelo de calidad) · ISO/IEC 12207 (ciclo de vida y control de cambios) · ISO/IEC/IEEE 29119 (verificación y validación) · ISO/IEC 27001/27002 (seguridad de la información) · ISO/IEC 27701 (privacidad/PII) |
| **Estado** | Línea base para revisión de aceptación |

---

## Nota de control de versión

Esta versión reemplaza íntegramente las Secciones 2 (Descripción general), 6 (Arquitectura), 7 (Modelo de datos) y 9 (Seguridad y privacidad) de la SRS v1.0, y actualiza de forma sustancial las Secciones 3 a 5, 8 y 10 a 12, conforme al plan de actualización AEROHUB-SRS-CR-006. **Todo artefacto de diseño (SDD, IEEE 1016) derivado de la SRS v1.0 y basado en PostgreSQL/RLS queda invalidado** y debe re-derivarse desde esta versión antes de continuar cualquier trabajo de implementación.

Los identificadores RF-O19, CU-O21, RF-O01 y RF-O18 incorporan en este documento la resolución interina de AEROHUB-ADR-INTERNO-001, confirmada por el propietario del producto. Las capacidades cuya numeración normativa permanecía en disputa en el documento fuente (RF-O20, RF-O21, RF-O22, RF-T13, RF-T14 y la capacidad de NPS/CSAT bajo el identificador provisional RF-O19-bis) se documentan en el **Apéndice A** como capacidades de hoja de ruta pendientes de confirmación de esquema, y no forman parte del catálogo normativo de las Secciones 4 y 7 hasta su cierre formal.

---

# 1. Introducción

## 1.1 Propósito

Este SRS especifica de manera completa, verificable y no ambigua los requisitos funcionales y no funcionales de la plataforma AeroHub, un sistema SaaS multi-tenant de gestión operativa, comercial y analítica para aeropuertos medianos y grandes en Latinoamérica. El documento sirve como contrato técnico entre las áreas de negocio (D1–D6) y el equipo de ingeniería, y como línea base de trazabilidad para el diseño (IEEE 1016), la verificación (ISO/IEC/IEEE 29119) y las auditorías de cumplimiento normativo (DGAC/OACI, SOC 2).

## 1.2 Alcance del producto

AeroHub integra, bajo una única plataforma multi-tenant, los siguientes dominios de negocio:

- Gestión operativa de vuelos en tiempo real (AODB) sobre un motor operacional MonetDB.
- Distribución de información a pantallas físicas de terminal (FIDS).
- Asignación óptima de puertas de embarque y posiciones remotas.
- Gestión de operaciones de rampa (turnaround), modelada como entidad propia que empareja vuelo de llegada y vuelo de salida.
- Facturación por uso de infraestructura aeroportuaria (Pax/Slots).
- Un pipeline analítico de arquitectura medallion (bronce/plata/oro) que alimenta dos bases ClickHouse segmentadas por nivel de decisión (`ah_tactico`, `ah_estrategico`).
- Analítica avanzada, Balanced Scorecard (BSC) y predicción explicable de demoras mediante Machine Learning.
- Cumplimiento normativo, auditoría y gestión de incidentes de seguridad, con aislamiento multi-tenant de naturaleza asimétrica (Sección 9).
- Soporte al cliente, portal de desarrollador y aprovisionamiento de tenants.

**Fuera de alcance de este SRS:** la lógica interna del CRM comercial de terceros y de la consola de facturación del proveedor PaaS (fuentes externas, Sección 7.7); los procesos organizacionales internos de gestión de sprints y de ADR (Anexo A de la fuente documental, ISO/IEC 12207); las capacidades listadas en el Apéndice A, pendientes de confirmación normativa.

## 1.3 Definiciones, acrónimos y abreviaturas

| Término | Definición |
|:---|:---|
| AODB | Airport Operational Database — base transaccional central de estados de vuelo. |
| FIDS | Flight Information Display System — sistema de pantallas de información de vuelos. |
| RBAC | Role-Based Access Control — control de acceso basado en roles. |
| Capa de repositorio | Única capa de software autorizada a emitir SQL hacia el motor operacional MonetDB; sustituye funcionalmente el aislamiento que antes ofrecía el RLS nativo. |
| Arquitectura medallion | Patrón de refinamiento progresivo de datos en tres capas (bronce: ingesta cruda; plata: validada y normalizada; oro: agregados listos para carga), con estado de ejecución gobernado en `etl_control`. |
| `ah_tactico` / `ah_estrategico` | Las dos bases ClickHouse de la capa analítica; la primera almacena el detalle transaccional histórico, la segunda los KPI agregados de consumo estratégico, derivados unidireccionalmente de la primera. |
| BCNF / 4NF / 5NF | Formas normales de Boyce-Codd, Cuarta y Quinta Forma Normal, aplicadas al rediseño del modelo de datos operacional (Sección 7.2). |
| BSC | Balanced Scorecard — tablero de mando con las cuatro perspectivas (financiera, cliente, procesos, aprendizaje). |
| DGAC | Dirección General de Aviación Civil (ente regulador nacional). |
| OACI | Organización de Aviación Civil Internacional. |
| RF / RNF | Requisito Funcional / Requisito No Funcional. |
| OE / OT / OP | Objetivo Estratégico / Táctico / Operativo. |
| CU | Caso de Uso. |
| PN | Prueba Negativa (batería de seguridad, Sección 8.2). |
| MAPE | Mean Absolute Percentage Error — métrica de error del modelo predictivo de demoras. |
| RTO / RPO | Recovery Time Objective / Recovery Point Objective. |
| PII | Personally Identifiable Information — información personal identificable. |
| MoSCoW | Técnica de priorización: Must, Should, Could, Won't. |

## 1.4 Referencias normativas

ISO/IEC/IEEE 29148:2018; IEEE 1016-2009; ISO/IEC/IEEE 42010:2011; ISO/IEC 25010:2011; ISO/IEC 12207:2017; ISO/IEC/IEEE 29119; ISO/IEC 27001:2022 e ISO/IEC 27002:2022; ISO/IEC 27701:2019; especificación OpenAPI 3.1; LOPDP (Ecuador), Ley 29733 (Perú), Ley 1581 (Colombia).

## 1.5 Visión general del documento

La Sección 2 describe el producto desde la perspectiva de negocio y arquitectura vigente (MonetDB/ClickHouse). La Sección 3 define actores y el modelo RBAC dual. La Sección 4 contiene el catálogo de requisitos funcionales confirmados. La Sección 5 especifica los requisitos no funcionales bajo ISO/IEC 25010, con la numeración oficial de la fuente reconciliada frente a la clasificación editorial previa. La Sección 6 resume la arquitectura de referencia y el estado de los ADR. La Sección 7 documenta el modelo de datos normalizado y la arquitectura medallion. La Sección 8 define la verificación y validación con la batería de pruebas negativas ampliada. La Sección 9 aborda el modelo de seguridad asimétrico y la privacidad. La Sección 10 presenta la matriz de trazabilidad. Las Secciones 11–12 cubren restricciones, riesgos abiertos y el enlace hacia el diseño. El Apéndice A documenta las capacidades pendientes de confirmación normativa.

---

# 2. Descripción general

## 2.1 Perspectiva del producto

AeroHub es una plataforma SaaS multi-tenant compuesta por tres capas de persistencia con responsabilidades disjuntas:

- **Base operacional (MonetDB):** transaccional, ocho esquemas departamentales más el esquema técnico `etl_control`. **No implementa Row-Level Security nativo**; el aislamiento por tenant es responsabilidad de la capa de repositorio (Sección 9.2).
- **Área de trabajo medallion (Parquet en disco):** tres capas de refinamiento (bronce/plata/oro) más una zona de cuarentena, gobernadas por Airflow y registradas en `etl_control.etl_ejecucion`.
- **Capa analítica (ClickHouse, dos bases):** `ah_tactico` (detalle histórico, con política de fila estructural por tenant) y `ah_estrategico` (KPI agregados, derivados unidireccionalmente de `ah_tactico` con reconciliación de tolerancia cero).

## 2.2 Funciones del producto (resumen por módulo)

| Módulo | Departamento propietario | Función principal |
|:---|:---|:---|
| M1 — AODB | D1 — Operaciones | Motor transaccional central de vuelos, itinerarios, estados, aeronaves y causas de demora, sobre MonetDB. |
| M2 — FIDS Management | D1 — Operaciones | Diseño y distribución de información a pantallas físicas vía WebSockets. |
| M3 — Terminal & Gate Manager | D1 — Operaciones | Asignación óptima de puertas y posiciones remotas mediante optimización lineal; el no solapamiento se verifica en capa de aplicación (Sección 8.2, PN-05). |
| M4 — Ground Operations | D2 — Rampa | Registro de turnaround (entidad propia que empareja vuelo de llegada y salida) y gestión de incidencias de rampa. |
| M5 — Revenue & Billing | D3 — Comercial y Finanzas | Tasación y facturación por Pax, slots y uso de infraestructura, con tarifario normalizado en cabecera y detalle. |
| M6 — Passenger Experience | D1 — Operaciones | Estimación agregada de tiempos de espera sin captura de PII de pasajeros. |
| M7 — ETL & Analytics | D4 — Datos e IA | Pipeline de arquitectura medallion (bronce/plata/oro) orquestado por Airflow, con carga hacia `ah_tactico` y derivación reconciliada hacia `ah_estrategico`. |
| M8 — Observability | D5 — Plataforma y Seguridad | Métricas, logs y trazas transversales de todos los módulos. |
| M9 — Compliance Hub | D5 — Plataforma y Seguridad | Auditoría append-only (con excepción controlada de `post_mortem`/`post_mortem_accion`), reportes DGAC/OACI y gestión de incidentes de seguridad. |

## 2.3 Dependencias entre módulos

| Módulo origen | Módulo destino | Naturaleza de la dependencia |
|:---|:---|:---|
| M2 FIDS | M1 AODB | Consume estados de vuelo y cambios de horario en tiempo real. |
| M3 Terminal & Gate | M1 AODB | Lee vuelos activos y programados para asignar puertas. |
| M4 Ground Operations | M1 AODB, M3 | Requiere ETA y puerta/posición asignada para movilizar personal. |
| M5 Revenue & Billing | M1 AODB, M3 | Consume movimientos reales y uso de infraestructura para calcular cargos. |
| M6 Passenger Experience | M2 FIDS | Sincroniza tiempos de espera agregados. |
| M7 ETL & Analytics | M1, M4, M5 | Extrae registros hacia el área de trabajo medallion y los promueve hasta `ah_tactico`/`ah_estrategico`. |
| M9 Compliance Hub | M1 AODB | Audita modificaciones de itinerarios para reportes DGAC. |
| M8 Observability | Todos | Consumidor universal de métricas, logs y trazas. |

## 2.4 Clases de usuario y características

Ver matriz completa de actores y roles RBAC en la Sección 3, incluyendo la distinción entre roles con acceso a la base operacional y roles con acceso a la capa analítica.

## 2.5 Entorno operativo

SPA en Angular 20+ (portal operativo, dashboards BI, reproductores FIDS); backend en FastAPI (Python) tras un API Gateway único (AuthN/AuthZ JWT, rate limiting, canal WebSocket, verificación de licencia por módulo); **base operacional MonetDB**; orquestación de pipelines Airflow con arquitectura medallion sobre almacenamiento Parquet; **capa analítica ClickHouse dual** (`ah_tactico`, `ah_estrategico`); observabilidad mediante la pila LGTM (Grafana, Prometheus, Loki). Despliegue en infraestructura declarativa (IaC) en fase Scale, con evolución hacia multi-región con residencia de datos por país.

## 2.6 Restricciones de diseño e implementación

- **Ningún componente distinto de la capa de repositorio puede emitir SQL hacia MonetDB.** Este control sustituye al RLS perdido y es puerta de release verificada por análisis estático en CI (Sección 8.2, PN-15).
- El filtro por `tenant_id` en la base operacional se obtiene exclusivamente del token JWT validado, nunca del cuerpo de la petición; toda discrepancia se registra y alerta (PN-02).
- Prohibición de `DELETE` físico en tablas de negocio: las bajas son lógicas.
- El esquema `compliance` es append-only, con la única excepción controlada de `post_mortem`/`post_mortem_accion`, editable exclusivamente por `role_sre`.
- La capa analítica (ClickHouse) sí conserva enforcement estructural de tenant mediante políticas de fila (`CREATE ROW POLICY`); ningún rol posee escritura simultánea en `ah_tactico` y `ah_estrategico`.
- Las APIs deben documentarse bajo OpenAPI 3.1 y validarse automáticamente en CI (linter Spectral, cero errores).
- Todo artefacto que no supere la validación de contrato de datos en la transición bronce→plata debe derivarse a cuarentena, sin excepción (RF-T12).

## 2.7 Supuestos y dependencias

- El aeropuerto tenant provee registros operativos de vuelos e itinerarios mediante ingesta diaria hacia la capa bronce.
- El pipeline comercial (leads, oportunidades) reside en un CRM externo, no en `billing` (Sección 7.7).
- El costo cloud por tenant se consulta desde la consola de facturación del proveedor PaaS; su eventual persistencia histórica se trata en el Apéndice A.
- **Riesgo abierto asumido por diseño:** MonetDB no ofrece PITR ni replicación streaming equivalentes a los de un motor con soporte nativo. El cumplimiento de RNF-R01 (Sección 5.2) depende de una estrategia de continuidad basada en respaldo lógico programado y no puede darse por satisfecho hasta que la prueba de restauración semanal lo demuestre de forma sostenida.

---

# 3. Actores del sistema y modelo de control de acceso (RBAC)

La organización de actores, módulos y permisos se rige por un eje departamental único; cada departamento es propietario de sus módulos y de los roles de sistema que operan sobre él. **Desde esta versión, el modelo de aislamiento es asimétrico** (Sección 9.2): el eje de tenant en la base operacional es un control de aplicación, mientras que el eje departamental (ambas capas) y el eje de tenant en la capa analítica son controles estructurales de motor.

## 3.1 Actores internos (AeroHub)

| Departamento | Actor | Rol de sistema | Alcance |
|:---|:---|:---|:---|
| D5 — Plataforma y Seguridad | CTO | `role_platform_admin` | Gestión global de tenants, configuración de plataforma, acceso de emergencia (break-glass) auditado. |
| D5 — Plataforma y Seguridad | SRE / Director de Operaciones Cloud | `role_sre` | Infraestructura, observabilidad, secretos y despliegues; único rol con `UPDATE` sobre `post_mortem`/`post_mortem_accion`. |
| D4 — Datos e IA | Director de Datos e IA / Data Engineer | `role_data_engineer` | Accede a la base operacional exclusivamente **vía `role_elt_reader`**; lectura/escritura en `etl_control`; lectura sin política de fila en `ah_tactico` para diagnóstico de pipeline (auditado). |
| D4 — Datos e IA | ML Engineer | `role_ml_engineer` | Registro de modelos y features en `etl_control`; lectura de hechos/features en `ah_tactico` sin política de fila (entrenamiento con corpus cruzado, auditado). |
| D6 — Soporte e Implementación | Especialista de Implementación | `role_implementation` | Aprovisionamiento y configuración inicial por tenant; acceso temporal con caducidad automática. |
| D6 — Soporte e Implementación | Especialista DevRel | `role_support` | Tickets, base de conocimientos, changelog; lectura limitada, nunca datos financieros. |
| D3 — Crecimiento Comercial | Director de Crecimiento Comercial | `role_business_viewer` | Escritura sobre `okr`/`okr_resultado_clave`; solo lectura de `ah_estrategico`, **sin acceso a `ah_tactico`**. |
| D5 — Plataforma y Seguridad | — | `role_people_viewer` | Único rol con acceso al esquema `people` en la base operacional; en la capa analítica, solo lectura de `resumen_talento_trimestral` en `ah_estrategico`. |
| D4 / D5 (técnico, sin actor humano) | Identidad técnica de Airflow | `role_elt_reader` (lectura operacional) / `role_elt_writer` (escritura analítica) | `role_elt_reader` es de solo lectura sobre toda la base operacional y el único autorizado a alimentar el área de trabajo medallion. `role_elt_writer` es el único rol con escritura simultánea en `ah_tactico` y `ah_estrategico`. |

## 3.2 Actores externos (por tenant)

| Departamento funcional | Actor | Rol de sistema | Alcance |
|:---|:---|:---|:---|
| D1 — Operaciones | Administrador del Aeropuerto (Tenant Admin) | `role_tenant_admin` | CRUD de usuarios locales, API Keys, licencias y configuración FIDS de su tenant. |
| D1 — Operaciones | Controlador de Operaciones | `role_operations_controller` | Registra vuelos, asigna puertas, gestiona desvíos e incidencias operativas. |
| D1 — Operaciones | Aerolínea Coordinadora | `role_airline_coordinator` | Actualiza itinerarios propios (sub-ámbito por `airline_id`); acceso exclusivo vía API. |
| D2 — Rampa | Agente de Rampa (Ground Handling) | `role_ramp_agent` | Registra tiempos de turnaround del vuelo asignado; mínimo privilegio. |
| D3 — Comercial y Finanzas | Operador de Facturación del Tenant | `role_billing_officer` | Concilia facturas, gestiona disputas. |
| D4 — Datos e IA | Analista del Tenant | `role_tenant_analyst` | Solo lectura de `ah_tactico`, **con política de fila estructural restringida a su `tenant_id`** (único rol de tenant con acceso analítico de detalle). |
| D5 — Plataforma y Seguridad | Auditor de Regulación Aérea (DGAC/OACI) | `role_regulatory_auditor` | Solo lectura de reportes de cumplimiento y logs de auditoría; acceso temporal, nominal y registrado. |

**Stakeholder pasivo (no actor de sistema):** el Pasajero Final consume las pantallas FIDS públicas y aplicaciones de terceros conectadas a la API del aeropuerto; no se autentica y por tanto no forma parte del catálogo RBAC.

## 3.3 Modelo de permisos por capa (síntesis)

| Eje de control | Base operacional (MonetDB) | Capa analítica (ClickHouse) |
|:---|:---|:---|
| Tenant | Control de **aplicación**: filtro inyectado desde el token por la capa de repositorio. Falla abierto ante error de programación; mitigado por los controles compensatorios de la Sección 9.3. | Control **estructural**: políticas de fila evaluadas por el motor. Falla cerrado. |
| Departamento | Control **estructural**: privilegios de esquema en el motor. Falla cerrado. | Control **estructural**: privilegios por base y por tabla; segregación total entre `ah_tactico` y `ah_estrategico`. Falla cerrado. |

La convención de permisos por esquema (**U** = USAGE, **S** = SELECT, **I** = INSERT, **Up** = UPDATE, **—** = sin acceso) se mantiene sin cambio; no se otorga `DELETE` a ningún rol de negocio.

## 3.4 Principios transversales de acceso

- **Mínimo privilegio:** cada rol posee únicamente los permisos definidos por su matriz de capa; toda ampliación requiere aprobación del owner del departamento y registro en `compliance`.
- **Segregación de funciones:** quien despliega (SRE) no accede a datos financieros; quien factura no modifica datos operativos; `role_elt_reader` es de solo lectura sobre la base operacional y el único autorizado a escribir en el área de trabajo medallion.
- **Doble eje de aislamiento, asimétrico desde esta versión:** ver Sección 3.3 y Sección 9.2.
- **Autenticación:** MFA obligatorio para todos los roles internos y para `role_tenant_admin`; API Keys con rotación automática; JWT de corta vida emitidos por el API Gateway.
- **Revisión de accesos:** recertificación trimestral de asignaciones rol-usuario por departamento.
- **Auditoría inmutable:** el esquema `compliance` es append-only salvo `post_mortem`/`post_mortem_accion`; al carecer MonetDB de triggers equivalentes a los de un motor con soporte nativo, la escritura del log de auditoría es responsabilidad de la capa de repositorio, verificada por la misma regla de análisis estático que el filtro de tenant.
- **Sin SQL fuera de la capa de repositorio:** control que sustituye al aislamiento de motor perdido; su cumplimiento es puerta de release (PN-15).

---

# 4. Catálogo de requisitos funcionales

Prioridad según MoSCoW (M = Must, S = Should, C = Could). Cada requisito traza a su objetivo de origen y define un criterio de aceptación verificable, base de las condiciones de prueba de la Sección 8.

## 4.1 Requisitos de nivel estratégico

| ID | Descripción | Prioridad | Fuente | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| RF-E01 | Tablero BSC con los KPIs de las cuatro perspectivas actualizado diariamente, servido desde `ah_estrategico.kpi_snapshot`. | S | OE1, OT13 | KPIs visibles con fecha de corte ≤ 24 h; diseño conforme a RNF-U01 (patrón de lectura Z). |
| RF-E02 | Consolidación de ingresos por tasas, slots y Pax por tenant y período. | M | OE1, OT2 | Reporte mensual concilia al 100 % con las facturas emitidas. |
| RF-E03 | Exposición del estado de disponibilidad (uptime) de los servicios críticos AODB/FIDS. | M | OE3 | Panel de uptime con granularidad mensual y consumo de error budget. |
| RF-E04 | Generación de reportes de conformidad normativa (DGAC/OACI) a partir del log de auditoría. | M | OE3 | Reporte exportable con evidencias trazables a eventos auditados. |
| RF-E05 | Configuración de metas y OKRs operativos por departamento. | C | OE5 | Metas versionadas con responsable y período, con resultados clave en tabla propia (`okr_resultado_clave`). |
| RF-E06 | Registro y visualización de métricas de clima laboral (eNPS) internas. | C | OE5 | Encuesta trimestral con resultados agregados y anónimos (anonimidad estructural, RNF-S05). |

## 4.2 Requisitos de nivel táctico

| ID | Descripción | Prioridad | Fuente | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| RF-T01 | Aprovisionamiento de entornos sandbox por tenant con datos sintéticos. | S | OT1 | Sandbox operativo en < 10 minutos desde la solicitud. |
| RF-T02 | Publicación de la API del AODB conforme a OpenAPI 3.1 validada automáticamente. | M | OT3 | Especificación con 0 errores en el linter (Spectral) en CI. |
| RF-T03 | Diseño y publicación de plantillas FIDS para pantallas físicas. | M | OT4 | Plantilla publicada se refleja en pantallas en < 1 s (interno). |
| RF-T04 | Validación de cada lote de ingesta contra contratos de datos formales en la transición bronce→plata. | M | OT7 | Lotes con violaciones quedan en cuarentena con reporte de causa (informe de validación, PN-12). |
| RF-T05 | Registro de versiones, métricas y drift de los modelos ML. | M | OT8 | Todo modelo en producción posee versión, dataset de entrenamiento y umbrales de drift. |
| RF-T06 | Pipeline CI/CD con análisis SAST, de dependencias y de contenedores en cada cambio. | M | OT6 | Ningún despliegue procede con hallazgos críticos abiertos. *(Proceso de ingeniería sin CU ni tabla asociados, por diseño.)* |
| RF-T07 | Administración del portal del desarrollador con SDKs y documentación interactiva. | S | OE2 | SDKs Python/TypeScript publicados y sincronizados con la API. |
| RF-T08 | Reporte de costo cloud por servicio y tenant con alertas de desviación. | S | OT14 | Alerta emitida ante desviación > 20 % del presupuesto mensual. |
| RF-T09 | Documentación estandarizada de decisiones arquitectónicas (ADR), incluyendo el estado de supersesión cuando corresponda. | M | OT9 | Toda decisión estructural posee ADR aprobado antes de implementarse. *(Proceso de ingeniería sin CU ni tabla asociados, por diseño.)* |
| RF-T10 | Soporte de experimentación de precios por volumen Pax/slots. | C | OT2 | Variantes de tarifario aplicables por tenant sin despliegue de código. |
| RF-T11 | Recopilación automática de evidencias de controles técnicos (logs de acceso, cifrado, backups, rotación de credenciales) exportables para auditoría SOC 2 Tipo II. | S | OT14 | Evidencia exportable trazable a `compliance.log_auditoria` y `compliance.reporte_dgac`, generada sin intervención manual. |
| RF-T12 | Promoción de artefactos entre capas medallion (bronce, plata, oro) únicamente si la validación de la transición resulta aprobada; los rechazados se derivan a cuarentena. | M | OT7 | Artefacto con contrato de datos inválido no promueve y queda en `/cuarentena` con informe de validación (PN-12). |

## 4.3 Requisitos de nivel operativo

| ID | Descripción | Prioridad | Fuente | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| RF-O01 | Aprovisionamiento de nuevos tenants, creando sus usuarios y su configuración base con aislamiento verificado por la capa de repositorio conforme al modelo de aplicación (ADR-014). | M | OP1 | Tenant operativo con aislamiento verificado en < 10 minutos (suite de pruebas cruzadas, Sección 8.2). |
| RF-O02 | Registro de vuelos y asignación de puertas de embarque manual y automática. | M | OE4, OP2a | Asignación sin conflictos de solapamiento, verificados en capa de aplicación (PN-05); conflicto detectado se notifica. |
| RF-O03 | Ingesta diaria de registros operativos de vuelos hacia la capa bronce del pipeline medallion. | M | OT7, OP11 | Carga diaria completa sin pérdida de registros; discrepancias reportadas y conteo de entrada/salida trazado en `etl_control`. |
| RF-O04 | Exposición del estado de vuelo en tiempo real vía API y WebSockets. | M | OE2, OP6 | Cambio de estado propagado a consumidores en < 1 s (interno). |
| RF-O05 | Reentrenamiento del modelo de predicción de demoras con validación temporal previa a promoción. | M | OP14 | Modelo promovido solo si MAPE ≤ 12 % en el holdout temporal, con comparación champion-challenger. |
| RF-O06 | Refresco de los tableros BI operativos conforme a la ventana definida. | S | OP13 | Refresco ≤ 5 minutos verificado por telemetría. |
| RF-O07 | Monitoreo de telemetría de pantallas FIDS (latencia, conexión, certificado). | M | OP6 | Pantalla sin señal genera alerta en < 60 s. |
| RF-O08 | Gestión de tickets de soporte con SLA por severidad. | M | OP2a, OP2b | Primera respuesta < 2 h en FIDS/AODB; < 4 h en rampa. |
| RF-O09 | Backups lógicos programados y pruebas de restauración automatizadas, ante la ausencia de PITR nativo en el motor operacional. | M | OP7 | Restauración semanal cumple RTO < 15 min y RPO ≤ 5 min; **criterio sujeto al riesgo abierto de RNF-R01 (Sección 2.7)**. |
| RF-O10 | Cálculo del consumo de error budget con bloqueo automático de despliegues al exceder el umbral. | S | OP9 | Despliegue bloqueado automáticamente al superar el 80 % del budget. |
| RF-O11 | Publicación del changelog del producto en el portal de clientes. | C | OP15 | Changelog semanal visible para todos los tenants, con ítems descompuestos en `changelog_item`. |
| RF-O12 | Rotación automática de credenciales, API Keys y certificados TLS. | M | OT6 | Rotación sin interrupción del servicio; evento registrado en auditoría. |
| RF-O13 | Elaboración de post-mortems con línea de tiempo automática de alertas, con acciones de remediación en tabla propia (`post_mortem_accion`). | S | OP16 | Post-mortem generado con eventos correlacionados del incidente; ciclo de vida auditado hasta el cierre. |
| RF-O14 | Gestión de la base de conocimientos con búsqueda semántica, con etiquetado normalizado (`articulo_kb_etiqueta`). | C | OE6 | Artículo publicado indexado y recuperable en el portal. |
| RF-O15 | Cálculo mensual de facturación por Pax y slots, aplicando el tarifario vigente (cabecera y detalle normalizados). | M | OP4 | Factura generada concilia con los movimientos del período sin diferencias. |
| RF-O16 | Registro de incidencias de rampa por desviación del estándar de turnaround con notificación. | S | OP2b | Incidencia generada en < 60 s tras superar el estándar. |
| RF-O17 | Estimación y publicación de tiempos de espera agregados por terminal, sin PII de pasajero. | C | OE4 | Actualización ≤ 15 minutos; 0 campos de PII en el modelo de datos (PN-11). |
| RF-O18 | Verificación de licencia vigente del tenant en cada acceso a un módulo, con denegación si no está activa, aplicada por el API Gateway como control de aplicación (ADR-014). | M | OP1 | Solicitud sin licencia retorna HTTP 403 en el 100 % de los casos; evento auditado (PN-09). |
| RF-O19 | Registro del estado, los conteos de entrada/salida y el checksum de cada ejecución ETL por capa medallion, impidiendo el reprocesamiento concurrente del mismo artefacto. | M | OT7, OP11 | Toda ejecución trazable en `etl_control.etl_ejecucion`; intento de reproceso concurrente rechazado por restricción única `(run_id, capa)` (PN-14). |

> **Nota de trazabilidad (AEROHUB-ADR-INTERNO-001):** RF-O19 adopta en este documento la definición de gobernanza de ejecuciones ETL, por estar sustentada de forma cruzada en el catálogo de casos de uso y en la batería de pruebas negativas de la fuente. La capacidad de captura automática de NPS/CSAT de operadores externos se preserva bajo el identificador provisional **RF-O19-bis** (Apéndice A) hasta el cierre formal de la errata solicitada.

---

# 5. Requisitos no funcionales (modelo de calidad ISO/IEC 25010)

## 5.1 Seguridad (Security)

| ID | Descripción | Prioridad | Fuente normativa | Criterio de aceptación |
|:---|:---|:---|:---|:---|
| RNF-S01 | Aislamiento multi-tenant en la base operacional: ningún usuario de un tenant podrá leer ni modificar datos de otro tenant. Control de **capa de aplicación** desde esta versión (ADR-014). | M | ISO/IEC 27002, 8.3 | Prueba negativa de acceso cruzado retorna HTTP 404 (no 403, para no confirmar la existencia del recurso ajeno) en el 100 % de los casos (PN-01); token con `tenant_id` discordante en el cuerpo es ignorado y alertado (PN-02). |
| RNF-S02 | Aislamiento departamental: ningún rol podrá operar sobre esquemas fuera de su matriz de permisos. Control **estructural de motor** en ambas capas. | M | ISO/IEC 27002, 5.15 | Prueba negativa por rol/esquema retorna denegación conforme a la matriz (PN-03, PN-08). |
| RNF-S03 | Cifrado en tránsito TLS 1.2+ (objetivo 1.3) en todas las interfaces; cifrado en reposo en MonetDB y ClickHouse. | M | ISO/IEC 27002, 8.24 | Escaneo de configuración sin protocolos ni cifrados débiles; verificado como puerta de release (PN-10). |
| RNF-S04 | Log de auditoría inmutable (append-only) para modificaciones de itinerarios, accesos y facturación. Al carecer MonetDB de triggers equivalentes a los de un motor con soporte nativo, la escritura es responsabilidad de la capa de repositorio, no del motor. | M | ISO/IEC 27002, 8.15 | Intento de UPDATE/DELETE sobre auditoría es rechazado y alertado (PN-04); toda operación mutante produce su registro correspondiente, verificado por muestreo en la suite de integración. |
| RNF-S05 | Minimización de datos personales: FIDS y módulos operativos no almacenarán PII de pasajeros. La encuesta de eNPS no referencia al empleado individual (anonimidad estructural). | M | ISO/IEC 27701 | Revisión de modelo de datos sin campos de PII; verificación dinámica (PN-11). |

## 5.2 Fiabilidad (Reliability)

| ID | Descripción | Prioridad | Fuente | Estado |
|:---|:---|:---|:---|:---|
| RNF-R01 | Continuidad operacional: RTO < 15 min y RPO ≤ 5 min sobre la base operacional, sostenidos mediante respaldo lógico programado y replicación de almacenamiento, dado que el motor operacional no ofrece PITR nativo equivalente al de PostgreSQL. | M | ISO/IEC 27002, 8.13 | **Riesgo abierto declarado por la fuente normativa: no puede darse por satisfecho hasta que la prueba de restauración semanal automatizada lo demuestre de forma sostenida (RF-O09).** No se documenta como control cerrado. |
| RNF-R02 | SLA de uptime de 99.9 % en fase MVP y 99.95 % en fase Scale para AODB/FIDS. *(Identificador editorial, sin contraparte numerada en la fuente; ver Sección 5.7.)* | M | RF-E03, OE3 | Cerrado, verificado por panel de uptime. |
| RNF-R03 | Bloqueo automático de despliegues al superar el 80 % del error budget mensual. *(Identificador editorial.)* | S | RF-O10 | Cerrado. |
| RNF-R04 | Detección de pantalla FIDS sin señal en menos de 60 segundos. *(Identificador editorial.)* | M | RF-O07 | Cerrado. |

## 5.3 Eficiencia de desempeño (Performance Efficiency) — identificadores editoriales

| ID | Descripción | Prioridad | Requisito funcional relacionado |
|:---|:---|:---|:---|
| RNF-P01 | Propagación de cambios de estado de vuelo a consumidores en < 1 segundo (interno). | M | RF-O04 |
| RNF-P02 | Reflejo de plantillas FIDS publicadas en pantallas físicas en < 1 segundo (interno). | M | RF-T03 |
| RNF-P03 | Refresco de tableros BI operativos en ≤ 5 minutos. | S | RF-O06 |
| RNF-P04 | Aprovisionamiento de tenant y sandbox en < 10 minutos. | S/M | RF-O01, RF-T01 |
| RNF-P05 | Carga incremental diaria hacia `ah_tactico` en menos de 10 minutos, sin duplicación ante recarga del mismo período. | S | RF-O19 |

## 5.4 Mantenibilidad (Maintainability) — identificadores editoriales

| ID | Descripción | Prioridad | Justificación |
|:---|:---|:---|:---|
| RNF-M01 | El modelo de datos operacional debe alcanzar BCNF en todas las tablas transaccionales y 4NF en las entidades con hechos multivaluados independientes, evitando dependencias transitivas y grupos repetitivos. | M | Sección 7.2; corrige violaciones de 1NF/2NF/3NF identificadas en la revisión previa del modelo. |
| RNF-M02 | Todo ADR debe documentar contexto, decisión, alternativas descartadas y consecuencias, incluyendo el estado de supersesión cuando corresponda. | S | RF-T09; ISO/IEC/IEEE 42010. |
| RNF-M03 | La retención y el archivado de tablas de alto volumen deben implementarse mediante particionamiento por rango, permitiendo operaciones de desconexión de partición en tiempo constante en vez de borrado masivo. | S | Eficiencia de recursos (ISO/IEC 25010); ver Apéndice A para la capacidad de retención pendiente de confirmación normativa. |

## 5.5 Compatibilidad (Compatibility) — Interfaces externas

| ID | Descripción | Prioridad | Mecanismo |
|:---|:---|:---|:---|
| RNF-C01 | Integración con el CRM comercial de terceros para el pipeline de leads y oportunidades. | S | Webhook/API REST hacia el API Gateway; fuente de verdad reside en el CRM. |
| RNF-C02 | Integración con la consola de facturación del proveedor PaaS para costo cloud por tenant. | S | Consulta periódica vía API por un job de D5; sin replicación salvo necesidad de auditoría histórica. |
| RNF-C03 | Publicación de API pública conforme a OpenAPI 3.1, con SDKs sincronizados en Python y TypeScript. | M | RF-T02, RF-T07. |

## 5.6 Usabilidad y portabilidad

| ID | Descripción | Prioridad | Fuente |
|:---|:---|:---|:---|
| RNF-U01 | Los tableros estratégicos adoptarán patrón de lectura en Z y los tácticos en F; los operativos, posición fija sin recorrido (*glanceability*). El KPI de mayor prioridad ocupa el cuadrante superior izquierdo; métricas relacionadas se agrupan en cuadrantes contiguos; el color codifica desviación respecto a la meta, nunca la identidad de la métrica; todo KPI declara su tabla de origen. | S | ISO/IEC 25010 (usabilidad); revisión de diseño por tipo de tablero, verificación mediante `dim_kpi.fuente_tabla`. |
| RNF-U02 | El portal operativo, dashboards BI y reproductores FIDS deben implementarse sobre un único framework frontend (Angular 20+). *(Identificador editorial, renumerado desde RNF-U01 v1.0 para resolver la colisión con el RNF-U01 oficial de la fuente.)* | S | Reducción de superficie de mantenimiento. |
| RNF-PO01 | Los reproductores FIDS deben construirse como build ligero del mismo monorepo, portables a hardware de terminal de recursos limitados. | S | Consolidación de frontend. |

## 5.7 Nota sobre numeración de identificadores no oficiales

Los identificadores marcados como "editoriales" en esta sección (RNF-R02 a RNF-R04, RNF-P01 a RNF-P05, RNF-M01 a RNF-M03, RNF-C01 a RNF-C03, RNF-U02, RNF-PO01) fueron acuñados por el equipo de Ingeniería de Requisitos para dar cobertura completa a las ocho características de ISO/IEC 25010; **no existen como identificadores en el documento fuente**. Se conservan en una subsección propia dentro de cada característica para que una auditoría futura no los busque erróneamente en el Análisis Documental Estratégico.

---

# 6. Arquitectura de referencia (ISO/IEC/IEEE 42010)

## 6.1 Vista general de componentes

```
Angular 20+ (SPA) — Portal Operativo · Dashboards BI · FIDS Players
        │ HTTPS / WSS
        ▼
API Gateway (FastAPI) — AuthN/AuthZ JWT · Rate limiting · Validación
        │ de licencia por módulo (RF-O18) · WebSocket gateway
        ▼
Capa de repositorio (único emisor de SQL hacia MonetDB — PN-15)
        │
        ▼
Base Operacional MonetDB — esquemas: ops, rampa, billing, compliance,
tenants, support, people, etl_control (aislamiento de tenant de
capa de aplicación; aislamiento departamental estructural)
        │ extracción hacia área de trabajo medallion
        ▼
/data/bronce → /data/plata → /data/oro → /data/cuarentena (Parquet)
        │ orquestado por Airflow, gobernado por etl_control
        ▼
ClickHouse `ah_tactico` (detalle histórico, política de fila por tenant)
        │ derivación unidireccional, reconciliación tolerancia cero
        ▼
ClickHouse `ah_estrategico` (KPI agregados, sin acceso de role_tenant_analyst)
```

## 6.2 Decisiones arquitectónicas rectoras

| Principio | Descripción |
|:---|:---|
| Aislamiento asimétrico por diseño | El eje de tenant se degrada de control estructural a control de aplicación únicamente en la base operacional; los otros tres cuadrantes (departamental en ambas capas, tenant en la analítica) conservan enforcement de motor. |
| Separación capa/estado en el pipeline | La capa de refinamiento (bronce/plata/oro) y el estado de ejecución (CRUDO/PROCESANDO/TERMINADO/RECHAZADO) son dimensiones ortogonales, gobernadas de forma independiente en `etl_control`. |
| Derivación unidireccional estratégica | Ningún KPI de `ah_estrategico` se publica sin ser reproducible con tolerancia cero desde el detalle de `ah_tactico`. |
| Capa de repositorio como control compensatorio | Sustituye funcionalmente al RLS perdido; su cumplimiento es puerta de release no negociable (PN-15). |

## 6.3 Estado de las decisiones arquitectónicas fundacionales

| ADR | Estado | Sustituido por | Nota |
|:---|:---|:---|:---|
| ADR-001 — PostgreSQL como motor operacional | **Supersedido** | ADR-013 | Se conserva el registro histórico; las causas que motivaron el abandono del motor previo (concurrencia, replicación, RPO) siguen vigentes y deben responderse mediante los controles compensatorios de ADR-014. |
| ADR-003 — ClickHouse staging / MonetDB DW | **Supersedido** | ADR-012 | ClickHouse asume el almacén analítico completo, segmentado en dos bases; MonetDB pasa a la capa operacional. |
| ADR-005 — Aislamiento estructural operacional vs. lógico analítico | **Supersedido** | ADR-014 | La premisa (RLS disponible en el motor operacional) deja de cumplirse; la asimetría se invierte. |
| ADR-012 — Roles de ClickHouse dual (`ah_tactico`/`ah_estrategico`) | Vigente | — | Segrega detalle transaccional de KPI de consumo estratégico. |
| ADR-013 — MonetDB como motor operacional | Vigente | — | Implica la pérdida de RLS, PITR y triggers nativos; controles compensatorios en ADR-014. |
| ADR-014 — Aislamiento asimétrico y controles compensatorios | Vigente | — | Ver Sección 9.2–9.3 de este documento. |
| ADR-015 — Arquitectura medallion y gobierno de `etl_control` | Vigente | — | Ver Sección 7.5. |
| ADR-016 — Derivación reconciliada `ah_tactico` → `ah_estrategico` | Vigente | — | Ver Sección 7.6. |

## 6.4 Tecnologías retiradas (antecedente obligatorio)

| Tecnología retirada | Sustituto | Motivo |
|:---|:---|:---|
| PocketBase (SQLite) como AODB | MonetDB (vía PostgreSQL como paso intermedio, ahora también retirado) | Incompatibilidad con SLA, replicación y concurrencia. |
| Next.js (BFF) | API Gateway FastAPI + Angular único | Eliminación de doble framework y doble runtime. |
| DuckDB en el pipeline | ClickHouse | Redundancia de motores analíticos. |
| PWA/Flutter para rampa | Interfaz responsiva Angular | Consolidación de frontend. |
| **PostgreSQL como base operacional** | **MonetDB** | Decisión de plataforma (ADR-013); implica pérdida de RLS, PITR y triggers nativos. |
| **MonetDB como Data Warehouse** | **ClickHouse (`ah_tactico`)** | El DW migra a ClickHouse (ADR-012). |
| **Esquema `analytics_bsc` en la base operacional** | **`ah_estrategico.kpi_snapshot`** | Los KPI consolidados son datos analíticos (ADR-016). |
| **Capas Raw/Cleansed en ClickHouse** | **Medallion bronce/plata/oro en disco** | El refinamiento ocurre en artefactos Parquet auditables antes de la carga (ADR-015). |

Ningún componente de esta tabla puede reintroducirse en un artefacto de diseño (IEEE 1016) sin un nuevo ADR que revierta explícitamente la decisión correspondiente.

---

# 7. Modelo de datos por dominio

## 7.1 Esquemas de la base operacional (MonetDB)

| Esquema | Alcance | Mecanismo de aislamiento de tenant | Función |
|:---|:---|:---|:---|
| `ops` | Por tenant | Capa de aplicación | Vuelos, estados, aeronaves, causas de demora, puertas, plantillas y pantallas FIDS. |
| `rampa` | Por tenant | Capa de aplicación | `turnaround` (entidad propia que empareja llegada/salida), tareas, incidencias. |
| `billing` | Por tenant | Capa de aplicación | Tarifario (cabecera/detalle normalizado), líneas de factura, tiempos de espera agregados. |
| `compliance` | Por tenant (mayormente) | Capa de aplicación | Log de auditoría append-only, incidentes, reportes DGAC, evidencia SOC 2, `post_mortem`/`post_mortem_accion`. |
| `tenants` | Por tenant | Capa de aplicación | Usuarios, API Keys, licencias, catálogo de roles, OKRs internos. |
| `support` | Por tenant | Capa de aplicación | Tickets con hilo de mensajes (`ticket_mensaje`), base de conocimientos etiquetada, changelog descompuesto. |
| `people` | Interno AeroHub | Sin `tenant_id` (por diseño); único acceso `role_people_viewer` | eNPS anonimizada estructuralmente, métricas de talento. |
| `etl_control` | Técnico, sin `tenant_id` | No aplica | Gobierno de ejecuciones del pipeline medallion (Sección 7.5). |

## 7.2 Normalización del modelo operacional

El modelo alcanza **BCNF** en todas las tablas transaccionales y **4NF** en las entidades con hechos multivaluados independientes.

| Forma normal | Corrección aplicada |
|:---|:---|
| 1NF | Grupos repetitivos descompuestos: `post_mortem_accion`, `changelog_item`, `articulo_kb_etiqueta`, `okr_resultado_clave`, `ticket_mensaje`. |
| 2NF | `tarifario` (cabecera) separado de `tarifario_concepto` (detalle), eliminando dependencia parcial de clave compuesta. |
| 3NF | Eliminación de atributos derivados almacenados (`vuelo.estado_actual`, `factura.total`, `conciliacion_pax.diferencia`); `puerta.terminal` reemplazado por FK a `terminal`. |
| BCNF | `aeropuerto` y `aerolinea` con doble clave candidata (`id` sustituta, `codigo_iata` natural), ambas determinando la tupla completa sin dependencias cruzadas. |
| 4NF | Hechos multivaluados independientes de `vuelo` (estados, demoras, asignaciones de puerta) separados en relaciones propias, evitando producto cartesiano. |
| 5NF | `tarifario_concepto` resuelve la relación ternaria tarifario-concepto-precio sin descomposición adicional posible sin pérdida. |

**Denormalizaciones deliberadas (documentadas, no defectos):** `cargo_aeronautico.tarifa_aplicada`/`monto_calculado` y `factura_linea.precio_unitario`/`monto` se mantienen como instantánea inmutable del cálculo, por integridad financiera y de auditoría; `encuesta_enps_respuesta.categoria_derivada` se materializa para permitir agregación sin exponer la puntuación individual.

**Entidad nueva relevante:** `rampa.turnaround`, que empareja explícitamente vuelo de llegada y vuelo de salida, en lugar de inferir el emparejamiento por convención a partir de las tareas individuales.

## 7.3 Arquitectura medallion y gobierno de ejecuciones ETL

### 7.3.1 Estructura del área de trabajo

```
/data
  /bronce      <- ingesta cruda, inmutable, retención 90 días
  /plata       <- validado y normalizado, retención 30 días
  /oro         <- agregados listos para carga, retención 30 días
  /cuarentena  <- artefactos RECHAZADOS, retención 180 días
```

Formato Parquet en las tres capas; particionamiento por fecha y tenant, habilitando el reproceso de un día de un tenant específico sin afectar al resto.

### 7.3.2 Separación entre capa y estado de ejecución

Capa (bronce/plata/oro) y estado (`CRUDO`/`PROCESANDO`/`TERMINADO`/`RECHAZADO`) son dimensiones ortogonales, registradas de forma independiente en `etl_control.etl_ejecucion`, con un manifiesto `_manifest.json` por ejecución que garantiza reconstruibilidad ante pérdida de la base de control.

### 7.3.3 Puntos de validación por transición

| Transición | Validación | Falla implica |
|:---|:---|:---|
| Origen → Bronce | Integridad de transferencia (checksum, conteo, formato) | `RECHAZADO`; el archivo original permanece en origen para reintento. |
| Bronce → Plata | Contrato de datos (esquema, tipos, dominios, nulos, duplicados) | `RECHAZADO`; artefacto a `/cuarentena` con informe de validación (RF-T12, PN-12). |
| Plata → Oro | Reglas de negocio (conciliación, integridad referencial, coherencia temporal) | `RECHAZADO`; el agregado no se construye. |
| Oro → ClickHouse | Idempotencia de carga, conteo destino = conteo origen | Rollback de la partición cargada. |
| `ah_tactico` → `ah_estrategico` | Reconciliación de tolerancia cero | La agregación no se publica; el tablero conserva el corte anterior. |

La unicidad de `(run_id, capa)` en `etl_control.etl_ejecucion` impide el reprocesamiento concurrente del mismo artefacto (RF-O19, PN-14).

## 7.4 Capa analítica dual (ClickHouse)

`ah_tactico` almacena el detalle histórico con política de fila estructural por tenant; `ah_estrategico` almacena únicamente KPI agregados derivados unidireccionalmente, poblados por la identidad técnica `role_elt_writer`. Ningún rol posee escritura simultánea en ambas bases; `role_business_viewer` accede a `ah_estrategico` pero no a `ah_tactico` (mínimo privilegio, verificado por PN-13). El catálogo `dim_kpi` permite que cada KPI declare su tabla de origen, sustentando RNF-U01.

## 7.5 Diagrama de dependencias entre módulos

Ver tabla de la Sección 2.3.

## 7.6 Fuentes de datos externas no modeladas

| RF / OT | Fuente externa | Mecanismo de integración | Responsable |
|:---|:---|:---|:---|
| RF-E01 (parcial), OT13 | CRM comercial de terceros | Webhook/API REST hacia el API Gateway | D3 — Crecimiento Comercial |
| RF-T08, OT14 | Consola de facturación del proveedor PaaS | API consultada periódicamente por un job de D5 | D5 — Plataforma y Seguridad |

Ver Apéndice A para la eventual persistencia histórica de costo cloud, actualmente sin esquema confirmado.

---

# 8. Verificación y validación (ISO/IEC/IEEE 29119)

## 8.1 Niveles de prueba

| Nivel | Alcance | Automatización |
|:---|:---|:---|
| Unitarias | Lógica de servicios FastAPI, transformaciones Polars, reglas de tarifario | 100 % en CI; cobertura ≥ 80 % en módulos críticos. |
| Integración | API Gateway ↔ capa de repositorio ↔ MonetDB; DAGs Airflow ↔ capas medallion ↔ ClickHouse | CI con contenedores efímeros; incluye la suite cruzada por tenant de ADR-014. |
| Sistema | Flujos extremo a extremo por caso de uso | Suite E2E nocturna. |
| Aceptación | Criterios de aceptación de RF por el tenant piloto | Checklist por RF en onboarding. |

## 8.2 Batería de pruebas negativas (obligatoria por release)

> Al migrar el aislamiento de tenant del motor a la capa de aplicación, PN-01 a PN-03 verifican la capa de repositorio y el API Gateway, no el comportamiento del motor. PN-12 a PN-15 son incorporaciones de esta versión.

| ID | Condición de prueba | Punto de enforcement | Resultado esperado |
|:---|:---|:---|:---|
| PN-01 | Usuario del tenant A solicita por API un recurso identificado del tenant B | Capa de repositorio | HTTP 404 (no 403); evento registrado con el `tenant_id` del token. |
| PN-02 | Petición con `tenant_id` explícito en el cuerpo distinto al del token JWT | API Gateway | El valor del cuerpo se ignora; discrepancia registrada y alertada. |
| PN-03 | Rol sin privilegio sobre un esquema departamental intenta consultarlo | Motor MonetDB | Denegación por el motor. |
| PN-04 | Intento de UPDATE/DELETE sobre `compliance.log_auditoria` | Motor + capa de repositorio | Denegación; sin método de mutación expuesto. |
| PN-05 | Asignación de dos vuelos solapados a la misma puerta | Capa de aplicación | Rechazo por conflicto de intervalos (verificación explícita, ante ausencia de restricción de exclusión nativa por rango). |
| PN-06 | API Key revocada o expirada invoca cualquier endpoint | API Gateway | HTTP 401; evento auditado. |
| PN-07 | Token JWT expirado o con scope insuficiente contra la API analítica | API Gateway | HTTP 401/403; sin fuga de información. |
| PN-08 | Cualquier rol distinto de `role_people_viewer` consulta el esquema `people` | Motor MonetDB | Denegación, incluso para `role_platform_admin`. |
| PN-09 | Tenant sin licencia activa invoca la API de un módulo | API Gateway (RF-O18) | HTTP 403; evento auditado. |
| PN-10 | Conexión con TLS < 1.2 o cifrado en reposo deshabilitado | Infraestructura / CI | Conexión rechazada; escaneo como puerta de release. |
| PN-11 | Campo que identifique nominalmente a un pasajero en M2/M6 | Validación de esquema | Rechazo; sin columna de destino en el modelo. |
| PN-12 | Artefacto con contrato de datos inválido intenta promover de bronce a plata | Great Expectations / DAG | No promueve; deriva a `/cuarentena` con informe (RF-T12). |
| PN-13 | `role_business_viewer` consulta `ah_tactico`; `role_tenant_analyst` consulta filas de otro tenant en `ah_tactico` | ClickHouse | Denegación en el primer caso; 0 filas en el segundo. |
| PN-14 | Dos DAGs procesan concurrentemente el mismo `(run_id, capa)` | Restricción única en `etl_control` | La segunda ejecución es rechazada por violación de unicidad (RF-O19). |
| PN-15 | Un módulo fuera de la capa de repositorio contiene un literal SQL dirigido a MonetDB | Análisis estático en CI | El build falla. |

## 8.3 Criterios de entrada y salida de la fase Sistema

**Entrada:** entorno de staging con datos sintéticos representativos y al menos dos tenants poblados. **Salida:** suite E2E y PN-01 a PN-15 en verde; suite de pruebas cruzadas por tenant con cobertura del 100 % de los endpoints que acceden a datos de tenant; prueba de restauración cumpliendo RNF-R01 (sin excepción, dado su carácter de riesgo abierto declarado).

## 8.4 Validación del modelo ML

Partición temporal estricta (sin mezcla aleatoria que induzca fuga temporal); criterio de promoción MAPE ≤ 12 % sobre holdout con comparación champion-challenger; monitoreo de drift en producción con umbrales de reentrenamiento; explicabilidad mediante valores SHAP versionados junto al modelo.

---

# 9. Seguridad de la información y privacidad (ISO/IEC 27001/27002/27701)

## 9.1 Clasificación de información

Datos operativos de vuelo (por tenant), datos financieros y de facturación (por tenant), datos de auditoría y cumplimiento (por tenant, append-only salvo excepción controlada), datos internos de AeroHub (talento, OKRs, sin `tenant_id`), evidencia de auditoría externa SOC 2 (inmutable en su totalidad), y detalle/agregado analítico segmentado por nivel de decisión.

## 9.2 Modelo de aislamiento asimétrico (cambio central de esta versión)

| Eje | Base operacional (MonetDB) | Capa analítica (ClickHouse) |
|:---|:---|:---|
| Tenant | Control de **aplicación**: filtro inyectado desde el token por la capa de repositorio. **Falla abierto** ante error de programación. | Control **estructural**: políticas de fila evaluadas por el motor. **Falla cerrado**. |
| Departamento | Control **estructural**: privilegios de esquema en el motor. Falla cerrado. | Control **estructural**: privilegios por base y tabla. Falla cerrado. |

**Lectura obligatoria de esta tabla:** tres de los cuatro cuadrantes conservan enforcement de motor. El único degradado es el eje de tenant en la capa operacional, consecuencia directa y asumida de la migración a MonetDB (ADR-013). La superficie de mayor volumen de datos históricos —la analítica— mantiene garantía estructural.

## 9.3 Controles compensatorios obligatorios

1. La capa de repositorio es el único emisor de SQL hacia MonetDB.
2. El `tenant_id` se toma siempre del token validado, nunca del cuerpo de la petición.
3. Análisis estático en CI que rechaza SQL fuera de la capa de repositorio (PN-15).
4. Suite de pruebas cruzadas por tenant sobre el 100 % de los endpoints, con filas canario permanentes por tenant para verificación continua.

## 9.4 Riesgo residual declarado (no eliminable)

Una consulta añadida dentro de la propia capa de repositorio que omita el filtro de tenant no sería detectada por el análisis estático (el SQL está en el lugar correcto) y solo se detectaría por la suite cruzada si el endpoint afectado está cubierto. Este riesgo es inherente a la migración del control al plano de aplicación; se acota, no se elimina, mediante la cobertura obligatoria del 100 % de endpoints como criterio de salida (Sección 8.3). **Este riesgo debe permanecer visible en toda revisión de seguridad futura y no debe presentarse como mitigado.**

## 9.5 Controles aplicables (ISO/IEC 27002)

| Control | Implementación en AeroHub |
|:---|:---|
| 5.15 / 5.18 | Matriz RBAC (Sección 3); recertificación trimestral. |
| 8.2 / 8.3 | Mínimo privilegio; segregación de funciones inter-departamental. |
| 8.5 | MFA para internos y `role_tenant_admin`; JWT de corta vida; API Keys con scopes. |
| 8.15 | `compliance.log_auditoria` append-only, poblado por la capa de repositorio. |
| 8.16 | Observabilidad LGTM con alertas por severidad. |
| 8.24 | TLS 1.2+ en tránsito; cifrado en reposo en MonetDB y ClickHouse; secretos en vault con rotación. |
| 8.25 / 8.28 | SAST, análisis de dependencias y contenedores, lint de código y de API en CI. |
| 5.24–5.26 | Severidades Sev1–Sev3, runbooks, post-mortems blameless en < 72 h. |

## 9.6 Privacidad (ISO/IEC 27701)

AeroHub actúa como Encargado del Tratamiento (Processor); cada aeropuerto tenant es Responsable (Controller), mediante Acuerdo de Tratamiento de Datos (DPA). Los módulos operativos y el FIDS no capturan PII de pasajeros; **todo componente de visión artificial para estimación de flujos queda retirado del alcance por implicar tratamiento biométrico de alta sensibilidad sin necesidad funcional demostrada.** La PII gestionada se limita a datos de usuarios del sistema, con derechos del titular implementados (acceso, rectificación, supresión lógica). En fase Scale, la arquitectura multi-región garantizará residencia de datos por país conforme a la normativa local (LOPDP Ecuador, Ley 29733 Perú, Ley 1581 Colombia); el mecanismo técnico de verificación de residencia se documenta en el Apéndice A hasta el cierre de su numeración normativa.

---

# 10. Matriz de trazabilidad (síntesis)

| Nivel | Origen | Destino | Mecanismo de verificación |
|:---|:---|:---|:---|
| Objetivo → Requisito | OE / OT / OP | RF-E / RF-T / RF-O | Columna "Fuente" en cada tabla de la Sección 4. |
| Requisito → Caso de uso | RF | CU (catálogo agrupado por departamento) | Trazabilidad directa citada en cada RF; recuento total pendiente de verificación formal (hallazgo I4, en tratamiento con el propietario del documento fuente). |
| Requisito → Modelo de datos | RF | Esquema/tabla (Sección 7) | Nota de modelo de datos por caso de uso. |
| Requisito no funcional → Prueba | RNF-S01–S05 | PN-01 a PN-15 (Sección 8.2) | Cobertura declarada como puerta de release. |
| Excepción intencional | RF-T06, RF-T09 | Sin CU ni tabla | Procesos de ingeniería (CI/CD, gestión de ADR), documentados como excepción deliberada, no como deuda de especificación. |

---

# 11. Restricciones generales, supuestos y riesgos abiertos

- Toda decisión que se aparte de un requisito de este SRS requiere un ADR formal antes de su implementación.
- **Riesgo abierto — continuidad operacional (RNF-R01):** no puede declararse satisfecho hasta que la prueba de restauración semanal lo demuestre de forma sostenida; ningún artefacto de diseño puede asumir RTO/RPO cumplidos por defecto.
- **Riesgo abierto — aislamiento de tenant operacional (Sección 9.4):** riesgo residual aceptado, no eliminado; acotado por cobertura del 100 % de endpoints en la suite de pruebas cruzadas.
- **Debilidad organizacional declarada (equivalente a D7 del análisis FODA de la fuente):** la ausencia de RLS, PITR y triggers nativos en el motor operacional traslada responsabilidades críticas de integridad a la capa de aplicación, exigiendo disciplina de ingeniería sostenida (capa de repositorio, análisis estático, suite cruzada) como sustituto funcional permanente, no como medida transitoria.
- Las capacidades listadas en el Apéndice A no forman parte del alcance normativo comprometido de esta versión hasta su confirmación.

---

# 12. Enlace hacia el diseño (IEEE 1016)

Este SRS constituye la entrada formal para la elaboración de la(s) Descripción(es) de Diseño de Software (SDD) de cada módulo, conforme a IEEE 1016. **Todo SDD derivado de la SRS v1.0 sobre PostgreSQL/RLS queda invalidado** y debe re-derivarse desde esta versión, incorporando obligatoriamente: la capa de repositorio como componente arquitectónico de primera clase (Sección 6.1, 9.3), la máquina de estados del pipeline medallion (Sección 7.3.3), y la segregación estructural entre `ah_tactico` y `ah_estrategico` (Sección 7.4). Ningún elemento de diseño podrá introducirse sin trazabilidad explícita a un identificador RF/RNF confirmado de este documento.

---

# Apéndice A. Capacidades pendientes de confirmación normativa

Conforme a la resolución interina AEROHUB-ADR-INTERNO-001 (hallazgo I3), las siguientes capacidades están declaradas en la hoja de ruta del documento fuente pero carecen de confirmación de esquema y numeración definitiva al cierre de esta versión. No se descartan como alcance de negocio; se excluyen del catálogo normativo de las Secciones 4 y 7 hasta su cierre formal con el propietario del producto.

| Identificador provisional | Capacidad | Esquema referenciado (sin confirmar) | Objetivo de origen |
|:---|:---|:---|:---|
| RF-O19-bis | Captura automática de encuestas NPS/CSAT de operadores externos | `support` (extensión) | OT11 |
| RF-O20 | Verificación y auditoría de la región de residencia de datos declarada por tenant | `tenants.residencia_auditoria` | OT5 |
| RF-O21 | Políticas de retención y archivado automatizado sobre tablas de alto volumen | Extensión de `compliance`/`ops` | Visión 2028 |
| RF-O22 | Validación de rol asignado contra catálogo vigente antes de aceptar la asignación | Extensión de `tenants` | OT6 |
| RF-T13 | Metadatos de negocio de modelos ML consultables sin acceso a MLflow | `ml` (esquema no confirmado en el modelo de datos vigente) | OT8 |
| RF-T14 | Costo cloud por tenant con vista de margen bruto | `finops` (esquema no confirmado en el modelo de datos vigente) | OT14 |

**Condición de incorporación a una futura SRS v2.1:** cada fila de esta tabla se promueve al catálogo normativo únicamente tras confirmación explícita del propietario del documento fuente sobre su numeración definitiva y la existencia del esquema referenciado en el modelo de datos vigente (Sección 7).

---

**Fin del documento — AEROHUB-SRS-001 v2.0**
