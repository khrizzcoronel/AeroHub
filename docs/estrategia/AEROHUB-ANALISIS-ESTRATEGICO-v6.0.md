**AeroHub S.A.** — Análisis Documental Estratégico del Sistema Aeroportuario · Versión 6.0

**Nota de versión (5.1 → 6.0):** Esta versión mayor incorpora un cambio de plataforma de datos
que supersede tres decisiones fundacionales. La base operacional migra de PostgreSQL a
**MonetDB** (ADR-013) y la capa analítica se consolida en **ClickHouse**, segmentada en dos
bases —`ah_tactico` y `ah_estrategico`— alineadas al nivel de objetivo que sirven (ADR-012,
ADR-016). El pipeline ETL orquestado por Airflow adopta una **arquitectura medallion**
(bronce/plata/oro) con estados de ejecución desacoplados de las capas y gobierno en
`etl_control` (ADR-015). Al carecer MonetDB de Row-Level Security, el aislamiento por tenant
en la capa operacional **se traslada a la capa de aplicación** con cuatro controles
compensatorios verificables (ADR-014); la capa analítica, en cambio, conserva enforcement
estructural mediante políticas de fila de ClickHouse. El modelo de datos operacional se
rediseña por completo alcanzando **BCNF** en todas las tablas transaccionales y 4NF en las
entidades con hechos multivaluados, corrigiendo violaciones de 1NF, 2NF y 3NF presentes en
v5.1 (Sección 7.2.0). Se incorporan los lineamientos de patrón de lectura Z para tableros
estratégicos y F para tácticos (RNF-U01, Sección 8.3). Superseden: ADR-001, ADR-003 y ADR-005.

**Riesgo abierto declarado:** MonetDB no ofrece PITR ni replicación streaming equivalentes a
los de PostgreSQL. El cumplimiento de RNF-R01 (RTO < 15 min, RPO <= 5 min) depende de la
estrategia de continuidad a diseñar en la Acción 1b y no puede darse por satisfecho hasta que
la prueba de restauración lo demuestre.

---

# 1. Desarrollo y Organización Empresarial

## 1.1 Nivel Estratégico

Define el rumbo de la organización a largo plazo. La alta dirección (CEO, CTO) traza la misión, visión, alianzas estratégicas y objetivos globales de la plataforma SaaS de AeroHub. Se materializa en 6 Objetivos Estratégicos (OE1-OE6). Las decisiones en este nivel determinan el posicionamiento competitivo de AeroHub como la plataforma integral líder para la gestión operativa y comercial de aeropuertos en Latinoamérica (LatAm).

## 1.2 Nivel Táctico

Traduce la estrategia en planes concretos por área a mediano plazo. Los líderes de departamento (Dirección de Crecimiento Comercial, CTO, Dirección de Operaciones Cloud, Dirección de Datos e IA) definen campañas, presupuestos, configuración de infraestructura y metodologías de implementación. Se concreta en 13 Objetivos Tácticos (OT1-OT9, OT10-OT11 renumerados y OT13-OT14 incorporados en v5.1; ver nota de trazabilidad en la Sección 3.2).

## 1.3 Nivel Operativo

Ejecución de tareas diarias y semanales a corto plazo. Ingenieros, analistas de operaciones aeroportuarias y especialistas de soporte sostienen la operación: pipelines de datos operativos de vuelo, optimización de recursos en rampa, monitoreo de infraestructura del aeropuerto, atención de tickets y documentación. Se especifica en 16 Objetivos Operativos (OP1-OP16, incluyendo el desdoblamiento departamental OP2a/OP2b introducido en v5.1).

La estructura organizacional se articula en 6 Departamentos (Sección 4.1), que actúan como propietarios (owners) de los módulos del sistema, de los esquemas de base de datos y de los roles de acceso. Este eje departamental gobierna la integridad y la segregación de funciones en todo el documento.

---

# 2. Estrategia de AeroHub S.A.

**Actividad:** Plataforma SaaS B2B todo-en-uno de operaciones aeroportuarias que integra la Base de Datos Operacional del Aeropuerto (AODB), el Sistema de Información de Vuelos (FIDS), la gestión de terminales y puertas de embarque, la coordinación de operaciones en rampa (turnaround), el cobro de tasas aeroportuarias, la analítica de tráfico aéreo y modelos de Aprendizaje Automático (ML) explicables para la predicción de demoras de salida y llegada.

## 2.1 Misión

Dotar a los aeropuertos de Latinoamérica de una plataforma tecnológica unificada, ágil y de alta disponibilidad, que transforme sus registros operativos en decisiones inteligentes en tiempo real, optimizando el uso de su infraestructura física, agilizando el flujo de aeronaves y pasajeros, y elevando la rentabilidad general de la concesión aeroportuaria.

## 2.2 Visión

Consolidarnos para el año 2028 como la solución de software aeroportuario líder y de más rápido crecimiento en el mercado andino y de Centroamérica, gestionando la operación diaria de al menos 40 terminales aéreas comerciales con excelencia técnica, altos estándares de seguridad física y digital, y optimización de costos.

## 2.3 Objetivo Estratégico General

Desarrollar y comercializar una plataforma SaaS integrada para la gestión operativa y comercial de aeropuertos comerciales medianos y grandes en LatAm, mediante una arquitectura multitenant segura con aislamiento por tenant y por esquema departamental, modelos predictivos explicables de puntualidad y demoras, y una estrategia comercial digital-inbound y de alianzas con concesionarios públicos y privados, garantizando un crecimiento financiero sostenido y el estricto cumplimiento de las normas de la Organización de Aviación Civil Internacional (OACI) y las Direcciones Generales de Aviación Civil (DGAC) locales.

## 2.4 Balanced Scorecard por Perspectiva

### 2.4.1 Perspectiva Financiera

| Objetivo | KPI | Fórmula | Meta | Iniciativas | Departamento Responsable |
|:---|:---|:---|:---|:---|:---|
| Incrementar ARR | ARR (Ingresos Recurrentes Anuales) | Suma de contratos aeroportuarios activos x 12 | +30-40% anual en LatAm | Demostraciones personalizadas de ROI, planes modulares escalonados | Dirección General (CEO) |
| Optimizar CAC | CAC (Costo de Adquisición) | (Gasto marketing + ventas) / nuevos aeropuertos | < USD 15,000 por aeropuerto | Marketing de contenidos sobre eficiencia aeroportuaria, alianzas con integradores | Crecimiento Comercial |
| Mejorar LTV/CAC | Ratio LTV/CAC | Valor de Vida del Cliente / CAC | > 4x | Up-selling de módulos adicionales (ML Predictivo, FIDS avanzado) | Dirección General / Plataforma |
| Margen Bruto | Margen Bruto | (ARR - Costo Infraestructura Cloud) / ARR x 100 | > 75% | Optimización de cómputo y egress en la infraestructura PaaS, right-sizing de servicios | Plataforma y Seguridad (CTO) |
| Expansión de Ingresos | NRR (Retención de Ingresos Netos) | (ARR inicial + Expansión - Churn) / ARR inicial x 100 | > 108% | Cobros variables basados en el volumen de pasajeros procesados (Pax) | Crecimiento Comercial |

### 2.4.2 Perspectiva del Cliente

| Objetivo | KPI | Fórmula | Meta | Iniciativas | Departamento Responsable |
|:---|:---|:---|:---|:---|:---|
| Satisfacción de Operadores | NPS | % Promotores - % Detractores | > 45 | Soporte técnico especializado y canales dedicados para Directores de Operaciones | Crecimiento Comercial |
| Retención de Aeropuertos | Churn Anual de Contratos | Aeropuertos cancelados / total aeropuertos x 100 | < 5% anual (GRR > 95%) | Onboarding en sitio, auditoría de satisfacción trimestral, contratos multianuales | Dirección General |
| Acelerar Adopción | TTFV (Tiempo hasta Valor) | Tiempo desde firma de contrato hasta primera operación | < 30 días | Plantillas de migración AODB automatizadas, carga masiva de itinerarios | Soporte e Implementación |
| Calidad del Servicio | CSAT | Encuestas de tickets resueltos | > 90% | SLAs de soporte estrictos (primera respuesta < 2h para fallos de FIDS) | Soporte e Implementación |

### 2.4.3 Perspectiva de Procesos Internos

| Objetivo | KPI | Fórmula | Meta | Iniciativas | Departamento Responsable |
|:---|:---|:---|:---|:---|:---|
| Garantizar Disponibilidad | Uptime Global | (Tiempo total - caída de servicios críticos) / total x 100 | >= 99.9% (MVP), 99.95% (Scale) | Replicación de almacenamiento y respaldo lógico programado (RNF-R01, Acción 1b), balanceo de carga para AODB y FIDS | Operaciones Cloud |
| Controlar Presupuesto de Error | Error Budget Consumido | Minutos caídos reales / minutos permitidos mensuales | <= 80% | Monitoreo en tiempo real del API Gateway, congelar despliegues si se excede | Operaciones Cloud |
| Sincronización de Vuelos | Latencia de Actualización | Tiempo de refresco AODB -> Paneles FIDS | Interna < 1 s; SLA contractual < 3 s | WebSockets eficientes sobre el gateway FastAPI | Datos e IA / Operaciones Cloud |
| Continuidad Operativa | RTO / RPO / MTTR | RTO: tiempo de restauración del servicio; RPO: pérdida máxima de datos; MTTR: promedio de resolución Sev1/Sev2 | RTO < 15 min; RPO <= 5 min; MTTR < 30 min | Réplicas con failover automatizado, backups PITR, runbooks probados | Operaciones Cloud |

### 2.4.4 Perspectiva de Aprendizaje y Crecimiento

| Objetivo | KPI | Fórmula | Meta | Iniciativas | Departamento Responsable |
|:---|:---|:---|:---|:---|:---|
| Clima Laboral | eNPS | % Promotores - % Detractores (encuesta interna) | > 40 | Trabajo remoto flexible, capacitaciones en industria aeronáutica y MLOps | Dirección General / Talento |
| Rápida Productividad | Time-to-Productivity | Días para que un dev nuevo realice su primer deploy | < 5 días hábiles | Entornos locales dockerizados, sandbox de pruebas automatizado | Plataforma y Seguridad |
| Retención de Talento Clave | Tasa de Retención Anual | Empleados activos / total al inicio x 100 | > 85% | Planes de carrera estructurados, compensación competitiva | Dirección General / Talento |
| Innovación en IA Aeroportuaria | Modelos ML en Producción | Modelos entrenados, validados y monitoreados en producción | >= 2 modelos activos | Alianzas académicas, pipeline MLOps con registro y monitoreo de drift | Datos e IA |

---

# 3. Objetivos Estratégicos, Tácticos y Operativos

## 3.1 Objetivos Estratégicos (6)

1. **OE1 — Expansión y Dominio del Mercado Aeroportuario Regional:** Adquirir y activar la plataforma en al menos 15 aeropuertos medianos/grandes en Ecuador, Perú y Colombia mediante ventas B2B consultivas y demostración del ROI operativo.
2. **OE2 — Conectividad Total mediante APIs Estandarizadas:** Integrar la plataforma AeroHub de manera segura con los sistemas de aerolíneas, proveedores de rampa y entes de control mediante endpoints API REST de alto rendimiento documentados bajo OpenAPI 3.1.
3. **OE3 — Resiliencia Operativa y Cumplimiento Normativo:** Garantizar un SLA de Uptime de 99.9% en fase MVP y 99.95% en fase Scale para operaciones críticas de vuelo (AODB/FIDS), cumpliendo con los estándares de seguridad digital OACI y los requisitos de auditoría de las DGAC.
4. **OE4 — Optimización Inteligente basada en Datos:** Proporcionar visualización analítica avanzada, indicadores de puntualidad por aerolínea y ruta, y predicción explicable de demoras de salida y llegada mediante modelos de Aprendizaje Automático, para apoyar la planificación operativa del aeropuerto.
5. **OE5 — Cultura de Alto Rendimiento y Retención de Talento Tecnológico:** Mantener un equipo cohesionado y distribuido geográficamente con baja rotación laboral y un tiempo de onboarding ágil.
6. **OE6 — Éxito del Cliente Aeroportuario y Adopción Acelerada:** Lograr que la puesta en marcha de la plataforma en un nuevo aeropuerto tome menos de 30 días. Durante la fase MVP, la satisfacción se mide mediante proxy operativo (cumplimiento del SLA de tickets Sev1/Sev2, RF-O08); la meta NPS > 45 a nivel de directorio se vuelve exigible y auditable a partir de la fase Growth, una vez desplegado el mecanismo de captura automatizada (Acción 28).

## 3.2 Objetivos Tácticos (13)

1. **OT1:** Automatizar el aprovisionamiento de entornos de pruebas (Sandbox) para aeropuertos.
2. **OT2:** Diseñar el módulo de tasación y facturación por uso de infraestructura (Pax/Slots).
3. **OT3:** Publicar y certificar las APIs del AODB bajo la especificación OpenAPI 3.1.
4. **OT4:** Lanzar el portal FIDS configurable por WebSockets para terminales físicas.
5. **OT5:** Evolucionar la plataforma hacia infraestructura declarativa (IaC) y despliegue multi-región con residencia de datos por país, conforme a la secuenciación temporal definida en ADR-004 y el Plan de Acción (Sección 13, Acciones 29-30).
6. **OT6:** Implementar seguridad perimetral estricta, gestión centralizada de identidades y auditorías automáticas de acceso.
7. **OT7:** Establecer pipelines de ingesta de registros operativos de vuelo con contratos de datos formales (validación automática de esquema, dominios y completitud).
8. **OT8:** Implementar el tracking y monitoreo de modelos ML (registro de versiones y detección de drift en las predicciones de demora).
9. **OT9:** Definir y estandarizar la documentación de decisiones arquitectónicas (ADRs).
10. **OT10:** Desarrollar plantillas de migración de datos para agilizar el onboarding de tenants. *(renumerado desde OT11 v5.0)*
11. **OT11:** Ejecutar trimestralmente encuestas de satisfacción del usuario (NPS operativo). *(renumerado desde OT12 v5.0)*
12. **OT13:** Ejecutar el plan de expansión comercial B2B consultiva por país (Ecuador, Perú, Colombia), con métricas de pipeline por etapa y desarrollo de alianzas con integradores regionales que reduzcan el CAC. *(nuevo en v5.1, cierra el eslabón OE1 → OT → RF-E01 → CU-T01)*
13. **OT14:** Establecer el programa de gestión continua de costos de infraestructura (FinOps) y sostener la recopilación de evidencias para la certificación SOC 2 Tipo II. *(nuevo en v5.1, deriva de OE3 y del KPI de Margen Bruto)*

> **Nota de trazabilidad:** el objetivo táctico "Implementar programas de capacitación y
> evaluaciones de desempeño semestrales" (OT10 en v5.0) se reubicó al Anexo A.4, por
> corresponder a un proceso organizacional interno (ISO/IEC 12207) sin RF ni CU de producto
> derivado, siguiendo el mismo criterio aplicado a la Gestión de Sprints de Desarrollo.

## 3.3 Objetivos Operativos (16)

1. **OP1:** Supervisar el aprovisionamiento automatizado de nuevos tenants y la asignación de sus políticas de aislamiento en la base de datos.
2. **OP2a:** Atender y solucionar incidencias prioritarias de la AODB (SLA de respuesta < 2h). **[D1]** *(desdoblado desde OP2 v5.0)*
3. **OP2b:** Atender y solucionar incidencias de turnaround en rampa detectadas por desviación del estándar de tarea (SLA de respuesta < 4h). **[D2]** *(desdoblado desde OP2 v5.0)*
4. **OP4:** Calcular y reportar mensualmente la facturación a los aeropuertos según pasajeros procesados y slots operados. *(renumerado desde OP3 v5.0)*
5. **OP5:** Mantener actualizados los manuales de integración de la API para sistemas externos de aerolíneas. *(renumerado desde OP4 v5.0)*
6. **OP6:** Monitorear en Grafana la latencia del canal de WebSockets de las pantallas FIDS. *(renumerado desde OP5 v5.0)*
7. **OP7:** Ejecutar pruebas semanales automatizadas de restauración de la base operacional (verificación de RTO/RPO). *(renumerado desde OP6 v5.0)*
8. **OP8:** Realizar escaneos automáticos de vulnerabilidades en el código fuente (SAST) y dependencias en cada despliegue. *(renumerado desde OP7 v5.0)*
9. **OP9:** Analizar diariamente el consumo de Error Budget y congelar despliegues preventivamente. *(renumerado desde OP8 v5.0)*
10. **OP10:** Verificar y corregir el dimensionamiento de los servicios PaaS para optimizar costos cloud. *(renumerado desde OP9 v5.0; fuente táctica reasignada a OT14)*
11. **OP11:** Monitorear la ejecución y calidad de las DAGs de ingesta y transformación del pipeline analítico (Airflow). *(renumerado desde OP10 v5.0)*
12. **OP12:** Validar la consistencia de los registros de vuelos diarios contra los contratos de datos definidos. *(renumerado desde OP11 v5.0)*
13. **OP13:** Garantizar que los tableros de BI operativo de las terminales se refresquen conforme a la ventana acordada (5 minutos). *(renumerado desde OP12 v5.0)*
14. **OP14:** Reentrenar quincenalmente el modelo ML de predicción de demoras de salida y llegada, con validación temporal previa a la promoción. *(renumerado desde OP13 v5.0)*
15. **OP15:** Documentar y publicar el Changelog semanal en el portal de clientes del aeropuerto. *(renumerado desde OP14 v5.0)*
16. **OP16:** Redactar y archivar los post-mortems de incidentes de gravedad (Sev1/Sev2) en menos de 72h. *(renumerado desde OP15 v5.0)*

> **Nota de trazabilidad:** el objetivo operativo "Atender y solucionar incidencias prioritarias
> de la AODB" (OP2 en v5.0) mezclaba dos dominios departamentales distintos (D1-AODB y
> D2-Rampa) bajo un único enunciado, violando el eje de segregación departamental declarado
> en la Sección 1.3. Se desdobla en OP2a (D1) y OP2b (D2), cada uno con su propio esquema de
> propiedad (`ops` y `rampa` respectivamente, Sección 7.2).

---

## 3.4 Matriz de Trazabilidad Estratégica (OE × OT × OP)

Notación: "⊂" indica derivación directa. Todo OT y todo OP debe poseer al menos un OE de
origen; en caso contrario, migra al Anexo A como proceso organizacional interno, conforme al
criterio aplicado a la Gestión de Sprints de Desarrollo y a OT10 (v5.0). Esta matriz constituye
el punto de entrada obligatorio de la cadena de trazabilidad exigida en la Sección 11.6 y debe
actualizarse antes de que cualquier objetivo nuevo genere requisitos funcionales derivados.

| OE | OT derivados | OP derivados | RF Fuente principal |
|:---|:---|:---|:---|
| OE1 — Expansión de Mercado | OT2, OT13 | OP1, OP4 | RF-E01, RF-E02, RF-O01, RF-O15, RF-O18 |
| OE2 — Conectividad APIs | OT3, OT4 | OP5, OP6 | RF-T02, RF-T03, RF-O04, RF-O07 |
| OE3 — Resiliencia y Cumplimiento | OT5, OT6, OT14 | OP7, OP8, OP9, OP10 | RF-E03, RF-E04, RF-O09, RF-O10, RF-O12, RF-T11 |
| OE4 — Optimización con Datos (ML) | OT7, OT8 | OP2a, OP11, OP12, OP14 | RF-O02, RF-O03, RF-O05, RF-O06, RF-O17, RF-O19, RF-T12 |
| OE5 — Cultura y Talento | OT9 | *(ver Anexo A.4 y esquema `people`, Sección 7.2.7)* | RF-E05, RF-E06 |
| OE6 — Éxito del Cliente | OT1, OT10, OT11 | OP2b, OP15, OP16 | RF-O08, RF-O11, RF-O13, RF-O14, RF-T01 |

**Nota v6.0:** todos los OE se sirven de la base analítica `ah_estrategico` y todos los OT de
`ah_tactico`, conforme a la regla de la Sección 3.5 (ADR-016). Los OP se sirven de la base
operacional MonetDB. RF-O19 (control de ejecuciones ETL) y RF-T12 (promoción entre capas
medallion) se incorporan bajo OE4/OT7 (ADR-015).

**Regla de completitud:** ningún OT u OP puede carecer de columna OE de origen en esta tabla.
Toda incorporación futura de objetivos debe actualizar esta matriz antes de generar RF
derivados, conforme al control de cambios registrado en ADR (Sección 9).

## 3.5 Alineación entre Nivel de Objetivo y Capa de Datos (ADR-016)

Regla de servicio de datos, de aplicación obligatoria en el diseño de todo caso de uso nuevo:

| Nivel de objetivo | Base de datos de servicio | Motor | Justificación |
|:---|:---|:---|:---|
| Estratégico (OE1-OE6) | `ah_estrategico` | ClickHouse | Horizonte trimestral/anual; consultas agregadas; no requiere dato transaccional vivo. |
| Táctico (OT1-OT14) | `ah_tactico` | ClickHouse | Horizonte mensual/trimestral; análisis comparativo por vuelo, ruta y aerolínea; features de ML. |
| Operativo (OP1-OP16) | Esquemas departamentales | MonetDB | Requiere estado vivo, latencia inferior a 1 s y escritura transaccional. |

**Direccionalidad:** la regla prohíbe que un consumidor estratégico o táctico lea de la base
operacional, pero no lo inverso: los procesos operativos escriben en MonetDB como fuente de
todo el pipeline analítico.

**Excepción documentada:** OP1 (aprovisionamiento), OP2a y OP2b (atención de incidencias) y
OP4 (facturación mensual) operan sobre dato vivo y no pueden servirse desde la capa analítica
bajo ninguna circunstancia, por su naturaleza transaccional.

**Derivación unidireccional:** `ah_estrategico` se construye exclusivamente a partir de
`ah_tactico` (Sección 7.3.1). Ninguna cifra del tablero estratégico puede publicarse sin
reconciliar contra el detalle táctico con tolerancia cero.


---

# 4. Departamentos, Actores y Modelo de Control de Acceso (RBAC)

La organización de actores, módulos, esquemas de base de datos y permisos se rige por un eje departamental único. Cada departamento es propietario (owner) de sus módulos, de su esquema en la base operacional y de los roles de sistema que operan sobre él. Este diseño implementa segregación de funciones y mínimo privilegio (ISO/IEC 27002, controles 5.15, 8.2 y 8.3).

## 4.1 Catálogo de Departamentos

| ID | Departamento | Responsable | Ámbito de Propiedad |
|:---|:---|:---|:---|
| **D1** | Dirección de Operaciones Aeroportuarias | Dirección de Operaciones Cloud (producto) | Módulos AODB, FIDS, Terminal & Gate Manager. Esquema `ops`. |
| **D2** | Ground Operations (Rampa) | Dirección de Datos e IA + Implementación | Módulo Ground Operations. Esquema `rampa`. |
| **D3** | Crecimiento Comercial y Finanzas | CEO / Dirección de Crecimiento Comercial | Módulos Revenue & Billing, Passenger Experience. Esquema `billing`. |
| **D4** | Datos e Inteligencia Artificial | Dirección de Datos e IA | Módulo ETL & Analytics, plataforma ML, DW analítico (ClickHouse/MonetDB). |
| **D5** | Plataforma y Seguridad | CTO | Módulos Observability y Compliance & Safety Hub. Esquemas `tenants` y `compliance`. Hosting técnico (no funcional) de los esquemas `people` y `analytics_bsc` — v5.1. Infraestructura, CI/CD, gestión de secretos. |
| **D6** | Soporte e Implementación (DevRel) | Especialista de Implementación / DevRel | Onboarding de tenants, tickets, base de conocimientos. Esquema `support`. |

## 4.2 Actores por Departamento

### 4.2.1 Actores Internos (AeroHub)

| Departamento | Cargo Organizacional | Rol de Sistema (RBAC) | Descripción |
|:---|:---|:---|:---|
| Dirección General | CEO / Founder | `role_business_viewer` | Define visión comercial, alianzas y metas del BSC. Solo lectura de indicadores agregados. |
| Dirección General | Director Financiero | `role_business_viewer` | Análisis de ingresos, ARR y márgenes. Solo lectura financiera agregada. |
| Dirección General | Director de Talento y Cultura | `role_people_viewer` | Gestión de eNPS, retención y contrataciones. Acceso limitado a módulos de personal internos. |
| D5 — Plataforma y Seguridad | CTO | `role_platform_admin` | Gestión global de tenants, configuración de plataforma, acceso de emergencia (break-glass) auditado. |
| D5 — Plataforma y Seguridad | SRE / Director de Operaciones Cloud | `role_sre` | Infraestructura, observabilidad, secretos y despliegues. Sin acceso a datos de negocio de los tenants. |
| D4 — Datos e IA | Director de Datos e IA / Data Engineer | `role_data_engineer` | DAGs de Airflow, staging ClickHouse, DW MonetDB, contratos de datos. Lectura de datos operativos vía rol técnico ELT. |
| D4 — Datos e IA | ML Engineer | `role_ml_engineer` | Registro de modelos, features y reentrenamiento. Sin escritura en la base operacional. |
| D6 — Soporte e Implementación | Especialista de Implementación | `role_implementation` | Aprovisionamiento y configuración inicial por tenant, plantillas FIDS. Acceso temporal por tenant con caducidad automática. |
| D6 — Soporte e Implementación | Especialista DevRel | `role_support` | Tickets, base de conocimientos, changelog. Lectura limitada de configuración del tenant; nunca datos financieros. |
| D3 — Crecimiento Comercial | Director de Crecimiento Comercial | `role_business_viewer` | Marketing inbound, ventas enterprise y retención. Solo lectura de métricas comerciales. |

### 4.2.2 Actores Externos (por Tenant)

Todo actor externo opera bajo doble aislamiento: Row-Level Security por `tenant_id` (eje tenant) y privilegios por esquema (eje departamental). El alcance indicado es siempre "su propio tenant".

| Departamento Funcional | Actor | Rol de Sistema (RBAC) | Descripción y Alcance |
|:---|:---|:---|:---|
| D1 — Operaciones | Administrador del Aeropuerto (Tenant Admin) | `role_tenant_admin` | Director de TI/Operaciones del aeropuerto contratante. CRUD de usuarios locales, API Keys, licencias y configuración FIDS de su tenant. |
| D1 — Operaciones | Controlador de Operaciones | `role_operations_controller` | Registra vuelos, asigna puertas de embarque, gestiona desvíos e incidencias operativas. |
| D1 — Operaciones | Aerolínea Coordinadora | `role_airline_coordinator` | Actualiza itinerarios propios de su aerolínea (sub-ámbito por `airline_id`) y solicita slots o puertas. Acceso exclusivo vía API. |
| D2 — Rampa | Agente de Rampa (Ground Handling) | `role_ramp_agent` | Registra tiempos de tareas de turnaround del vuelo asignado; lectura de su plan de trabajo. Mínimo privilegio. |
| D3 — Comercial y Finanzas | Operador de Facturación del Tenant | `role_billing_officer` | Concilia facturas, gestiona disputas y consulta reportes Pax de su tenant. |
| D4 — Datos e IA | Analista del Tenant | `role_tenant_analyst` | Solo lectura de dashboards BI y exportes agregados de su tenant sobre las vistas analíticas de dominio. |
| D5 — Plataforma y Seguridad | Auditor de Regulación Aérea (DGAC / OACI) | `role_regulatory_auditor` | Solo lectura de reportes de cumplimiento y logs de auditoría. Acceso temporal, nominal y registrado. |

**Stakeholder pasivo (no actor de sistema):** el Pasajero Final consume las pantallas FIDS públicas y aplicaciones de terceros conectadas a la API del aeropuerto. No se autentica en la plataforma y por tanto no forma parte del catálogo RBAC; sus intereses se representan en los requisitos de usabilidad y disponibilidad del FIDS.

## 4.3 Matriz Rol x Esquema x Permiso

Convención: **U** = USAGE sobre el esquema, **S** = SELECT, **I** = INSERT, **Up** = UPDATE, **—** = sin acceso. No se otorga DELETE a ningún rol de negocio; las bajas son lógicas (soft delete auditado).

> **Cambio estructural en v6.0 (ADR-013/ADR-014):** MonetDB no implementa Row-Level Security.
> Los privilegios de esta matriz se otorgan a nivel de esquema en el motor, pero **el filtro
> por `tenant_id` ya no es aplicado por la base de datos**: lo inyecta obligatoriamente la
> capa de repositorio a partir del token validado. Toda celda que en v5.1 se leía como
> "acceso a las filas del propio tenant" debe leerse ahora como "acceso al esquema, con el
> filtro de tenant garantizado por la capa de aplicación y verificado por PN-01 a PN-03 y
> PN-15". La capa analítica sí conserva enforcement de motor mediante políticas de fila de
> ClickHouse.

### 4.3.1 Base Operacional (MonetDB)

| Rol | `ops` | `rampa` | `billing` | `compliance` | `tenants` | `support` | `people` | `etl_control` |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| `role_platform_admin` | U,S | U,S | U,S | U,S (escritura solo break-glass auditado) | U,S,I,Up | U,S | — | U,S |
| `role_sre` | — | — | — | U,S; U,S,I sobre `evidencia_soc2`; U,S,I,Up sobre `post_mortem` y `post_mortem_accion` | U,S | — | — | U,S |
| `role_data_engineer` | vía `role_elt_reader` | vía `role_elt_reader` | vía `role_elt_reader` | U,S | — | — | — | U,S,I,Up |
| `role_ml_engineer` | — | — | — | — | — | — | — | U,S |
| `role_implementation` | U,S,I,Up (temporal por tenant) | — | — | — | U,S,I (alta de tenant) | U,S,I | — | — |
| `role_support` | U,S (configuración) | — | — | — | U,S | U,S,I,Up | — | — |
| `role_business_viewer` | — | — | — | — | U,S,I,Up (`okr`, `okr_resultado_clave`) | — | — | — |
| `role_tenant_admin` | U,S,Up (configuración FIDS) | U,S | U,S (facturas propias) | — | U,S,I,Up (usuarios propios) | U,S,I | — | — |
| `role_operations_controller` | U,S,I,Up | U,S | — | — | — | U,S,I | — | — |
| `role_airline_coordinator` | U,S,I,Up (solo sus itinerarios) | — | U,S (sus cargos) | — | — | U,S,I | — | — |
| `role_ramp_agent` | U,S (vuelos asignados) | U,S,I,Up | — | — | — | — | — | — |
| `role_billing_officer` | — | — | U,S,Up (disputas) | — | — | U,S,I | — | — |
| `role_tenant_analyst` | — | — | — | — | — | U,S | — | — |
| `role_regulatory_auditor` | — | — | — | U,S | — | — | — | — |
| `role_people_viewer` | — | — | — | — | — | — | U,S | — |
| `role_elt_reader` (técnico, Airflow) | U,S | U,S | U,S | U,S | U,S | U,S | U,S | U,S,I,Up |

### 4.3.2 Capa Analítica (ClickHouse)

Aquí el aislamiento **sí** es estructural: las políticas de fila (`CREATE ROW POLICY`) filtran
por `tenant_id` a nivel de motor, conforme a la Sección 7.3.4.

| Rol | `ah_tactico` | `ah_estrategico` | Política de fila por tenant |
|:---|:---|:---|:---|
| `role_business_viewer` | — | S | No aplica (consume agregados multi-tenant autorizados) |
| `role_platform_admin` | S | S | No aplica (rol de plataforma) |
| `role_tenant_analyst` | S | — | **Sí**, restringida a su `tenant_id` |
| `role_data_engineer` | S, I, Up | — | No (requiere visión cruzada para diagnóstico; auditado y verificado por PN-13) |
| `role_ml_engineer` | S sobre hechos y features | — | No (entrenamiento requiere corpus cruzado; auditado) |
| `role_people_viewer` | — | S solo sobre `resumen_talento_trimestral` | No aplica (sin `tenant_id`, alcance interno) |
| `role_elt_writer` (técnico, Airflow) | S, I, Up | S, I, Up | No (identidad técnica de carga) |
| Resto de roles | — | — | — |

> **Segregación entre bases analíticas:** ningún rol posee escritura simultánea en ambas.
> `role_business_viewer` accede a `ah_estrategico` pero **no a `ah_tactico`**, evitando que el
> nivel estratégico consulte detalle transaccional que su nivel de decisión no requiere
> (mínimo privilegio, ISO/IEC 27002 8.2). Verificado por PN-13.

## 4.4 Principios Transversales de Acceso

- **Mínimo privilegio:** cada rol posee únicamente los permisos de la matriz 4.3; toda ampliación requiere aprobación del owner del departamento y registro en `compliance`.
- **Segregación de funciones:** quien despliega (SRE) no accede a datos financieros; quien factura no modifica datos operativos; el rol técnico ELT (`role_elt_reader`) es de solo lectura sobre la base operacional y es el único autorizado a escribir en staging analítico.
- **Doble eje de aislamiento (asimétrico desde v6.0):** en la base operacional, el eje de tenant se aplica en la capa de repositorio (ADR-014) y el eje departamental por privilegios de esquema en el motor; en la capa analítica, ambos ejes son estructurales (políticas de fila + privilegios por base). Todos se prueban de forma negativa (Sección 11.4).
- **Autenticación:** MFA obligatorio para todos los roles internos y para `role_tenant_admin`. Autenticación de API por claves con rotación automática y JWT de corta vida emitidos por el API Gateway.
- **Revisión de accesos:** recertificación trimestral de asignaciones rol-usuario por departamento (ISO/IEC 27002, 5.18).
- **Auditoría inmutable:** el esquema `compliance` es append-only salvo `post_mortem`/`post_mortem_accion` (excepción de ADR-009). Al carecer MonetDB de triggers equivalentes, la escritura del log de auditoría es responsabilidad de la capa de repositorio y su completitud se verifica con la misma regla de análisis estático que el filtro de tenant (ADR-014).
- **Sin SQL fuera de la capa de repositorio:** ningún componente distinto de la capa de acceso a datos puede emitir SQL hacia MonetDB. Es el control que sustituye al RLS perdido y su cumplimiento es puerta de release (PN-15).

---

# 5. Catálogo de Requisitos Funcionales

Tabla maestra de requisitos. Prioridad según MoSCoW (M = Must, S = Should, C = Could). Cada requisito traza a su fuente (objetivo) y define un criterio de aceptación verificable, base de las condiciones de prueba de la Sección 11 (ISO/IEC/IEEE 29119).

## 5.1 Requisitos de Nivel Estratégico

| ID | Descripción | Prioridad | Fuente | Criterio de Aceptación |
|:---|:---|:---|:---|:---|
| RF-E01 | El sistema presentará un tablero BSC con los KPIs de las cuatro perspectivas actualizado diariamente. | S | OE1, OT13 | KPIs visibles con fecha de corte <= 24h. |
| RF-E02 | El sistema consolidará ingresos por tasas, slots y Pax por tenant y período. | M | OE1, OT2 | Reporte mensual concilia al 100% con las facturas emitidas. |
| RF-E03 | El sistema expondrá el estado de disponibilidad (uptime) de los servicios críticos AODB/FIDS. | M | OE3 | Panel de uptime con granularidad mensual y consumo de error budget. |
| RF-E04 | El sistema generará reportes de conformidad normativa (DGAC/OACI) a partir del log de auditoría. | M | OE3 | Reporte exportable con evidencias trazables a eventos auditados. |
| RF-E05 | El sistema permitirá configurar metas y OKRs operativos por departamento. | C | OE5 | Metas versionadas con responsable y período. |
| RF-E06 | El sistema registrará y visualizará métricas de clima laboral (eNPS) internas. | C | OE5 | Encuesta trimestral con resultados agregados y anónimos. |

## 5.2 Requisitos de Nivel Táctico

| ID | Descripción | Prioridad | Fuente | Criterio de Aceptación |
|:---|:---|:---|:---|:---|
| RF-T01 | El sistema aprovisionará entornos sandbox por tenant con datos sintéticos. | S | OT1 | Sandbox operativo en < 10 minutos desde la solicitud. |
| RF-T02 | El sistema publicará la API del AODB conforme a OpenAPI 3.1 validada automáticamente. | M | OT3 | Especificación con 0 errores en el linter (Spectral) en CI. |
| RF-T03 | El sistema permitirá diseñar y publicar plantillas FIDS para pantallas físicas. | M | OT4 | Plantilla publicada se refleja en pantallas en < 1 s (interno). |
| RF-T04 | El sistema validará cada lote de ingesta contra contratos de datos formales. | M | OT7 | Lotes con violaciones quedan en cuarentena con reporte de causa. |
| RF-T05 | El sistema registrará versiones, métricas y drift de los modelos ML. | M | OT8 | Todo modelo en producción posee versión, dataset de entrenamiento y umbrales de drift. |
| RF-T06 | El pipeline CI/CD ejecutará análisis SAST, de dependencias y de contenedores en cada cambio. | M | OT6 | Ningún despliegue procede con hallazgos críticos abiertos. |
| RF-T07 | El sistema administrará el portal del desarrollador con SDKs y documentación interactiva. | S | OE2 | SDKs Python/TypeScript publicados y sincronizados con la API. |
| RF-T08 | El sistema reportará el costo cloud por servicio y tenant con alertas de desviación. | S | OT14 | Alerta emitida ante desviación > 20% del presupuesto mensual. |
| RF-T09 | El sistema documentará las decisiones arquitectónicas (ADRs) versionadas en el repositorio. | M | OT9 | Toda decisión estructural posee ADR aprobado antes de implementarse. |
| RF-T10 | El sistema soportará experimentación de precios por volumen Pax/slots. | C | OT2 | Variantes de tarifario aplicables por tenant sin despliegue de código. |
| RF-T12 | El sistema promoverá artefactos entre las capas medallion (bronce, plata, oro) únicamente si la validación de la transición resulta aprobada; los rechazados se derivan a cuarentena. | M | OT7 | Artefacto con contrato de datos inválido no promueve y queda en `/cuarentena` con informe de validación. |
| RF-T11 | El sistema recopilará automáticamente evidencias de controles técnicos (logs de acceso, cifrado, backups, rotación de credenciales) exportables para auditoría SOC 2 Tipo II. | S | OT14 | Evidencia exportable trazable a `compliance.log_auditoria` y `compliance.reporte_dgac`, generada sin intervención manual. |

> **Nota v5.1 (auditoría de trazabilidad):** RF-T01 queda instrumentalizado por CU-T13
> (Sección 6.1, D6). RF-T06 (SAST/CI-CD) y RF-T09 (documentación de ADRs) son deliberadamente
> procesos de ingeniería sin CU ni tabla asociados: se ejecutan en GitHub Actions y en el
> repositorio de código respectivamente, no en la base operacional, y se documentan como
> procesos organizacionales en el Anexo A (A.3, Gestión de Decisiones Arquitectónicas). No
> constituyen gaps de modelo, sino la ausencia intencional del mismo por no ser funcionalidad
> de producto.

## 5.3 Requisitos de Nivel Operativo

| ID | Descripción | Prioridad | Fuente | Criterio de Aceptación |
|:---|:---|:---|:---|:---|
| RF-O01 | El sistema aprovisionará nuevos tenants creando sus usuarios, políticas RLS y configuración base. | M | OP1 | Tenant operativo con aislamiento verificado en < 10 minutos. |
| RF-O02 | El sistema permitirá registrar vuelos y asignar puertas de embarque de forma manual y automática. | M | OE4, OP2a | Asignación sin conflictos de solapamiento; conflicto detectado se notifica. |
| RF-O03 | El sistema ingerirá diariamente los registros operativos de vuelos provistos por el aeropuerto y entes de itinerarios. | M | OT7, OP11 | Carga diaria completa sin pérdida de registros; discrepancias reportadas. |
| RF-O04 | El sistema expondrá el estado de vuelo en tiempo real vía API y WebSockets. | M | OE2, OP6 | Cambio de estado propagado a consumidores en < 1 s (interno). |
| RF-O05 | El sistema reentrenará el modelo de predicción de demoras con validación temporal previa a promoción. | M | OP14 | Modelo promovido solo si MAPE <= umbral en el holdout temporal. |
| RF-O06 | El sistema refrescará los tableros BI operativos conforme a la ventana definida. | S | OP13 | Refresco <= 5 minutos verificado por telemetría. |
| RF-O07 | El sistema monitoreará la telemetría de pantallas FIDS (latencia, conexión, versión de certificado). | M | OP6 | Pantalla sin señal genera alerta en < 60 s. |
| RF-O08 | El sistema gestionará tickets de soporte con SLAs por severidad. | M | OP2a, OP2b | Primera respuesta < 2h en incidencias de FIDS/AODB; < 4h en incidencias de rampa. |
| RF-O09 | El sistema ejecutará backups continuos (PITR) y pruebas de restauración automatizadas. | M | OP7 | Restauración semanal cumple RTO < 15 min y RPO <= 5 min. |
| RF-O10 | El sistema calculará el consumo de error budget y bloqueará despliegues al exceder el umbral. | S | OP9 | Despliegue bloqueado automáticamente al superar el 80% del budget. |
| RF-O11 | El sistema publicará el changelog del producto en el portal de clientes. | C | OP15 | Changelog semanal visible para todos los tenants. |
| RF-O12 | El sistema rotará credenciales, API Keys y certificados TLS de forma automática. | M | OT6 | Rotación sin interrupción del servicio; evento registrado en auditoría. |
| RF-O13 | El sistema soportará la elaboración de post-mortems con línea de tiempo automática de alertas. | S | OP16 | Post-mortem generado con eventos correlacionados del incidente. |
| RF-O14 | El sistema gestionará la base de conocimientos con búsqueda semántica. | C | OE6 | Artículo publicado indexado y recuperable en la búsqueda del portal. |
| RF-O15 | El sistema calculará mensualmente la facturación por Pax y slots a partir de los registros operados. | M | OP4 | Factura generada concilia con los movimientos del período sin diferencias. |
| RF-O16 | El sistema registrará incidencias de rampa por desviación del estándar de turnaround y notificará al agente responsable y al departamento D2. | S | OP2b | Incidencia generada en < 60 s tras superar el estándar; visible en `rampa.incidencia_rampa`. |
| RF-O17 | El sistema estimará y publicará tiempos de espera agregados por terminal a partir de datos operativos, sin capturar información nominal del pasajero. | C | OE4 | Estimación visible en el portal público con actualización <= 15 minutos; 0 campos de PII en el modelo de datos (RNF-S05). |
| RF-O18 | El sistema verificará en cada acceso a un módulo que el tenant posee licencia vigente y denegará el acceso sin licencia activa. | M | OP1 | Solicitud a módulo sin licencia retorna 403 en el 100% de los casos; evento registrado en auditoría. |
| RF-O19 | El sistema registrará el estado, los conteos de entrada/salida y el checksum de cada ejecución ETL por capa medallion, impidiendo el reprocesamiento concurrente del mismo artefacto. | M | OT7, OP11 | Toda ejecución trazable en `etl_control.etl_ejecucion`; intento de reproceso concurrente rechazado por unicidad `(run_id, capa)`. |

## 5.4 Requisitos No Funcionales Transversales (Seguridad e Integridad)

| ID | Descripción | Prioridad | Fuente | Criterio de Aceptación |
|:---|:---|:---|:---|:---|
| RNF-S01 | Aislamiento multi-tenant: ningún usuario de un tenant podrá leer ni modificar datos de otro tenant. | M | ISO 27002 8.3 | Prueba negativa de acceso cruzado retorna denegación en el 100% de los casos. |
| RNF-S02 | Aislamiento departamental: ningún rol podrá operar sobre esquemas fuera de su matriz de permisos (4.3). | M | ISO 27002 5.15 | Prueba negativa por rol/esquema retorna denegación conforme a la matriz. |
| RNF-S03 | Cifrado en tránsito TLS 1.2+ (objetivo 1.3) en todas las interfaces; cifrado en reposo en bases y staging. | M | ISO 27002 8.24 | Escaneo de configuración sin protocolos ni cifrados débiles; verificado como puerta de release en PN-10 (Sección 11.4, v5.1). |
| RNF-S04 | Log de auditoría inmutable (append-only) para modificaciones de itinerarios, accesos y facturación. Al carecer MonetDB de triggers equivalentes, su escritura es responsabilidad de la capa de repositorio, no del motor. | M | ISO 27002 8.15 | Intento de UPDATE/DELETE sobre auditoría es rechazado y alertado (PN-04); toda operación mutante produce su registro correspondiente, verificado por muestreo en la suite de integración. |
| RNF-S05 | Minimización de datos personales: el FIDS y los módulos operativos no almacenarán PII de pasajeros. La encuesta de eNPS no referencia al empleado individual (anonimidad estructural, Sección 7.2.8). | M | ISO 27701 | Revisión de modelo de datos sin campos de PII; verificación dinámica en PN-11. |
| RNF-U01 | Los tableros estratégicos adoptarán patrón de lectura en Z y los tácticos en F; los operativos, posición fija sin recorrido. El KPI de mayor prioridad ocupa el cuadrante superior izquierdo y todo KPI declara su tabla de origen. | S | ISO 25010 (usabilidad) | Revisión de diseño por tipo de tablero conforme a la Sección 8.3; cada KPI del tablero resuelve su origen vía `dim_kpi.fuente_tabla`. |
| RNF-R01 | Continuidad operacional: RTO < 15 min y RPO <= 5 min sobre la base operacional, sostenidos mediante respaldo lógico programado y replicación de almacenamiento, dado que MonetDB no ofrece PITR nativo equivalente. | M | ISO 27002 8.13 | Prueba de restauración semanal automatizada cumple ambos umbrales (RF-O09, Acción 1b). |

---

# 6. Catálogo de Casos de Uso

El sistema implementa 37 Casos de Uso distribuidos en los niveles estratégico, táctico y operativo, agrupados por el departamento propietario de su módulo. La gestión de sprints de desarrollo (antes CU-O15) se reubica como proceso organizacional interno en el Anexo A, por corresponder a procesos de gestión del ciclo de vida (ISO/IEC 12207) y no a funcionalidad del producto. En v5.1 se incorporan CU-O19 (M6 Passenger Experience), CU-T11 (evidencia SOC 2), CU-T13 (sandbox) y CU-O20 (validación de licencia), y se reclasifica CU-T05 de D2 a D4, conforme al análisis de consistencia Caso de Uso × Modelo de Datos y a la auditoría de trazabilidad OE-OT-OP-RF-CU completa.

## 6.1 Catálogo General por Departamento

### D1 — Dirección de Operaciones Aeroportuarias

| Código | Nombre | Nivel | Actor Principal (Rol RBAC) | RF Asociados |
|:---|:---|:---|:---|:---|
| CU-E03 | Evaluar Disponibilidad del Core Aeroportuario (AODB/FIDS) | Estratégico | `role_platform_admin` | RF-E03 |
| CU-T02 | Configurar y Publicar APIs del AODB | Táctico | `role_platform_admin` | RF-T02 |
| CU-T03 | Configurar Plantillas FIDS para Pantallas Físicas | Táctico | `role_implementation` | RF-T03 |
| CU-O01 | Registrar Vuelo y Asignar Puerta de Embarque Dinámicamente | Operativo | `role_operations_controller` / Sistema | RF-O02 |
| CU-O02 | Consultar Estado de Vuelo en Tiempo Real vía API | Operativo | `role_airline_coordinator` | RF-O04 |
| CU-O07 | Monitorear Telemetría de las Pantallas FIDS | Operativo | `role_sre` | RF-O07 |

### D2 — Ground Operations (Rampa)

| Código | Nombre | Nivel | Actor Principal (Rol RBAC) | RF Asociados |
|:---|:---|:---|:---|:---|
| CU-O16 | Registrar Tiempos de Tareas de Turnaround | Operativo | `role_ramp_agent` | RF-O02, RF-O03 |

> **Nota v5.1:** `CU-T05 — Evaluar y Versionar Modelos ML de Demoras` se reclasificó de D2 a D4
> (ver catálogo D4 más abajo), dado que su artefacto de datos (registro de modelos en MLflow,
> features en el DW) es propiedad exclusiva de Datos e IA; el esquema `rampa` no contiene
> tabla alguna relacionada con modelos ML.

### D3 — Crecimiento Comercial y Finanzas

| Código | Nombre | Nivel | Actor Principal (Rol RBAC) | RF Asociados |
|:---|:---|:---|:---|:---|
| CU-E01 | Consultar Tablero Balanced Scorecard | Estratégico | `role_business_viewer` | RF-E01 |
| CU-E02 | Analizar Ingresos por Tasas y Concesiones | Estratégico | `role_business_viewer` | RF-E02 |
| CU-T01 | Diseñar Campaña de Ventas B2B para Concesionarios | Táctico | `role_business_viewer` | RF-E01, OT13 |
| CU-T10 | Evaluar Estrategia de Precios por Volumen de Pasajeros | Táctico | `role_business_viewer` | RF-T10 |
| CU-O17 | Generar y Conciliar Facturación Mensual por Pax y Slots | Operativo | Sistema / `role_billing_officer` | RF-O15, RF-E02 |
| CU-O19 | Estimar y Publicar Tiempos de Espera Agregados por Terminal | Operativo | Sistema | RF-O17 |

### D4 — Datos e Inteligencia Artificial

| Código | Nombre | Nivel | Actor Principal (Rol RBAC) | RF Asociados |
|:---|:---|:---|:---|:---|
| CU-T04 | Supervisar Integración y Calidad del Pipeline ELT de Vuelos | Táctico | `role_data_engineer` | RF-T04 |
| CU-T05 | Evaluar y Versionar Modelos ML de Demoras | Táctico | `role_ml_engineer` | RF-T05 |
| CU-O03 | Ingerir Registros Operativos de Vuelos Diarios | Operativo | Sistema | RF-O03 |
| CU-O04 | Validar Contratos de Datos de Ingesta | Operativo | Sistema / `role_data_engineer` | RF-T04, RF-O03 |
| CU-O05 | Reentrenar Modelo Predictivo de Demoras (ML) | Operativo | Sistema / `role_ml_engineer` | RF-O05, RF-T05 |
| CU-O06 | Refrescar Tableros BI de Operación de la Terminal | Operativo | Sistema | RF-O06 |
| CU-T14 | Promover Datos entre Capas Bronce, Plata y Oro | Táctico | Sistema / `role_data_engineer` | RF-T12, RF-T04 |
| CU-O21 | Supervisar el Estado del Pipeline Medallion por Capa | Operativo | `role_data_engineer` | RF-O19 |

### D5 — Plataforma y Seguridad

| Código | Nombre | Nivel | Actor Principal (Rol RBAC) | RF Asociados |
|:---|:---|:---|:---|:---|
| CU-E04 | Auditar Cumplimiento de Normativa de Aviación (DGAC/OACI) | Estratégico | `role_regulatory_auditor` / `role_platform_admin` | RF-E04, RNF-S04 |
| CU-E05 | Configurar Metas y OKRs Operativos | Estratégico | `role_platform_admin` | RF-E05 |
| CU-T06 | Configurar Alertas de Seguridad de la Plataforma | Táctico | `role_sre` | RF-T06 |
| CU-T08 | Analizar y Optimizar Costos Cloud de la Infraestructura | Táctico | `role_platform_admin` / `role_sre` | RF-T08 |
| CU-T09 | Ejecutar Pruebas de Carga y Fallos Simulados en la AODB | Táctico | `role_sre` | RF-O09, RF-E03 |
| CU-T11 | Recopilar Evidencia Continua de Cumplimiento SOC 2 | Táctico | Sistema / `role_sre` | RF-T11 |
| CU-O09 | Ejecutar Copias de Seguridad de la Base Operacional | Operativo | Sistema / `role_sre` | RF-O09 |
| CU-O10 | Validar Presupuesto de Error y Suspender Despliegues | Operativo | Sistema | RF-O10 |
| CU-O12 | Rotar Credenciales y Certificados TLS de los FIDS | Operativo | Sistema / `role_sre` | RF-O12 |
| CU-O13 | Redactar Post-Mortem de Caída de Servicio | Operativo | `role_sre` | RF-O13 |
| CU-O18 | Aprovisionar Nuevo Tenant con Aislamiento Verificado | Operativo | `role_platform_admin` / `role_implementation` | RF-O01, RNF-S01 |
| CU-O20 | Validar Acceso por Licencia de Módulo Disponible | Operativo | Sistema | RF-O18 |

### D6 — Soporte e Implementación (DevRel)

| Código | Nombre | Nivel | Actor Principal (Rol RBAC) | RF Asociados |
|:---|:---|:---|:---|:---|
| CU-E06 | Analizar Clima Laboral y Retención en AeroHub | Estratégico | `role_people_viewer` | RF-E06 |
| CU-T07 | Administrar Portal del Desarrollador y SDKs | Táctico | `role_support` | RF-T07 |
| CU-T13 | Crear Entorno Sandbox de Prueba por Tenant | Táctico | `role_implementation` | RF-T01 |
| CU-O08 | Atender Tickets de Soporte del Concesionario | Operativo | `role_implementation` | RF-O08 |
| CU-O11 | Publicar Bitácora de Cambios (Changelog) | Operativo | `role_support` | RF-O11 |
| CU-O14 | Enriquecer Base de Conocimientos Operativa | Operativo | `role_support` | RF-O14 |

> **Nota v5.1 (resuelve hallazgo 3.7):** `CU-E06` carecía de esquema físico y `role_people_viewer`
> no poseía fila en la matriz RBAC 4.3. Se incorpora el esquema `people` (Sección 7.2.7),
> propiedad técnica de D5 por analogía con `tenants`, y se añade `role_people_viewer` a la
> matriz 4.3 con acceso exclusivo de solo lectura sobre dicho esquema.
>
> **Nota v5.1 (resuelve hallazgo 3.1 de la auditoría de trazabilidad):** `RF-T01` (sandbox de
> pruebas, prioridad Should) carecía de CU explícito pese a ser Must implícito del onboarding
> acelerado (OE6). Se incorpora `CU-T13`, trazado a OT1 (Sección 3.2), reutilizando
> `tenants.tenant` con el atributo `is_sandbox`.

## 6.2 Especificaciones Detalladas de Casos de Uso Modificados

Los casos de uso no listados en esta subsección conservan la especificación detallada de la versión 4.0, con la única sustitución de los nombres de actores por sus roles RBAC equivalentes (Sección 4.2).

### CU-O03: Ingerir Registros Operativos de Vuelos Diarios

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema (DAG de Airflow) |
| **Departamento** | D4 — Datos e IA |
| **Propósito** | Incorporar diariamente al pipeline analítico los registros operativos de vuelos (itinerarios, horarios reales, demoras y causas tipificadas) provistos por el aeropuerto y los entes de itinerarios. |
| **Precondición** | Contrato de datos vigente (esquema, dominios, completitud) registrado en la suite de validación. |
| **Flujo Principal** | 1. La DAG extrae el lote diario desde la fuente configurada del tenant.<br>2. El lote se carga en la capa Raw del staging (ClickHouse).<br>3. Se ejecuta la validación del contrato de datos (Great Expectations).<br>4. Los registros válidos se transforman (Python/Polars y SQL) a la capa Cleansed.<br>5. Se carga incrementalmente el resultado curado al DW (MonetDB). |
| **Flujos Alternativos** | 3a. Violación del contrato: el lote queda en cuarentena, se genera reporte de causa y alerta a `role_data_engineer` (RF-T04). |
| **Postcondición** | DW actualizado con el día operativo; métricas de calidad del lote registradas. |

### CU-O05: Reentrenar Modelo Predictivo de Demoras (ML)

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema (pipeline MLOps) / `role_ml_engineer` |
| **Departamento** | D4 — Datos e IA |
| **Propósito** | Reentrenar quincenalmente el modelo de predicción de demoras de salida y llegada por aeropuerto, aerolínea, ruta, franja horaria y causa tipificada, con explicabilidad SHAP. |
| **Precondición** | DW actualizado; conjunto de features versionado; umbrales de aceptación definidos (MAPE y drift). |
| **Flujo Principal** | 1. El pipeline construye el dataset de entrenamiento con partición temporal (entrenamiento sobre el período histórico inicial, holdout sobre los períodos finales) evitando fuga temporal.<br>2. Entrena el modelo (XGBoost) y calcula métricas sobre el holdout.<br>3. Si MAPE <= umbral, registra la versión candidata en el model registry (MLflow) con dataset, hiperparámetros y explicaciones SHAP globales.<br>4. `role_ml_engineer` aprueba la promoción; el modelo se publica para scoring.<br>5. El monitoreo de drift (Evidently) queda activo sobre las predicciones en producción. |
| **Flujos Alternativos** | 3a. MAPE > umbral: la versión se descarta, se conserva el modelo vigente y se alerta a `role_ml_engineer`. |
| **Postcondición** | Modelo vigente trazable (versión, datos, métricas) y monitoreado; predicciones disponibles para los tableros operativos. |

### CU-O16: Registrar Tiempos de Tareas de Turnaround

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | `role_ramp_agent` |
| **Departamento** | D2 — Ground Operations |
| **Propósito** | Registrar inicio y fin de cada tarea de turnaround (combustible, catering, limpieza, equipaje) del vuelo asignado, alimentando la detección de demoras operativas. |
| **Precondición** | Vuelo con puerta o posición asignada; agente autenticado con vuelo asignado. |
| **Flujo Principal** | 1. El agente selecciona el vuelo asignado en la interfaz móvil/web.<br>2. Marca inicio de la tarea; el sistema registra el timestamp y el usuario.<br>3. Marca fin de la tarea; el sistema calcula la duración y la compara con el estándar.<br>4. Desviaciones sobre el estándar generan una incidencia de rampa, notificada conforme a RF-O16. |
| **Postcondición** | Tiempos registrados en `rampa` y disponibles para el pipeline analítico; incidencias de rampa visibles en `rampa.incidencia_rampa` y trazables a OP2b. |
| **RF Asociados** | RF-O03, RF-O16 |

### CU-O17: Generar y Conciliar Facturación Mensual por Pax y Slots

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema (motor de facturación) / `role_billing_officer` |
| **Departamento** | D3 — Crecimiento Comercial y Finanzas |
| **Propósito** | Calcular los cargos aeronáuticos del período (slots operados, mangas, estacionamiento) y las tasas por pasajero, emitir la factura y soportar su conciliación por el tenant. |
| **Precondición** | Tarifario vigente por tenant; registros operativos del período cerrado. |
| **Flujo Principal** | 1. El motor consolida despegues, aterrizajes y usos de infraestructura del período desde `ops`.<br>2. Aplica el tarifario vigente y calcula la factura por aerolínea.<br>3. Emite la factura y notifica al tenant.<br>4. `role_billing_officer` revisa, concilia y registra disputas si corresponde. |
| **Flujos Alternativos** | 4a. Disputa registrada: la línea disputada queda en revisión con trazabilidad completa del cálculo. |
| **Postcondición** | Facturas emitidas y conciliadas; conciliación trazada en auditoría. |

### CU-O18: Aprovisionar Nuevo Tenant con Aislamiento Verificado

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | `role_platform_admin` / `role_implementation` |
| **Departamento** | D5 — Plataforma y Seguridad |
| **Propósito** | Dar de alta un aeropuerto tenant creando su configuración base, usuarios iniciales y políticas RLS, verificando el aislamiento antes de la entrega. |
| **Precondición** | Contrato firmado; plan de suscripción definido. |
| **Flujo Principal** | 1. Se registra el tenant en el esquema `tenants` con su plan y límites.<br>2. El sistema aplica las políticas RLS y los roles iniciales del tenant.<br>3. Se ejecuta la batería automática de pruebas negativas de aislamiento (RNF-S01/S02).<br>4. Con las pruebas en verde, se habilita el acceso y se entrega al equipo de implementación. |
| **Flujos Alternativos** | 3a. Fallo de aislamiento: el aprovisionamiento se revierte y se abre incidente de severidad alta. |
| **Postcondición** | Tenant operativo con aislamiento verificado y evidencia registrada en `compliance`. |

### CU-O13: Redactar Post-Mortem de Caída de Servicio *(especificación incorporada en v5.1)*

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | `role_sre` |
| **Departamento** | D5 — Plataforma y Seguridad |
| **Propósito** | Documentar de forma blameless la causa raíz, línea de tiempo y acciones de remediación de todo incidente Sev1/Sev2, dentro de las 72 horas posteriores a su resolución. |
| **Precondición** | Incidente resuelto y cerrado en el sistema de observabilidad (Grafana/PagerDuty). |
| **Flujo Principal** | 1. El sistema reconstruye automáticamente la línea de tiempo de alertas desde M8 Observability.<br>2. `role_sre` documenta el análisis de causa raíz (5 Porqués) y las acciones de remediación; el registro se crea en `compliance.post_mortem` con `estado='abierto'`.<br>3. Se publica un resumen no técnico en `support.articulo_kb` para transparencia con el tenant afectado, cuando corresponda.<br>4. A medida que se cierran los tickets de remediación, `role_sre` actualiza `acciones_remediacion` y `estado` hasta `estado='cerrado'`. |
| **Postcondición** | Post-mortem trazable con eventos correlacionados, tiempo de resolución y acciones de remediación abiertas como tickets; ciclo de vida completo auditado hasta el cierre. |
| **RF Asociados** | RF-O13 |
| **Nota de modelo de datos** | `compliance.post_mortem` es distinta de `compliance.incidente_seguridad` (reservada a incidentes de seguridad física/digital de naturaleza regulatoria). Es la única tabla del esquema `compliance` con UPDATE permitido, dado su ciclo de vida activo hasta el cierre de remediación (Sección 7.2.4). |

### CU-O19: Estimar y Publicar Tiempos de Espera Agregados por Terminal

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema |
| **Departamento** | D3 — Crecimiento Comercial y Finanzas (módulo M6 — Passenger Experience) |
| **Propósito** | Calcular y publicar en el FIDS/portal público una estimación agregada del tiempo de espera por puerta/terminal, a partir de datos operativos, sin capturar información nominal del pasajero (RNF-S05). |
| **Precondición** | Datos operativos del día (`ops.vuelo`, `ops.asignacion_puerta`) disponibles; ventana de agregación configurada. |
| **Flujo Principal** | 1. El sistema consolida el flujo estimado por puerta a partir de la ocupación y el histórico de turnaround.<br>2. Calcula el tiempo de espera agregado sin asociar el dato a ningún pasajero individual.<br>3. Publica la estimación en `billing.tiempo_espera_agregado` y la sincroniza con M2 FIDS (Sección 7.4). |
| **Postcondición** | Estimación visible en pantallas públicas con actualización <= 15 minutos; modelo de datos verificado sin campos de PII. |
| **RF Asociados** | RF-O17 |

### CU-T11: Recopilar Evidencia Continua de Cumplimiento SOC 2

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema / `role_sre` |
| **Departamento** | D5 — Plataforma y Seguridad |
| **Propósito** | Recolectar de forma automática y continua evidencias de controles técnicos (acceso, cifrado, backups, rotación de credenciales) exigidas por la auditoría SOC 2 Tipo II, evitando recopilación manual previa a la auditoría. |
| **Precondición** | `compliance.log_auditoria` y `compliance.reporte_dgac` operativos; controles de la matriz 4.4 implementados. |
| **Flujo Principal** | 1. Un job programado extrae periódicamente evidencias de `compliance.log_auditoria` (accesos, rotación de credenciales) y de la configuración de cifrado (RNF-S03).<br>2. Las evidencias se empaquetan por período y control (CC6, CC7 del framework SOC 2) y se almacenan de forma exportable.<br>3. `role_sre` revisa la completitud trimestral. |
| **Postcondición** | Evidencia continua disponible para el auditor externo (Acción 23), sin recopilación manual de última hora antes de la certificación (Acción 31). |
| **RF Asociados** | RF-T11 |

### CU-T13: Crear Entorno Sandbox de Prueba por Tenant *(incorporado en v5.1)*

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | `role_implementation` |
| **Departamento** | D6 — Soporte e Implementación |
| **Propósito** | Provisionar un entorno de prueba con datos sintéticos de vuelos para que un aeropuerto prospecto o un tenant en onboarding valide la integración antes de operar en producción, apoyando el TTFV < 30 días de OE6. |
| **Precondición** | Solicitud de sandbox aprobada; catálogo de datos sintéticos disponible. |
| **Flujo Principal** | 1. `role_implementation` solicita el aprovisionamiento de un tenant de prueba.<br>2. El sistema crea el registro en `tenants.tenant` con `is_sandbox=true` y límites reducidos (`limites_json`).<br>3. Se cargan datos sintéticos de vuelos, aerolíneas y rutas en `ops` bajo el `tenant_id` del sandbox.<br>4. Se notifica al solicitante con las credenciales de acceso temporal. |
| **Postcondición** | Sandbox operativo en menos de 10 minutos, aislado por RLS como cualquier tenant real, sin consumo del plan Developer/Sandbox más allá de los límites definidos (Sección 12.4). |
| **RF Asociados** | RF-T01 |
| **Nota de modelo de datos** | No requiere tabla adicional: reutiliza `tenants.tenant` con el atributo `is_sandbox`, y los esquemas `ops`/`rampa`/`billing` ya existentes bajo el `tenant_id` sintético. |

### CU-O20: Validar Acceso por Licencia de Módulo Disponible *(incorporado en v5.1)*

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema |
| **Departamento** | D5 — Plataforma y Seguridad |
| **Propósito** | Verificar en cada solicitud a un módulo (AODB, FIDS, Rampa, Billing, ML) que el tenant posee una licencia activa para ese módulo según su plan contratado, denegando el acceso en caso contrario. |
| **Precondición** | `tenants.licencia` poblada al momento del aprovisionamiento (CU-O18) o de un up-sell de plan. |
| **Flujo Principal** | 1. El API Gateway intercepta la solicitud e identifica el módulo destino y el `tenant_id`.<br>2. Consulta `tenants.licencia` verificando vigencia (`activa_desde`/`activa_hasta`).<br>3. Si la licencia está vigente, la solicitud continúa; si no, se deniega con HTTP 403 y se registra el evento en `compliance.log_auditoria`. |
| **Postcondición** | Ningún módulo es accesible sin licencia vigente; evento auditado en el 100% de los intentos denegados. |
| **RF Asociados** | RF-O18 |

### CU-T14: Promover Datos entre Capas Bronce, Plata y Oro *(incorporado en v6.0)*

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | Sistema (DAG de Airflow) / `role_data_engineer` para reproceso manual |
| **Departamento** | D4 — Datos e Inteligencia Artificial |
| **Propósito** | Ejecutar la transición de un artefacto entre capas medallion validando la condición de promoción correspondiente, garantizando que ningún dato inválido alcance la capa analítica. |
| **Precondición** | Artefacto presente en la capa de origen con estado `CRUDO`; ninguna ejecución previa en estado `PROCESANDO` para el mismo `(run_id, capa)`. |
| **Flujo Principal** | 1. La DAG toma el artefacto y registra la ejecución en `etl_control.etl_ejecucion` con estado `PROCESANDO`.<br>2. Ejecuta la validación de la transición (checksum en bronce, contrato de datos en plata, reglas de negocio en oro) y registra cada resultado en `etl_control.etl_validacion`.<br>3. Si todas aprueban, escribe el artefacto en la capa siguiente y marca `TERMINADO`.<br>4. Si alguna falla, mueve el artefacto a `/cuarentena` con su informe y marca `RECHAZADO`. |
| **Flujo Alternativo** | Si otra ejecución mantiene el mismo `(run_id, capa)` en `PROCESANDO`, la restricción de unicidad rechaza la nueva ejecución y la DAG termina sin efectos (PN-14). |
| **Postcondición** | El artefacto reside en la capa siguiente o en cuarentena; en ambos casos su estado y el detalle de validaciones son consultables. |
| **RF Asociados** | RF-T12, RF-T04 |

### CU-O21: Supervisar el Estado del Pipeline Medallion por Capa *(incorporado en v6.0)*

| Elemento | Descripción |
|:---|:---|
| **Actor Principal** | `role_data_engineer` |
| **Departamento** | D4 — Datos e Inteligencia Artificial |
| **Propósito** | Ofrecer visibilidad del estado de todas las ejecuciones ETL por capa, tenant y fecha, incluyendo artefactos en cuarentena y su motivo de rechazo, como insumo del KPI de calidad de datos. |
| **Precondición** | `etl_control.etl_ejecucion` poblada por las DAGs. |
| **Flujo Principal** | 1. El ingeniero consulta el tablero de pipeline filtrando por fecha, capa y tenant.<br>2. Identifica ejecuciones en `RECHAZADO` y consulta el detalle de `etl_validacion`.<br>3. Corrige el origen o ajusta la regla, y relanza la ejecución con un nuevo `run_id`. |
| **Postcondición** | Toda ejecución rechazada tiene causa identificada; la tasa de artefactos aprobados alimenta el KPI de calidad de datos de la perspectiva de procesos internos del BSC. |
| **RF Asociados** | RF-O19 |

---

# 7. Módulos del Sistema y Modelo de Datos por Departamento

## 7.1 Módulos Agrupados por Departamento Propietario

### D1 — Dirección de Operaciones Aeroportuarias

| Módulo | Descripción |
|:---|:---|
| **M1 — AODB (Airport Operational Database)** | Motor transaccional central. Almacena, procesa y distribuye la información de vuelos en tiempo real (itinerarios, estados, aerolíneas, aeronaves, demoras y causas tipificadas) con aislamiento por tenant. Implementado sobre MonetDB con aislamiento por tenant en la capa de repositorio (ADR-014). |
| **M2 — FIDS Management** | Diseño, aprovisionamiento y distribución de información a las pantallas físicas de la terminal. Transmite cambios de estado por WebSockets a través del API Gateway y cuenta con renderizado adaptable para monitores. |
| **M3 — Terminal & Gate Manager** | Motor algorítmico y visual para la asignación óptima de puertas de embarque, fajas de equipaje y posiciones remotas (optimización lineal con PuLP/SciPy). Minimiza conflictos de flujo y maximiza el uso de la infraestructura. |

### D2 — Ground Operations

| Módulo | Descripción |
|:---|:---|
| **M4 — Ground Operations (Rampa)** | Coordinación del turnaround: registro de inicio y fin de cada tarea en tierra (combustible, catering, limpieza, equipaje) para detectar demoras operativas y alimentar la analítica de puntualidad. |

### D3 — Crecimiento Comercial y Finanzas

| Módulo | Descripción |
|:---|:---|
| **M5 — Revenue & Billing** | Cálculo y emisión de facturas automáticas a las aerolíneas por cargos aeronáuticos (slots, mangas, estacionamiento) y tasas por pasajero. Integrado con pasarelas de pago locales. |
| **M6 — Passenger Experience** | Portales de retroalimentación del pasajero y estimación de tiempos de espera a partir de datos operativos agregados. No captura ni almacena PII de pasajeros (RNF-S05). Instrumentado por CU-O19 y `billing.tiempo_espera_agregado` (v5.1). |

### D4 — Datos e Inteligencia Artificial

| Módulo | Descripción |
|:---|:---|
| **M7 — ETL & Analytics** | Pipeline ETL orquestado con Airflow sobre arquitectura medallion: extracción desde MonetDB hacia bronce, refinamiento a plata y oro con Python/Polars, validación por transición con Great Expectations y carga idempotente a ClickHouse (`ah_tactico`, luego `ah_estrategico`). Incluye la plataforma MLOps (MLflow, Evidently) y el gobierno de ejecuciones en `etl_control`. |

### D5 — Plataforma y Seguridad

| Módulo | Descripción |
|:---|:---|
| **M8 — Observability & Alerting** | Monitoreo centralizado: métricas (Prometheus), logs (Loki) y trazas (Tempo) en Grafana, con alertas a PagerDuty (Sev1/2) y Slack (Sev3). Consumidor universal de todos los módulos. |
| **M9 — Compliance & Safety Hub** | Registro append-only de auditoría (modificaciones de itinerarios, accesos, facturación), incidentes de seguridad en rampa y reportes automáticos de conformidad DGAC/OACI. |

## 7.2 Base Operacional (MonetDB): Modelo Normalizado por Departamento

Conforme a ADR-013, la base operacional reside en MonetDB. Dado que este motor no
implementa Row-Level Security, el aislamiento por tenant deja de ser estructural y se
traslada a la capa de aplicación (ADR-014). Ello impone dos consecuencias de diseño que
gobiernan todo el modelo siguiente:

1. **`tenant_id` obligatorio y no nulo** en toda tabla de alcance de tenant, como primer
   atributo del índice primario, para que el filtro de aislamiento sea siempre indexable.
2. **Catálogos de referencia globales sin `tenant_id`** (aeropuertos, aerolíneas, modelos de
   aeronave, códigos IATA de demora): son datos de industria compartidos, no propiedad de
   ningún aeropuerto contratante, y su duplicación por tenant introduciría anomalías de
   actualización sin beneficio de aislamiento.

### 7.2.0 Criterios de Normalización Aplicados

El modelo alcanza **BCNF** en todas las tablas transaccionales y **4NF** en las entidades con
hechos multivaluados independientes. Las decisiones se documentan explícitamente porque la
versión 5.1 contenía violaciones que este rediseño corrige.

| Forma Normal | Criterio | Violaciones corregidas respecto a v5.1 |
|:---|:---|:---|
| **1NF** | Atributos atómicos; sin grupos repetitivos | `post_mortem.acciones_remediacion` (múltiples acciones en un campo) → `post_mortem_accion`. `changelog.contenido` → `changelog_item`. `articulo_kb` sin etiquetas → `articulo_kb_etiqueta`. `okr_interno` sin resultados clave → `okr_resultado_clave`. `ticket` sin hilo de conversación → `ticket_mensaje`. |
| **2NF** | Sin dependencias parciales de clave compuesta | `tarifario` mezclaba cabecera y precios por concepto → `tarifario` + `tarifario_concepto`. |
| **3NF** | Sin dependencias transitivas | `vuelo.estado_actual` (derivado del último `vuelo_estado`) eliminado. `factura.total` (derivado de líneas) eliminado. `conciliacion_pax.diferencia` (derivado) eliminado. `puerta.terminal` (texto) → FK a `terminal`. |
| **BCNF** | Todo determinante es clave candidata | `aeropuerto` y `aerolinea` tienen dos claves candidatas (`id` sustituta y `codigo_iata` natural); ambas determinan la tupla completa, sin dependencias cruzadas. |
| **4NF** | Sin dependencias multivaluadas | `vuelo` tenía hechos multivaluados independientes (estados, demoras, asignaciones de puerta) que en un modelo plano habrían producido producto cartesiano; cada uno reside en su propia relación. |
| **5NF** | Sin dependencias de join residuales | `tarifario_concepto` resuelve la relación ternaria tarifario-concepto-precio sin descomposición adicional posible sin pérdida. |

**Denormalizaciones deliberadas** (documentadas, no defectos):

| Atributo | Justificación |
|:---|:---|
| `cargo_aeronautico.tarifa_aplicada`, `monto_calculado` | Instantánea inmutable en el momento del cálculo. Si la tarifa se modifica después, el cargo histórico y la factura emitida no deben alterarse (integridad financiera y de auditoría, ISO 27002 8.15). Recalcular desde `tarifario_concepto` produciría cifras distintas a las facturadas. |
| `factura_linea.precio_unitario`, `monto` | Misma justificación: la línea de factura es evidencia contable congelada. |
| `encuesta_enps_respuesta.categoria_derivada` | Derivada de `puntuacion`, pero materializada para permitir agregación sin exponer la puntuación individual (minimización, ISO 27701). |

### 7.2.1 Catálogos Globales de Referencia (sin `tenant_id`)

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `pais` | id, codigo_iso2, codigo_iso3, nombre | PK id; UQ codigo_iso2; UQ codigo_iso3. |
| `aeropuerto` | id, codigo_iata, codigo_icao, nombre, pais_id, ciudad, zona_horaria, latitud, longitud | PK id; UQ codigo_iata; UQ codigo_icao; FK pais_id. Clave candidata natural: codigo_iata (BCNF). |
| `aerolinea` | id, codigo_iata, codigo_icao, nombre, pais_id | PK id; UQ codigo_iata; UQ codigo_icao; FK pais_id. |
| `modelo_aeronave` | id, codigo_icao_tipo, fabricante, modelo, capacidad_pax_tipica, envergadura_m, categoria_estela | PK id; UQ codigo_icao_tipo. `categoria_estela` restringida a L/M/H/J (OACI). |
| `aeronave` | id, matricula, modelo_aeronave_id, aerolinea_id | PK id; UQ matricula (globalmente única por convención OACI); FK modelo_aeronave_id, aerolinea_id. |
| `tipo_vuelo` | id, codigo, descripcion | PK id; UQ codigo. Comercial, carga, chárter, aviación general, militar. |
| `motivo_demora` | id, codigo_iata, descripcion, categoria | PK id; UQ codigo_iata. Códigos IATA de demora estandarizados; `categoria` agrupa para el BSC. |
| `estado_vuelo_catalogo` | id, codigo, descripcion, es_terminal | PK id; UQ codigo. `es_terminal` marca estados finales (aterrizado, cancelado, desviado). |
| `departamento` | id, codigo, nombre | PK id; UQ codigo. Catálogo D1-D6 de la Sección 4.1. |
| `modulo` | id, codigo, nombre, departamento_id | PK id; UQ codigo; FK departamento_id. Catálogo M1-M9 de la Sección 7.1. |

### 7.2.2 Esquema `tenants` (D5) — Identidad, Acceso y Licenciamiento

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `plan` | id, codigo, nombre, tarifa_base_mensual, moneda, activo | PK id; UQ codigo. Corresponde a la Sección 12.4. |
| `plan_modulo` | plan_id, modulo_id | PK compuesta (plan_id, modulo_id); FK a `plan` y `modulo`. Relación N:M sin atributos propios (2NF trivialmente satisfecha). |
| `tenant` | id, codigo, razon_social, aeropuerto_id, plan_id, es_sandbox, estado, creado_en | PK id; UQ codigo; FK aeropuerto_id, plan_id. `es_sandbox` sustenta CU-T13. |
| `licencia` | id, tenant_id, modulo_id, activa_desde, activa_hasta | PK id; FK tenant_id, modulo_id; UQ (tenant_id, modulo_id, activa_desde). Verificada en cada acceso por RF-O18. |
| `usuario` | id, tenant_id, email, hash_credencial, nombre, estado, mfa_habilitado, creado_en, ultimo_acceso_en | PK id; UQ (tenant_id, email); FK tenant_id. `tenant_id` nulo solo para usuarios de plataforma (AeroHub). |
| `rol` | id, codigo, nombre, alcance | PK id; UQ codigo. `alcance` ∈ {plataforma, tenant}, corresponde a la matriz 4.3. |
| `usuario_rol` | usuario_id, rol_id, otorgado_por, otorgado_en, expira_en | PK compuesta (usuario_id, rol_id); FK ambas. `expira_en` sustenta el acceso temporal de `role_implementation` y `role_regulatory_auditor`. |
| `api_key` | id, tenant_id, prefijo, hash_secreto, creada_en, rotada_en, expira_en, estado | PK id; UQ prefijo; FK tenant_id. Nunca almacena el secreto en claro (RF-O12). |
| `okr` | id, departamento_id, periodo, objetivo_descripcion, responsable_usuario_id, estado | PK id; FK departamento_id, responsable_usuario_id. Alcance interno AeroHub, sin `tenant_id`. |
| `okr_resultado_clave` | id, okr_id, descripcion, valor_inicial, valor_objetivo, valor_actual, unidad | PK id; FK okr_id. **Corrige 1NF de v5.1**: un OKR tiene múltiples resultados clave. |

### 7.2.3 Esquema `ops` (D1) — Núcleo AODB

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `terminal` | id, tenant_id, codigo, nombre | PK id; UQ (tenant_id, codigo); FK tenant_id. |
| `puerta` | id, tenant_id, terminal_id, codigo, tipo, envergadura_max_m, tiene_pasarela | PK id; UQ (tenant_id, codigo); FK terminal_id. **Corrige 3NF de v5.1**: la terminal era un atributo textual, generando dependencia transitiva. |
| `vuelo` | id, tenant_id, aerolinea_id, aeronave_id, numero_vuelo, tipo_vuelo_id, fecha_operacion, sentido, aeropuerto_origen_id, aeropuerto_destino_id, sta_utc, std_utc, eta_utc, etd_utc, ata_utc, atd_utc, pax_estimado, creado_en | PK id; UQ (tenant_id, aerolinea_id, numero_vuelo, fecha_operacion, sentido); FK a catálogos globales. **Sin `estado_actual`** (3NF): el estado vigente se obtiene de `vuelo_estado` mediante la vista `v_vuelo_estado_actual`. **Sin `ruta_id`**: la ruta es la pareja origen-destino, derivable; se materializa como dimensión únicamente en la capa analítica. |
| `vuelo_estado` | id, tenant_id, vuelo_id, estado_id, registrado_en, registrado_por_usuario_id, origen_cambio | PK id; FK vuelo_id, estado_id; IDX (tenant_id, vuelo_id, registrado_en DESC). Bitácora de eventos; el estado vigente es el registro más reciente. `origen_cambio` ∈ {manual, api, automatico}. |
| `asignacion_puerta` | id, tenant_id, vuelo_id, puerta_id, inicio_previsto, fin_previsto, inicio_real, fin_real, asignado_por_usuario_id, asignado_en, estado | PK id; FK vuelo_id, puerta_id. **Restricción de no solapamiento**: no pueden coexistir dos asignaciones activas sobre la misma `puerta_id` con intervalos `[inicio_previsto, fin_previsto)` intersecados (verificada en capa de aplicación y por PN-05, dado que MonetDB carece de tipos de rango con restricción de exclusión nativa). |
| `vuelo_demora` | id, tenant_id, vuelo_id, motivo_demora_id, minutos, registrado_en, registrado_por_usuario_id | PK id; FK vuelo_id, motivo_demora_id. **4NF**: un vuelo puede acumular varios motivos de demora independientes de sus cambios de estado y de sus asignaciones de puerta; mantenerlos en relaciones separadas evita el producto cartesiano. |
| `plantilla_fids` | id, tenant_id, nombre, definicion_json, version, vigente_desde, creada_por_usuario_id | PK id; UQ (tenant_id, nombre, version); FK tenant_id. |
| `pantalla_fids` | id, tenant_id, terminal_id, codigo, ubicacion_descripcion, plantilla_id, ultima_senal_en, version_firmware, estado | PK id; UQ (tenant_id, codigo); FK terminal_id, plantilla_id. Telemetría de RF-O07. |

### 7.2.4 Esquema `rampa` (D2) — Turnaround

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `tipo_tarea` | id, codigo, nombre, duracion_estandar_min, es_ruta_critica | PK id; UQ codigo. Catálogo global (no por tenant): los tipos de tarea de rampa son estándar de industria. |
| `tipo_incidencia_rampa` | id, codigo, descripcion | PK id; UQ codigo. |
| `turnaround` | id, tenant_id, vuelo_llegada_id, vuelo_salida_id, aeronave_id, inicio_previsto, fin_previsto, inicio_real, fin_real, estado | PK id; UQ (tenant_id, vuelo_llegada_id); FK ambos vuelos y aeronave. **Entidad nueva en v6.0**: en v5.1 las tareas colgaban directamente del vuelo, lo que impedía expresar el emparejamiento llegada→salida que *define* un turnaround y obligaba a inferirlo por convención. |
| `tarea_turnaround` | id, tenant_id, turnaround_id, tipo_tarea_id, agente_usuario_id, inicio_real, fin_real, estado | PK id; FK turnaround_id, tipo_tarea_id, agente_usuario_id. La duración se deriva de `fin_real - inicio_real`; no se almacena (3NF). |
| `incidencia_rampa` | id, tenant_id, tarea_turnaround_id, tipo_incidencia_id, descripcion, severidad, detectada_en, resuelta_en, resuelta_por_usuario_id | PK id; FK tarea_turnaround_id, tipo_incidencia_id. Sustenta RF-O16 y OP2b. |

### 7.2.5 Esquema `billing` (D3) — Tarifación y Facturación

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `concepto_cargo` | id, codigo, nombre, unidad_medida, base_calculo | PK id; UQ codigo. `base_calculo` ∈ {peso_mtow, pax, tiempo_estacionamiento, uso_pasarela, fijo}. Catálogo global. |
| `tarifario` | id, tenant_id, nombre, moneda, vigente_desde, vigente_hasta, estado, creado_por_usuario_id | PK id; FK tenant_id. **Corrige 2NF de v5.1**: la cabecera del tarifario (vigencia, moneda) se separa de los precios por concepto, que dependían solo parcialmente de la clave. |
| `tarifario_concepto` | id, tarifario_id, concepto_cargo_id, tarifa_unitaria, monto_minimo, monto_maximo | PK id; UQ (tarifario_id, concepto_cargo_id); FK ambas. Resuelve la relación ternaria en 5NF. |
| `cargo_aeronautico` | id, tenant_id, vuelo_id, concepto_cargo_id, tarifario_concepto_id, cantidad, tarifa_aplicada, monto_calculado, calculado_en | PK id; FK vuelo_id, concepto_cargo_id, tarifario_concepto_id. `tarifa_aplicada` y `monto_calculado` son denormalización deliberada (instantánea inmutable). |
| `factura` | id, tenant_id, aerolinea_id, periodo_inicio, periodo_fin, moneda, estado, emitida_en, vence_en | PK id; UQ (tenant_id, aerolinea_id, periodo_inicio, periodo_fin); FK aerolinea_id. **Sin `total`** (3NF): se obtiene por agregación de `factura_linea`. |
| `factura_linea` | id, factura_id, cargo_aeronautico_id, descripcion, cantidad, precio_unitario, monto | PK id; UQ cargo_aeronautico_id (un cargo se factura una sola vez); FK factura_id, cargo_aeronautico_id. |
| `conciliacion_pax` | id, tenant_id, vuelo_id, periodo, pax_reportado_aerolinea, pax_registrado_sistema, fuente_reporte, conciliado_en, conciliado_por_usuario_id | PK id; UQ (tenant_id, vuelo_id, periodo); FK vuelo_id. **Sin `diferencia`** (3NF): derivada de los dos conteos. |
| `tiempo_espera_agregado` | id, tenant_id, terminal_id, fecha, franja_inicio, franja_fin, minutos_estimados, muestra_n, calculado_en | PK id; UQ (tenant_id, terminal_id, fecha, franja_inicio); FK terminal_id. Módulo M6 (RF-O17). `muestra_n` permite descartar estimaciones con soporte estadístico insuficiente. **Sin atributo alguno que identifique a un pasajero** (RNF-S05, verificado por PN-11). |

### 7.2.6 Esquema `compliance` (D5) — Auditoría, Cumplimiento y Post-Mortems

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `log_auditoria` | id, tenant_id, esquema, tabla, registro_id, operacion, usuario_id, rol_codigo, ocurrido_en, valores_anteriores, valores_nuevos, ip_origen | PK id; IDX (tenant_id, ocurrido_en DESC). **Append-only**. El `tenant_id` se toma del token validado, nunca del cuerpo de la petición (control de ADR-014). |
| `tipo_incidente` | id, codigo, descripcion, categoria | PK id; UQ codigo. Catálogo global. |
| `incidente_seguridad` | id, tenant_id, tipo_incidente_id, descripcion, severidad, detectado_en, reportado_por_usuario_id, estado | PK id; FK tipo_incidente_id. Append-only. |
| `tipo_reporte_regulatorio` | id, codigo, nombre, periodicidad, autoridad | PK id; UQ codigo. DGAC, OACI. |
| `reporte_dgac` | id, tenant_id, tipo_reporte_id, periodo_inicio, periodo_fin, contenido_ref, hash_contenido, emitido_por_usuario_id, emitido_en | PK id; FK tipo_reporte_id. `hash_contenido` permite verificar integridad del artefacto exportado. Append-only. |
| `acceso_auditor` | id, tenant_id, auditor_usuario_id, otorgado_por_usuario_id, inicio, fin, alcance_json, motivo | PK id; FK auditor_usuario_id. Append-only. |
| `post_mortem` | id, tenant_id, incidente_ref, severidad, causa_raiz, estado, iniciado_en, publicado_en, tiempo_resolucion_min | PK id. **Excepción controlada de UPDATE** sobre `causa_raiz` y `estado` (ADR-009); toda edición queda registrada en `log_auditoria`. |
| `post_mortem_accion` | id, post_mortem_id, descripcion, responsable_usuario_id, ticket_ref, estado, vence_en, completada_en | PK id; FK post_mortem_id. **Corrige 1NF de v5.1**, donde las acciones de remediación se almacenaban como un único atributo no atómico. Permite además consultar acciones vencidas sin análisis de texto. |
| `control_soc2` | id, codigo_control, nombre, categoria | PK id; UQ codigo_control. Catálogo de controles del marco SOC 2 (CC6, CC7, etc.). |
| `evidencia_soc2` | id, control_soc2_id, tenant_id, periodo_inicio, periodo_fin, referencia_log_id, ruta_artefacto, hash_artefacto, generado_en | PK id; FK control_soc2_id, referencia_log_id. Append-only (RF-T11). |

### 7.2.7 Esquema `support` (D6) — Soporte y Documentación

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `categoria_ticket` | id, codigo, nombre | PK id; UQ codigo. |
| `ticket` | id, tenant_id, categoria_id, creado_por_usuario_id, asignado_a_usuario_id, severidad, estado, asunto, creado_en, primera_respuesta_en, resuelto_en, sla_objetivo_min | PK id; FK categoria_id, ambos usuarios. Sustenta RF-O08 y el proxy de OE6 durante el MVP. |
| `ticket_mensaje` | id, ticket_id, autor_usuario_id, cuerpo, enviado_en, es_interno | PK id; FK ticket_id, autor_usuario_id. **Corrige 1NF de v5.1**: el hilo de conversación no era representable en el modelo anterior. |
| `articulo_kb` | id, titulo, cuerpo, version, estado, publicado_en, autor_usuario_id, embedding_ref | PK id; UQ (titulo, version). Sin `tenant_id`: la base de conocimientos es común a todos los tenants. |
| `etiqueta` | id, nombre | PK id; UQ nombre. |
| `articulo_kb_etiqueta` | articulo_id, etiqueta_id | PK compuesta; FK ambas. **Corrige 1NF de v5.1**: las etiquetas eran un atributo multivaluado. |
| `changelog` | id, version_producto, resumen, publicado_en | PK id; UQ version_producto. |
| `changelog_item` | id, changelog_id, modulo_id, tipo_cambio, descripcion | PK id; FK changelog_id, modulo_id. **Corrige 1NF de v5.1**. `tipo_cambio` ∈ {nuevo, mejora, corrección, obsolescencia}. |

### 7.2.8 Esquema `people` (D5 hosting técnico) — Talento Interno

Sin `tenant_id` por ser de alcance interno de AeroHub (ADR-010). Diseñado bajo minimización
de ISO/IEC 27701: **ninguna tabla referencia a un empleado individual**.

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `periodo_encuesta` | id, anio, trimestre, abierta_desde, cerrada_en | PK id; UQ (anio, trimestre). |
| `encuesta_enps_respuesta` | id, periodo_encuesta_id, departamento_id, puntuacion, categoria_derivada | PK id; FK periodo_encuesta_id, departamento_id. **Deliberadamente sin FK a empleado**: la anonimidad es estructural, no procedimental. `categoria_derivada` ∈ {promotor, pasivo, detractor}. |
| `metrica_departamento` | id, departamento_id, periodo, headcount_inicio, headcount_fin, bajas_voluntarias, bajas_involuntarias, time_to_productivity_dias_prom | PK id; UQ (departamento_id, periodo); FK departamento_id. Agregados exclusivamente; la tasa de retención se deriva, no se almacena (3NF). |

### 7.2.9 Esquema `etl_control` (D4) — Gobierno del Pipeline

Incorporado en v6.0 para sustentar RF-O19 y RF-T12 (ADR-015).

| Tabla | Atributos | Claves e Integridad |
|:---|:---|:---|
| `etl_ejecucion` | id, run_id, dag_id, tenant_id, capa, archivo_ruta, estado, registros_entrada, registros_salida, checksum_sha256, iniciado_en, finalizado_en, error_detalle | PK id; UQ (run_id, capa); IDX (tenant_id, iniciado_en DESC). `capa` ∈ {bronce, plata, oro}; `estado` ∈ {CRUDO, PROCESANDO, TERMINADO, RECHAZADO}. La unicidad de (run_id, capa) es lo que impide el reprocesamiento concurrente verificado por PN-14. |
| `etl_validacion` | id, etl_ejecucion_id, tipo_validacion, regla, resultado, registros_fallidos, detalle_json | PK id; FK etl_ejecucion_id. **1NF**: una ejecución acumula múltiples validaciones (esquema, dominios, nulos, duplicados, reglas de negocio). |

### 7.2.10 Relaciones Inter-Esquema y Vistas Derivadas

| Origen | Destino | Naturaleza |
|:---|:---|:---|
| `rampa.turnaround.vuelo_llegada_id` / `vuelo_salida_id` | `ops.vuelo.id` | FK dura. Todo turnaround empareja dos vuelos del AODB. |
| `billing.cargo_aeronautico.vuelo_id` | `ops.vuelo.id` | FK dura. Todo cargo se origina en un movimiento operado. |
| `billing.tiempo_espera_agregado.terminal_id` | `ops.terminal.id` | FK dura. |
| `compliance.log_auditoria` | (todas) | Lógica, poblada por la capa de aplicación (MonetDB no ofrece triggers equivalentes a los de PostgreSQL; ver ADR-014). |
| `compliance.evidencia_soc2.referencia_log_id` | `compliance.log_auditoria.id` | FK dura. |
| `support.ticket.creado_por_usuario_id` | `tenants.usuario.id` | FK dura. |

**Vistas derivadas obligatorias** (sustituyen a los atributos denormalizados eliminados):

| Vista | Reemplaza a | Definición |
|:---|:---|:---|
| `ops.v_vuelo_estado_actual` | `vuelo.estado_actual` | Último `vuelo_estado` por `vuelo_id` según `registrado_en`. |
| `billing.v_factura_total` | `factura.total` | Suma de `factura_linea.monto` agrupada por `factura_id`. |
| `billing.v_conciliacion_diferencia` | `conciliacion_pax.diferencia` | `pax_reportado_aerolinea - pax_registrado_sistema`. |
| `people.v_tasa_retencion` | (nueva) | Derivada de `metrica_departamento`, insumo del BSC de talento. |

## 7.3 Capa Analítica (ClickHouse): Dos Bases por Nivel de Objetivo

Conforme a ADR-012 y ADR-016, la capa analítica reside íntegramente en ClickHouse y se
segmenta en dos bases de datos alineadas al nivel de objetivo que sirven. MonetDB queda
reservado exclusivamente a la operación transaccional (ADR-013).

| Base de datos | Alcance | Granularidad | Consumidores (roles) | Objetivos servidos |
|:---|:---|:---|:---|:---|
| `ah_tactico` | Hechos por vuelo y turnaround, dimensiones conformadas, features de ML | Detalle por vuelo, por tenant, por día | `role_data_engineer`, `role_ml_engineer`, `role_tenant_analyst` | OT1-OT14 (CU-T04, CU-T05, CU-T10, CU-O05, CU-O06) |
| `ah_estrategico` | KPIs consolidados de las cuatro perspectivas del BSC, series históricas largas | Agregada por mes/trimestre; sin detalle de vuelo individual | `role_business_viewer`, `role_platform_admin`, `role_people_viewer` (solo perspectiva de talento) | OE1-OE6 (CU-E01, CU-E02, CU-E06) |

### 7.3.1 Regla de Derivación Unidireccional

`ah_estrategico` **se deriva de `ah_tactico`**, nunca se ingiere en paralelo desde el origen:

```
MonetDB (operacional) → bronce → plata → oro → ah_tactico → ah_estrategico
```

Esta restricción es deliberada y no negociable. Una doble ingestión independiente permitiría
que el tablero estratégico y el táctico reporten cifras distintas para el mismo indicador,
que es el modo de fallo más costoso en reputación de un Balanced Scorecard: una vez que el
directorio detecta dos cifras de puntualidad divergentes, la confianza en todo el tablero se
pierde. La derivación unidireccional garantiza que `ah_estrategico` sea siempre una agregación
verificable de `ah_tactico`, reconciliable registro a registro.

### 7.3.2 Base `ah_tactico` — Esquema Estrella de Detalle

**Dimensiones conformadas** (compartidas por todos los hechos):

| Tabla | Motor | Clave de Ordenamiento | Notas |
|:---|:---|:---|:---|
| `dim_tiempo` | `MergeTree` | `fecha` | Calendario con atributos derivados (trimestre, semana ISO, temporada alta/baja). |
| `dim_tenant` | `ReplacingMergeTree(version)` | `tenant_id` | SCD tipo 1; refleja el estado vigente del tenant. |
| `dim_aerolinea` | `ReplacingMergeTree(version)` | `aerolinea_id` | |
| `dim_aeropuerto` | `ReplacingMergeTree(version)` | `aeropuerto_id` | |
| `dim_ruta` | `ReplacingMergeTree(version)` | `(aeropuerto_origen_id, aeropuerto_destino_id)` | Materializada aquí, no en la operacional (donde sería redundante). |
| `dim_aeronave` | `ReplacingMergeTree(version)` | `aeronave_id` | Incluye modelo y categoría de estela desnormalizados. |
| `dim_puerta` | `ReplacingMergeTree(version)` | `(tenant_id, puerta_id)` | Incluye terminal desnormalizada. |
| `dim_motivo_demora` | `ReplacingMergeTree(version)` | `motivo_demora_id` | |

**Tablas de hechos:**

| Tabla | Motor | Partición | Ordenamiento | TTL |
|:---|:---|:---|:---|:---|
| `hecho_vuelo` | `ReplacingMergeTree(cargado_en)` | `toYYYYMM(fecha_operacion)` | `(tenant_id, fecha_operacion, vuelo_id)` | 5 años |
| `hecho_turnaround` | `ReplacingMergeTree(cargado_en)` | `toYYYYMM(fecha_operacion)` | `(tenant_id, fecha_operacion, turnaround_id)` | 5 años |
| `hecho_demora` | `ReplacingMergeTree(cargado_en)` | `toYYYYMM(fecha_operacion)` | `(tenant_id, fecha_operacion, vuelo_id, motivo_demora_id)` | 5 años |
| `hecho_cargo` | `ReplacingMergeTree(cargado_en)` | `toYYYYMM(periodo)` | `(tenant_id, periodo, vuelo_id, concepto_cargo_id)` | 7 años (retención fiscal) |
| `feature_prediccion_demora` | `MergeTree` | `toYYYYMM(fecha_operacion)` | `(tenant_id, fecha_operacion, vuelo_id)` | 2 años |

`ReplacingMergeTree` es la elección correcta para hechos recargables: permite que una
reejecución de la DAG sobre el mismo período sustituya registros sin duplicarlos, propiedad
indispensable para la idempotencia exigida en la transición oro→ClickHouse (Sección 7.6).

### 7.3.3 Base `ah_estrategico` — Agregados del Balanced Scorecard

| Tabla | Motor | Partición | Ordenamiento | Contenido |
|:---|:---|:---|:---|:---|
| `kpi_snapshot` | `ReplacingMergeTree(calculado_en)` | `toYYYYMM(fecha_corte)` | `(perspectiva, kpi_codigo, tenant_id, fecha_corte)` | KPI consolidado por perspectiva del BSC (RF-E01, CU-E01). Sustituye a `analytics_bsc.kpi_snapshot` de v5.1. |
| `resumen_operacion_mensual` | `ReplacingMergeTree(calculado_en)` | `toYYYYMM(periodo)` | `(tenant_id, periodo)` | Puntualidad, movimientos, pax procesados, turnaround promedio. |
| `resumen_financiero_mensual` | `ReplacingMergeTree(calculado_en)` | `toYYYYMM(periodo)` | `(tenant_id, periodo)` | ARR, facturación, margen bruto, costo cloud por tenant (OT14). |
| `resumen_cliente_trimestral` | `ReplacingMergeTree(calculado_en)` | `toYYYYMM(periodo)` | `(tenant_id, periodo)` | NPS, CSAT, TTFV, churn (OE6). |
| `resumen_talento_trimestral` | `ReplacingMergeTree(calculado_en)` | `toYYYYMM(periodo)` | `(departamento_id, periodo)` | eNPS, retención, time-to-productivity. Sin `tenant_id`: alcance interno. |

**Catálogo de KPIs** (`dim_kpi`): `kpi_codigo`, `nombre`, `perspectiva`, `unidad`,
`meta_objetivo`, `direccion_favorable`, `formula_descripcion`, `fuente_tabla`. Permite que el
tablero se construya por metadatos en vez de por consultas fijas, y que cada KPI declare su
tabla de origen, cerrando la trazabilidad exigida en la Sección 11.6 hasta el nivel de dato.

### 7.3.4 Aislamiento Multi-Tenant en la Capa Analítica

A diferencia de MonetDB, **ClickHouse sí implementa políticas de fila** (`CREATE ROW POLICY`).
El aislamiento por tenant se conserva por tanto como control estructural en la capa
analítica, aun cuando en la operacional haya migrado a la capa de aplicación (ADR-014):

```sql
CREATE ROW POLICY politica_tenant ON ah_tactico.hecho_vuelo
  FOR SELECT USING tenant_id = getSetting('SQL_tenant_actual')
  TO role_tenant_analyst;
```

Esta asimetría es intencional y debe entenderse como mitigación parcial de la degradación
introducida por ADR-013: la superficie de datos históricos —la de mayor volumen y por tanto
la de mayor impacto ante una fuga— mantiene enforcement a nivel de motor. Los roles internos
de AeroHub (`role_data_engineer`, `role_ml_engineer`) operan sin política de fila por
requerir visión cruzada para entrenamiento de modelos y diagnóstico de pipeline, lo cual queda
registrado en `compliance.log_auditoria` y verificado por PN-13.

### 7.3.5 Segregación entre Bases Analíticas

Ningún rol posee acceso simultáneo de escritura a ambas bases. `ah_estrategico` es poblada
exclusivamente por la DAG de agregación ejecutada bajo la identidad técnica `role_elt_writer`;
`role_business_viewer` posee únicamente `SELECT` sobre `ah_estrategico` y **ningún acceso a
`ah_tactico`**, evitando que el nivel estratégico consulte detalle transaccional que su nivel
de decisión no requiere (principio de mínimo privilegio, ISO/IEC 27002 8.2). La verificación
de esta frontera es PN-13.

## 7.4 Diagrama de Dependencias entre Módulos

| Módulo Origen | Módulo Destino | Tipo de Dependencia |
|:---|:---|:---|
| M2 FIDS | M1 AODB | Consume estados de vuelo y cambios de horario en tiempo real. |
| M3 Terminal & Gate | M1 AODB | Lee vuelos activos y programados para asignar puertas. |
| M4 Ground Operations | M1 AODB | Requiere ETA para movilizar personal de rampa. |
| M4 Ground Operations | M3 Terminal & Gate | Necesita la puerta o posición remota asignada. |
| M5 Revenue & Billing | M1 AODB | Consume despegues y aterrizajes reales para calcular cargos. |
| M5 Revenue & Billing | M3 Terminal & Gate | Consume uso de mangas y fajas para cargos adicionales. |
| M6 Passenger Experience | M2 FIDS | Sincroniza información mostrada con tiempos de espera agregados. |
| M7 ETL & Analytics | M1, M4, M5 | Extrae registros operativos, de rampa y de facturación hacia staging. |
| M9 Compliance Hub | M1 AODB | Audita modificaciones de itinerarios para reportes DGAC. |
| M8 Observability | Todos | Recolecta métricas, logs y trazas (consumidor universal). |

## 7.5 Fuentes de Datos Externas No Modeladas en la Base Operacional ni Analítica

Dos requisitos funcionales dependen de sistemas externos cuya integración no se documentaba
formalmente en versiones previas, generando ambigüedad sobre el origen del dato. Se declaran
aquí como fuentes explícitas, consistente con el tratamiento ya dado a MLflow y Great
Expectations (ADR-003).

| RF / OT | Fuente Externa | Mecanismo de Integración | Responsable |
|:---|:---|:---|:---|
| RF-E01 (parcial, iniciativa de CAC), OT13 (CU-T01) | CRM comercial (fuera del alcance de este documento; ej. HubSpot/Pipedrive) | Webhook/API REST hacia el API Gateway; el pipeline comercial (leads, oportunidades, etapas) reside en el CRM, no en `billing`. | D3 — Crecimiento Comercial |
| RF-T08 (OT14, CU-T08) | Consola de facturación del proveedor PaaS | API del proveedor consultada periódicamente por un job de D5; no se replica en la base operacional salvo que se requiera trazabilidad histórica para auditoría de Margen Bruto, en cuyo caso se evaluará una tabla `compliance.costo_cloud_snapshot` en una futura revisión. | D5 — Plataforma y Seguridad |

Esta sección no introduce nuevas tablas: formaliza la ausencia intencional de modelo interno
para datos cuya fuente de verdad es un sistema de terceros, evitando que auditorías futuras de
trazabilidad (Sección 11.6) las interpreten como gaps no resueltos.

---

## 7.6 Arquitectura Medallion y Gobierno de Ejecuciones ETL

Incorporada en v6.0 conforme a ADR-015. El pipeline orquestado por Airflow materializa cada
ejecución como artefactos en disco organizados en tres capas de refinamiento, con un estado
de ejecución registrado de forma independiente.

### 7.6.1 Separación entre Capa de Refinamiento y Estado de Ejecución

Capa y estado son dimensiones **ortogonales**, no sinónimos. Conflacionarlas produce
ambigüedad operativa: un archivo "procesado" no indica si reside en plata o si es un archivo
de bronce cuyo procesamiento concluyó. El modelo las separa explícitamente:

- **Capa** (bronce / plata / oro): *dónde* está el dato y *cuánto* refinamiento acumula.
- **Estado** (CRUDO / PROCESANDO / TERMINADO / RECHAZADO): *en qué punto del ciclo* está la
  ejecución que produce o consume ese archivo.

Un archivo en plata con estado `CRUDO` es perfectamente válido: ya fue validado y promovido
desde bronce, pero la DAG que lo transformará a oro aún no lo ha tomado.

### 7.6.2 Estructura de la Carpeta de Datos

```
/data
  /bronce                          <- ingesta cruda, inmutable
    /YYYY-MM-DD
      /<tenant_id>
        vuelos_<run_id>.parquet
        turnaround_<run_id>.parquet
        _manifest.json
  /plata                           <- validado y normalizado
    /YYYY-MM-DD
      /<tenant_id>
        vuelos_<run_id>.parquet
        _manifest.json
  /oro                             <- agregados listos para carga
    /YYYY-MM-DD
      hecho_vuelo_<run_id>.parquet
      hecho_turnaround_<run_id>.parquet
      kpi_estrategico_<run_id>.parquet
      _manifest.json
  /cuarentena                      <- artefactos RECHAZADOS
    /YYYY-MM-DD
      /<tenant_id>
        vuelos_<run_id>.parquet
        _informe_validacion.json
```

**Formato:** Parquet en las tres capas. Es columnar, comprimido y tipado, lo que evita la
pérdida de tipos que introduce CSV entre etapas y reduce el volumen en disco frente a JSON.
En bronce se conserva adicionalmente el archivo en su formato original cuando el origen no es
tabular, para preservar la trazabilidad del dato tal como fue recibido.

**Particionamiento por fecha y tenant:** permite reprocesar un día de un tenant específico sin
tocar el resto, requisito operativo frecuente cuando un aeropuerto corrige su reporte de
pasajeros a posteriori.

### 7.6.3 Manifiesto por Ejecución

Cada carpeta de ejecución contiene un `_manifest.json` con la misma información que persiste
`etl_control.etl_ejecucion` (Sección 7.2.9), garantizando que el estado del pipeline sea
reconstruible aun ante pérdida de la base de control:

```json
{
  "run_id": "2026-11-04T03:00:00Z__ingesta_vuelos__aeropuerto_mec",
  "dag_id": "ingesta_vuelos_diaria",
  "tenant_id": "aeropuerto_mec",
  "capa": "bronce",
  "estado": "TERMINADO",
  "registros_entrada": 148,
  "registros_salida": 148,
  "checksum_sha256": "9f2b...",
  "iniciado_en": "2026-11-04T03:00:12Z",
  "finalizado_en": "2026-11-04T03:01:47Z",
  "validaciones": [
    { "tipo": "integridad_transferencia", "resultado": "APROBADO", "registros_fallidos": 0 }
  ]
}
```

### 7.6.4 Máquina de Estados de Ejecución

| Estado | Significado | Transición desde | Transición hacia |
|:---|:---|:---|:---|
| `CRUDO` | Archivo depositado en la capa; la DAG siguiente aún no lo ha tomado | (inicial) | `PROCESANDO` |
| `PROCESANDO` | DAG en ejecución sobre el archivo | `CRUDO` | `TERMINADO`, `RECHAZADO` |
| `TERMINADO` | Promovido a la capa siguiente con éxito | `PROCESANDO` | (final exitoso) |
| `RECHAZADO` | Falló una validación; el artefacto se mueve a `/cuarentena` y no promueve | `PROCESANDO` | (final con error) |

La unicidad de `(run_id, capa)` en `etl_control.etl_ejecucion` es el mecanismo que impide el
reprocesamiento concurrente del mismo artefacto: una segunda DAG que intente tomar un archivo
ya en estado `PROCESANDO` es rechazada por violación de restricción única, no por convención
de código. Esta propiedad se verifica en PN-14.

### 7.6.5 Puntos de Validación por Transición

Redefine y amplía RF-T04, que en v5.1 declaraba un único punto de validación.

| Transición | Validación | Herramienta | Falla implica |
|:---|:---|:---|:---|
| Origen → **Bronce** | Integridad de transferencia: checksum SHA-256, conteo de registros, formato legible | Sensor de Airflow | `RECHAZADO`; alerta a D4; el archivo original permanece en el origen para reintento |
| Bronce → **Plata** | Contrato de datos: esquema, tipos, dominios de catálogo, nulos en obligatorios, duplicados por clave natural | Great Expectations | `RECHAZADO`; artefacto a `/cuarentena` con informe de validación; no promueve |
| Plata → **Oro** | Reglas de negocio: conciliación de pasajeros, integridad referencial contra dimensiones, coherencia temporal (ATA >= ATD del tramo previo) | Suite SQL / Polars | `RECHAZADO`; el agregado no se construye |
| Oro → **ClickHouse** | Idempotencia de carga y verificación de conteo destino = conteo origen por partición | Airflow + ClickHouse | Rollback de la partición cargada (`ALTER TABLE ... DROP PARTITION`) |
| `ah_tactico` → **`ah_estrategico`** | Reconciliación: cada KPI agregado debe reproducirse desde el detalle con tolerancia cero | Suite SQL | La agregación no se publica; el tablero conserva el corte anterior |

La última fila es la que materializa la regla de derivación unidireccional de la Sección
7.3.1: el tablero estratégico nunca publica una cifra que no sea reproducible desde el detalle
táctico.

### 7.6.6 Retención y Ciclo de Vida de Artefactos

| Capa | Retención en disco | Justificación |
|:---|:---|:---|
| Bronce | 90 días | Ventana de reproceso ante correcciones tardías del aeropuerto; el dato permanece en ClickHouse indefinidamente según TTL de cada hecho. |
| Plata | 30 días | Intermedio reconstruible desde bronce; retención menor por ser reproducible. |
| Oro | 30 días | Reconstruible desde plata; ClickHouse es la fuente de verdad una vez cargado. |
| Cuarentena | 180 días | Evidencia de incidentes de calidad de datos; insumo de análisis de causa raíz y de auditoría (D2 del FODA: dependencia de fuentes externas). |

---

# 8. Arquitectura y Stack Tecnológico Definitivo

## 8.1 Vista General

```
                            Angular 20+ (SPA)
    Portal Operativo · Tablero Estratégico (Z) · Tableros Tácticos (F) · FIDS
                                   │ HTTPS / WSS
                                   ▼
                       API Gateway (FastAPI, Python)
   AuthN/AuthZ JWT · Rate limiting · WebSocket · Validación de licencia (RF-O18)
   INYECCIÓN OBLIGATORIA DE tenant_id DESDE EL TOKEN (ADR-014)
                    │                                    │
                    ▼                                    ▼
     Servicios Transaccionales              Servicios Analíticos (Python)
     AODB · Gates · Rampa · Billing         API BI · Scoring ML
                    │                            │              │
                    │ vía capa de repositorio    │              │
                    │ (único punto con SQL)      │              │
                    ▼                            ▼              ▼
     ┌──────────────────────────┐      ┌──────────────┐  ┌──────────────────┐
     │   MonetDB (OPERACIONAL)  │      │ ah_tactico   │  │ ah_estrategico   │
     │   ops · rampa · billing  │      │ (ClickHouse) │  │ (ClickHouse)     │
     │   tenants · compliance   │      │ hechos +     │  │ kpi_snapshot +   │
     │   support · people       │      │ dimensiones  │  │ resúmenes BSC    │
     │   etl_control            │      └──────────────┘  └──────────────────┘
     │   SIN RLS → aislamiento  │             ▲                   ▲
     │   en capa de aplicación  │             │                   │
     └──────────────────────────┘             │        derivación unidireccional
                    │                         │        (nunca ingesta paralela)
                    │ extracción batch        │                   │
                    ▼                         │                   │
     ┌──────────────────────────────────────────────────────────────────┐
     │              Airflow — Orquestación del Pipeline Medallion       │
     │                                                                  │
     │   /data/bronce ──► /data/plata ──► /data/oro ──► ClickHouse      │
     │    (crudo)        (validado)      (agregado)                     │
     │       │               │               │                          │
     │   checksum      Great Expect.    reglas negocio                  │
     │       └───────────────┴───────────────┴──► /data/cuarentena      │
     │                                              (RECHAZADO)         │
     │   Estado por ejecución → etl_control.etl_ejecucion (MonetDB)     │
     └──────────────────────────────────────────────────────────────────┘

  Integraciones externas no replicadas (Sección 7.5):
  CRM comercial (OT13) ──► API Gateway
  Consola de costos PaaS (OT14) ──► job D5
  Grafana/Prometheus (Uptime, Error Budget) ──► DAG de agregación BSC
```

**Alineación objetivo ↔ capa de datos (ADR-016):** los tableros estratégicos consultan
exclusivamente `ah_estrategico`; los tácticos, `ah_tactico`; los flujos operativos, MonetDB.
La regla es direccional: ningún consumidor estratégico o táctico accede a la base operacional,
pero los procesos operativos sí escriben en ella como fuente de todo el pipeline.

## 8.2 Stack por Componente

| Componente | Tecnología | Owner | Justificación (ISO/IEC 25010) |
|:---|:---|:---|:---|
| Frontend único | Angular 20+ | D1 (producto) / D5 (build) | Un solo framework reduce superficie de ataque y costo de mantenimiento; FIDS players como build ligero del monorepo. |
| API Gateway | FastAPI, JWT, rate limiting, validación de licencia (RF-O18) | D5 | Fachada única de autenticación; **punto de inyección del `tenant_id`** que sustituye al RLS perdido (ADR-014). |
| Capa de repositorio | Python, SQLAlchemy Core con filtro de tenant obligatorio | D5 (contrato) / D1-D3 (uso) | **Único componente autorizado a emitir SQL** hacia MonetDB; su unicidad es lo que hace verificable el aislamiento en ausencia de RLS. |
| Servicios transaccionales | FastAPI + Pydantic v2 | D1, D2, D3 | Lógica de AODB, rampa y billing. |
| Base operacional | **MonetDB** (esquemas departamentales, sin RLS) | D5 (infraestructura) / owners por esquema | Motor operacional adoptado por ADR-013. Requiere los controles compensatorios de ADR-014 y una estrategia de respaldo explícita (Acción 1b) por no disponer de PITR nativo equivalente. |
| Almacén analítico táctico | **ClickHouse** — base `ah_tactico` | D4 | Hechos y dimensiones a nivel de vuelo; `ReplacingMergeTree` para recarga idempotente (ADR-012). |
| Almacén analítico estratégico | **ClickHouse** — base `ah_estrategico` | D4 (carga) / D3 (consumo) | KPIs consolidados del BSC, derivados de `ah_tactico` (ADR-016). |
| Orquestación ETL | Apache Airflow (DAGs en Python) | D4 | Programación, reintentos, observabilidad y control de estados del pipeline medallion (ADR-015). |
| Capas de datos en disco | Parquet sobre almacenamiento de objetos, particionado por fecha y tenant | D4 | Bronce/plata/oro con manifiesto por ejecución; formato columnar tipado que evita pérdida de tipos entre etapas. |
| Control de ejecuciones ETL | Tablas `etl_control` en MonetDB | D4 | Estado, conteos y checksum por ejecución (RF-O19); la unicidad `(run_id, capa)` bloquea reprocesos concurrentes. |
| Transformación | Python: Polars + SQL | D4 | Tratamiento analítico homogéneo en Python. |
| Calidad de datos | Great Expectations | D4 | Contratos de datos en la transición bronce→plata (RF-T04, RF-T12). |
| MLOps | XGBoost + SHAP, MLflow, Evidently | D4 | Modelos explicables con trazabilidad de versiones; consume `ah_tactico.feature_prediccion_demora`. |
| Observabilidad | Grafana (Prometheus, Loki, Tempo), PagerDuty, Slack | D5 | Alertamiento por severidad; fuente de RF-O10 y de la perspectiva de procesos del BSC. |
| CI/CD y seguridad | GitHub Actions: Ruff, bandit, trivy, Spectral | D5 | SAST, dependencias, contenedores, lint de OpenAPI (RF-T06). |
| Verificación de aislamiento | Regla de análisis estático (SQL fuera de la capa de repositorio) + suite de pruebas cruzadas por tenant | D5 | Control compensatorio obligatorio de ADR-014; sin él, el aislamiento sería solo una convención de código. |
| Escaneo de cifrado y TLS | testssl.sh integrado en GitHub Actions | D5 | Verifica RNF-S03 como puerta de release (PN-10). |
| Evidencia SOC 2 | DAG de Airflow sobre `compliance.log_auditoria` | D5 | Puebla `compliance.evidencia_soc2` sin intervención manual (RF-T11). |
| Integraciones externas | Webhook/API REST (CRM); API del proveedor PaaS (costos) | D3 / D5 | Fuentes declaradas sin replicación interna (Sección 7.5). |
| Infraestructura MVP | PaaS (frontend estático + servicios gestionados) | D5 | Time-to-market; evolución a IaC/multi-región en fase Scale (ADR-004). |
| Gestión de secretos | Vault del proveedor PaaS con rotación automática | D5 | RF-O12; sin secretos en repositorio. |

## 8.3 Lineamientos de Diseño de Interfaz Analítica (RNF-U01)

Incorporado en v6.0. El patrón de lectura aplicable no es único: depende de la densidad de
información y de la frecuencia de uso de cada tablero, conforme a los atributos de usabilidad
de ISO/IEC 25010.

| Tipo de tablero | Patrón | Fundamento |
|:---|:---|:---|
| **Estratégico** (CU-E01, CU-E02) — `ah_estrategico` | **Z** | Baja densidad (4 perspectivas del BSC, máximo 17 KPIs), audiencia de directorio con consulta esporádica y recorrido narrativo. El patrón Z opera bien en layouts dispersos con jerarquía visual fuerte y un punto terminal de cierre, donde se ubica la llamada a la acción o el KPI de síntesis. |
| **Táctico** (CU-T04, CU-T10, CU-O06) — `ah_tactico` | **F** | Alta densidad (tablas comparativas, series por aerolínea, ruta y período), audiencia analista de uso diario que escanea verticalmente el eje de métricas y luego horizontalmente el detalle del período. El patrón F es el que emerge naturalmente al leer contenido tabular denso de forma repetida. |
| **Operativo** (FIDS, torre de control) — MonetDB | Ninguno | Los tableros de monitoreo operativo se rigen por *glanceability*: posición fija e invariante por elemento. Un controlador no recorre la pantalla, verifica una posición conocida. Imponer Z o F introduciría reubicaciones que degradarían el tiempo de reacción. |

**Reglas comunes a Z y F:**

1. El KPI de mayor prioridad ocupa siempre el cuadrante superior izquierdo.
2. Las métricas semánticamente relacionadas se agrupan en cuadrantes contiguos; dispersarlas
   en extremos opuestos obliga a saltos de mirada que penalizan el uso repetido.
3. El color codifica desviación respecto a la meta, nunca la identidad de la métrica.
4. Todo KPI declara su origen (`dim_kpi.fuente_tabla`), permitiendo al usuario rastrear la
   cifra hasta el dato, en cumplimiento de la trazabilidad de la Sección 11.6.

## 8.4 Tecnologías Retiradas Respecto a Versiones Previas

| Tecnología retirada | Versión | Sustituto | Motivo |
|:---|:---|:---|:---|
| PocketBase (SQLite) como AODB | v4.0 | MonetDB | Incompatible con SLA, replicación y concurrencia declarados (ADR-001, luego ADR-013). |
| Next.js 16 (BFF) | v4.0 | API Gateway FastAPI + Angular único | Eliminación de doble framework frontend y doble runtime backend (ADR-002). |
| DuckDB en el pipeline | v4.0 | ClickHouse | Redundancia de motores analíticos (ADR-003). |
| PWA/Flutter para rampa | v4.0 | Interfaz responsiva Angular | Consolidación de frontend. |
| **PostgreSQL como base operacional** | **v5.1** | **MonetDB** | Decisión de plataforma (ADR-013). Implica la pérdida de RLS, PITR y triggers nativos, con controles compensatorios en ADR-014 y Acción 1b. |
| **MonetDB como Data Warehouse** | **v5.1** | **ClickHouse (`ah_tactico`)** | El DW migra a ClickHouse, que asume simultáneamente staging y almacén analítico (ADR-012). |
| **Esquema `analytics_bsc` en la operacional** | **v5.1** | **`ah_estrategico.kpi_snapshot`** | Los KPIs consolidados son datos analíticos; residían en la base operacional por ausencia de una capa estratégica dedicada (ADR-016). |
| **Capas Raw/Cleansed en ClickHouse** | **v5.1** | **Medallion bronce/plata/oro en disco** | El refinamiento ocurre en artefactos Parquet versionados y auditables antes de la carga; ClickHouse pasa a ser destino, no área de trabajo intermedia (ADR-015). |

---

# 9. Decisiones Arquitectónicas (ADRs)

Formato conforme a la práctica de registro de rationale exigida por ISO/IEC/IEEE 42010: contexto, decisión, alternativas evaluadas y consecuencias.

## ADR-001 — PostgreSQL como Motor de la Base Operacional (AODB) [SUPERSEDIDO por ADR-013]

> **Estado: SUPERSEDIDO en v6.0.** ADR-013 sustituye PostgreSQL por MonetDB en la capa
> operacional. Se conserva el registro porque las causas que motivaron el abandono de
> PocketBase (concurrencia, replicación, RPO) siguen vigentes y ADR-013 debe responder a
> ellas explícitamente mediante controles compensatorios, no ignorarlas.

| Campo | Contenido |
|:---|:---|
| **Contexto** | El AODB exige alta concurrencia de escritura, réplicas para failover (RTO < 15 min, RPO <= 5 min), RLS multi-tenant y esquemas con privilegios diferenciados. El motor previo (PocketBase/SQLite) no soporta replicación activa nativa ni concurrencia de escritura adecuada. |
| **Decisión** | Adoptar PostgreSQL 16+ con Row-Level Security por `tenant_id`, esquemas departamentales, réplicas streaming y backups PITR. |
| **Alternativas** | (a) Mantener PocketBase con SLA rebajado: descartada por deuda técnica estructural. (b) MySQL: RLS no nativa, políticas por vista más frágiles. |
| **Consecuencias** | Mayor esfuerzo operativo inicial (mitigado con servicio gestionado); habilita RNF-S01/S02 de forma nativa; desbloquea el SLA de OE3. |

## ADR-002 — Frontend Único Angular con API Gateway FastAPI

| Campo | Contenido |
|:---|:---|
| **Contexto** | La versión previa combinaba Next.js (BFF/SSR) y Angular (dashboards), duplicando frameworks, superficie de ataque y coste de mantenimiento para un equipo reducido. |
| **Decisión** | Angular 20+ como único frontend (portal, BI, FIDS players); las responsabilidades del BFF (sesiones, JWT, WebSockets, rate limiting) migran a un API Gateway en FastAPI. |
| **Alternativas** | (a) Mantener el dual Next.js/Angular: descartada por mantenibilidad. (b) Consolidar en Next.js: descartada por la directriz de frontend Angular y la homogeneidad backend en Python. |
| **Consecuencias** | Un solo lenguaje de backend (Python); pipeline de build único; pérdida de SSR (aceptable: aplicación interna B2B autenticada, sin requisitos SEO). |

## ADR-003 — ClickHouse como Staging y MonetDB como Data Warehouse [SUPERSEDIDO por ADR-012]

> **Estado: SUPERSEDIDO en v6.0.** ADR-012 invierte los roles: ClickHouse asume el almacén
> analítico completo en dos bases, y MonetDB pasa a la capa operacional.

| Campo | Contenido |
|:---|:---|
| **Contexto** | El ELT requiere ingesta masiva de lotes diarios y transformaciones intermedias; el consumo BI/ML requiere un esquema estrella estable. Operar dos motores columnares exige responsabilidades disjuntas. |
| **Decisión** | ClickHouse asume exclusivamente las capas Raw y Cleansed del staging (ingesta y transformación de alto volumen); MonetDB asume exclusivamente la capa Gold (DW estrella, vistas de dominio, features ML). Ningún usuario de negocio consulta staging. |
| **Alternativas** | (a) MonetDB único con staging en Parquet/Polars: menor capacidad de ingesta. (b) ClickHouse único: contradice la directriz de mantener MonetDB como capa analítica de consumo. |
| **Consecuencias** | Responsabilidad única por capa; costo de operar dos motores, acotado por el aislamiento total del staging respecto a usuarios finales. |

## ADR-004 — PaaS en Fase MVP, IaC y Multi-Región en Fase Scale

| Campo | Contenido |
|:---|:---|
| **Contexto** | El roadmap previo declaraba Kubernetes/Terraform como fortaleza vigente mientras el plan los ubicaba dos años adelante, generando inconsistencia entre vistas (ISO/IEC/IEEE 42010). |
| **Decisión** | MVP sobre PaaS gestionado con despliegue automático; Terraform (IaC) y multi-región con residencia de datos por país se ejecutan en fase Scale (acciones 27-28 del plan). |
| **Alternativas** | Kubernetes desde el MVP: descartado por coste operativo desproporcionado para el tamaño del equipo. |
| **Consecuencias** | Time-to-market acelerado; el SLA del MVP se declara en 99.9% y asciende a 99.95% al completar la fase Scale. |

## ADR-005 — Aislamiento Estructural en Operacional vs. Aislamiento Lógico en Analítica [SUPERSEDIDO por ADR-014]

> **Estado: SUPERSEDIDO en v6.0.** La premisa de esta decisión (RLS disponible en el motor
> operacional) deja de cumplirse con MonetDB. ADR-014 invierte la asimetría: el aislamiento
> estructural pasa a la capa analítica (ClickHouse, con políticas de fila) y el operacional
> se degrada a control de aplicación con verificación compensatoria.

| Campo | Contenido |
|:---|:---|
| **Contexto** | El control departamental exige límites de acceso verificables. En la base operacional (normalizada, escritura por dominio) los esquemas físicos con GRANT por rol son el mecanismo natural. En el DW, la tabla de hechos integra datos de varios departamentos por definición; fragmentarla por esquemas rompería el propósito analítico transversal y degradaría el desempeño. |
| **Decisión** | Operacional: esquemas físicos por departamento + RLS por tenant. Analítica: esquema estrella único con vistas de dominio (`v_operaciones`, `v_finanzas`) y roles de solo lectura; filtrado por tenant inyectado por la capa de servicio. |
| **Alternativas** | Esquemas departamentales también en el DW: descartada por fragmentación de hechos y JOINs inter-esquema en toda consulta. |
| **Consecuencias** | El mismo control de acceso (ISO/IEC 27002, 8.2/8.3) se implementa con el mecanismo idóneo a cada capa; ambos ejes quedan cubiertos por pruebas negativas (Sección 11). |

> **Nota v5.1:** ADR-010 extiende esta decisión con una tercera categoría de esquema
> ("interno-AeroHub", sin `tenant_id`/RLS) para `people` y `analytics_bsc`, sin contradecir
> la frontera operacional/analítica aquí establecida.

## ADR-006 — Reestructuración del Catálogo de Objetivos Estratégicos-Tácticos-Operativos

| Campo | Contenido |
|:---|:---|
| **Contexto** | La auditoría de trazabilidad (Sección 11.6) detectó objetivos huérfanos (OT10 v5.0, sin RF ni CU derivado), eslabones faltantes en la cadena OE1→OT→RF-E01→CU-T01, un objetivo estratégico (OE6) no verificable durante la fase MVP por ausencia de instrumento de medición de NPS, y un objetivo operativo (OP2 v5.0) que mezclaba dos dominios departamentales (D1-AODB y D2-Rampa), incumpliendo el eje de segregación declarado en la Sección 1.3. |
| **Decisión** | (1) Insertar matriz formal OE×OT×OP (Sección 3.4) como punto de entrada obligatorio de la cadena de trazabilidad; (2) reubicar OT10 (v5.0) al Anexo A.4 como proceso organizacional interno; (3) incorporar OT13 (expansión comercial B2B) y OT14 (FinOps y cumplimiento SOC 2), cerrando los gaps de cobertura identificados frente al BSC y al Plan de Acción; (4) diferir la meta cuantitativa de NPS de OE6 a la fase Growth, sustituyéndola por un proxy de SLA de tickets durante el MVP, respaldado por la nueva Acción 14b; (5) desdoblar OP2 (v5.0) en OP2a (D1, incidencias AODB) y OP2b (D2, incidencias de rampa), con RF-O16 como requisito funcional derivado para la incidencia de rampa, previamente sin fuente formal. |
| **Alternativas** | (a) Mantener el catálogo sin matriz formal, verificando trazabilidad de forma manual por RF: descartada por no escalar y por incumplir el criterio de trazabilidad obligatoria de la Sección 11.6. (b) Fusionar OT13/OT14 en objetivos tácticos existentes (OT2/OT5): descartada por mezclar preocupaciones de negocio, arquitectura y cumplimiento distintas, violando el principio de responsabilidad única ya aplicado en ADR-003. (c) Mantener OE6 con la meta NPS vigente desde el MVP sin instrumento de medición: descartada por dejar un objetivo estratégico declarado como no verificable durante toda la fase inicial. |
| **Consecuencias** | Renumeración de OT11→OT10, OT12→OT11 y de OP3-OP15→OP4-OP16, con actualización propagada a las Secciones 5 (RF-T y RF-O), 6 (CU) y 13 (Plan de Acción, nueva columna OT Fuente). Se incorpora un nuevo requisito funcional (RF-O16, prioridad Should) sin impacto en el alcance Must del MVP. La matriz de trazabilidad de la Sección 3.4 se convierte en el artefacto de referencia obligatorio para la incorporación de cualquier objetivo futuro. |

## ADR-007 — Cierre de Gaps de Modelo de Datos Detectados en la Auditoría Caso de Uso × Base de Datos

| Campo | Contenido |
|:---|:---|
| **Contexto** | La revisión cruzada de los 30 casos de uso contra los esquemas de la Sección 7 detectó: un caso de uso (CU-T05) catalogado bajo el departamento incorrecto (D2 en vez de D4); tres casos de uso estratégicos/tácticos (CU-E01, CU-E05, CU-E06) sin ninguna tabla de respaldo; un rol (`role_people_viewer`) definido como actor pero ausente de la matriz RBAC 4.3 y sin esquema propio; un módulo completo (M6 — Passenger Experience) sin caso de uso ni tabla; el objetivo OT14 (SOC 2) sin RF ni CU de recopilación de evidencia; y dos fuentes de datos externas (CRM comercial, consola de costos PaaS) referenciadas por RF sin mecanismo de integración documentado. |
| **Decisión** | (1) Reclasificar CU-T05 de D2 a D4; (2) incorporar los esquemas `people` y `analytics_bsc` (hosting técnico D5) con las tablas `encuesta_enps`, `empleado_metrica`, `okr_interno` y `kpi_snapshot`, y añadir `role_people_viewer` a la matriz 4.3; (3) añadir el módulo M6 al catálogo de casos de uso mediante CU-O19 y la tabla `billing.tiempo_espera_agregado`; (4) incorporar RF-T11 y CU-T11 para evidencia continua de SOC 2, con las tablas `compliance.evidencia_soc2` y `compliance.post_mortem` (esta última resolviendo también la ambigüedad de modelo de CU-O13); (5) documentar formalmente el CRM comercial y la consola de costos PaaS como fuentes de datos externas no modeladas (Sección 7.5), evitando que se interpreten como gaps no resueltos en auditorías futuras. |
| **Alternativas** | (a) Reubicar CU-E01, CU-E05 y CU-E06 al Anexo A por carecer de modelo de datos, siguiendo el precedente de OT10: descartada para CU-E01 y CU-E05 porque el BSC y los OKRs sí constituyen funcionalidad de producto consumida por `role_business_viewer` y `role_platform_admin` dentro de la plataforma, a diferencia de la capacitación semestral (proceso puramente de RRHH sin consumo por el sistema). Para CU-E06 se evaluó la misma reubicación, pero se optó por dotarlo de esquema propio (`people`) porque el BSC ya declara eNPS como KPI de primera clase (Sección 2.4.4) consumido por el mismo tablero que CU-E01, por lo que retirarlo del catálogo de producto habría dejado una perspectiva completa del BSC sin fuente. (b) Modelar el CRM comercial y los costos PaaS como tablas internas replicadas: descartada por duplicar la fuente de verdad sin necesidad funcional inmediata; se prefiere declarar la integración externa explícitamente. |
| **Consecuencias** | El catálogo de casos de uso crece a 35 entradas (se añaden CU-O19 y CU-T11, y se formaliza la especificación de CU-O13). Se incorporan dos esquemas nuevos y cinco tablas nuevas sin alterar el aislamiento tenant/departamental existente (ambos nuevos esquemas carecen de `tenant_id`, al ser de alcance interno de AeroHub). La matriz 4.3 gana dos columnas y una fila; ningún rol previamente existente pierde privilegios sobre los esquemas operacionales ya auditados (PN-01..PN-07, Sección 11.4), y se incorpora PN-08 para verificar la segregación del nuevo esquema `people`. |

## ADR-008 — Cierre de la Cadena Completa de Trazabilidad OE-OT-OP-RF-CU-Tabla

| Campo | Contenido |
|:---|:---|
| **Contexto** | La auditoría exhaustiva de la cadena descendente OE→OT→OP→RF→CU→Tabla (Sección 11.6) detectó tres requisitos funcionales sin caso de uso derivado (RF-T01, RF-T06, RF-T09) y una tabla sin requisito funcional que la justifique (`tenants.licencia`). De estos, RF-T06 y RF-T09 se confirmaron como procesos de ingeniería (CI/CD, ADRs) correctamente libres de CU y tabla por no ser funcionalidad de producto, mientras que RF-T01 (sandbox, prioridad Should) y la ausencia de control de licencias (implícito en el modelo de planes de la Sección 12.4, pero nunca declarado como RF) sí constituían gaps genuinos. |
| **Decisión** | (1) Incorporar CU-T13 (Crear Entorno Sandbox de Prueba por Tenant), cerrando RF-T01, reutilizando `tenants.tenant` con el atributo `is_sandbox` sin requerir tabla nueva; (2) incorporar RF-O18 (verificación de licencia por acceso a módulo) y CU-O20 (Validar Acceso por Licencia de Módulo Disponible), formalizando el propósito de `tenants.licencia`, previamente sin RF que lo justificara; (3) documentar explícitamente en la Sección 5.2 que RF-T06 y RF-T09 son procesos de ingeniería intencionalmente sin CU ni tabla, evitando que auditorías futuras los reporten como gaps; (4) incorporar PN-09 a la batería de pruebas negativas, verificando la denegación de acceso a módulos sin licencia vigente. |
| **Alternativas** | (a) Dejar RF-T01 sin CU por tratarse de un requisito de prioridad Should: descartada porque RF-T01 sustenta directamente el TTFV < 30 días de OE6 (Must a nivel de objetivo, aunque Should a nivel de RF individual), por lo que su ausencia de instrumentación operativa era inconsistente con la criticidad real del objetivo que sirve. (b) Omitir RF-O18 y dejar `tenants.licencia` como tabla de configuración sin verificación activa: descartada porque una tabla de control de acceso sin el requisito funcional que obligue a consultarla en cada petición no garantiza que el control se aplique, dejando un riesgo de seguridad no verificable por la Sección 11 (RNF-S02, control de privilegios). |
| **Consecuencias** | El catálogo de casos de uso alcanza 37 entradas. Se incorpora un nuevo requisito funcional Must (RF-O18) al alcance del MVP, con impacto menor en el API Gateway (una verificación adicional por petición, ya contemplada arquitectónicamente en el rate limiting de RF-T02/OT3, Sección 8.2). La cadena de trazabilidad OE-OT-OP-RF-CU-Tabla queda cerrada al 100% para todos los requisitos Must y Should; los únicos RF sin CU/tabla (RF-T06, RF-T09) están explícitamente documentados como excepción intencional, no como deuda de especificación. |

## ADR-009 — Cierre de Cobertura de Pruebas Negativas para RNF-S03/S05 y Excepción de Inmutabilidad en `post_mortem`

| Campo | Contenido |
|:---|:---|
| **Contexto** | La revisión cruzada de los Requisitos No Funcionales (Sección 5.4) contra el modelo de seguridad (10.2) y la batería de pruebas negativas (11.4) detectó que RNF-S03 (cifrado) y RNF-S05 (minimización de PII) carecían de prueba negativa dentro de la batería "obligatoria por release" pese a que las tres RNF-S restantes sí la poseían, dejando dos requisitos Must sin puerta de verificación dinámica pese a estar citados en el criterio de salida de la fase Sistema (11.5). Adicionalmente, la incorporación de `compliance.post_mortem` en ADR-007 heredó por defecto el carácter append-only del esquema `compliance`, contradiciendo su propio flujo de trabajo (CU-O13), que exige actualizar `acciones_remediacion` hasta el cierre del incidente. |
| **Decisión** | (1) Incorporar PN-10 (verificación negativa de TLS/cifrado en reposo, cerrando RNF-S03) y PN-11 (rechazo de campos nominales de pasajero en M2/M6, cerrando RNF-S05) a la Sección 11.4; (2) declarar explícitamente `post_mortem` como única excepción controlada de UPDATE dentro del esquema `compliance`, manteniendo append-only estricto en `log_auditoria`, `incidente_seguridad`, `reporte_dgac`, `acceso_auditor` y `evidencia_soc2`; (3) otorgar a `role_sre` el permiso `Up` sobre `post_mortem` exclusivamente, revocándolo implícitamente de `evidencia_soc2` (que permanece en `U,S,I`); (4) actualizar la clasificación de información (10.1) para reflejar las categorías de dato incorporadas en ADR-006/007/008. |
| **Alternativas** | (a) Mantener `post_mortem` como append-only y modelar cada actualización de remediación como una fila nueva versionada: descartada por añadir complejidad de consulta (requeriría siempre `MAX(version)` para leer el estado vigente) sin beneficio de integridad adicional, dado que la propia edición ya queda auditada vía trigger en `log_auditoria`. (b) No añadir PN-10/PN-11 y confiar en el escaneo de configuración y la revisión de modelo de datos como controles suficientes: descartada porque ambos son controles de diseño/configuración, no pruebas de release, dejando una brecha entre lo que el criterio de salida de la Sección 11.5 declara verificado (PN-01..PN-09) y lo que realmente se ejecuta en cada release. |
| **Consecuencias** | La batería de pruebas negativas crece a PN-01..PN-11, actualizándose el criterio de salida de la fase Sistema (11.5). Las cinco RNF-S transversales quedan con cobertura de prueba negativa 1:1 (S01→PN-01, S02→PN-02/03/08, S03→PN-10, S04→PN-04, S05→PN-11). `evidencia_soc2` mantiene inmutabilidad total como corresponde a evidencia de auditoría externa, mientras `post_mortem` gana la flexibilidad operativa que su caso de uso siempre exigió sin comprometer el principio de auditoría inmutable, que se preserva a nivel de `log_auditoria` como registro de cada cambio. |

## ADR-010 — Extensión de ADR-005: Esquemas de Alcance Interno (`people`, `analytics_bsc`) y Reflejo Arquitectónico de las Integraciones v5.1

| Campo | Contenido |
|:---|:---|
| **Contexto** | ADR-005 estableció una frontera binaria: esquemas operacionales con RLS por `tenant_id` en PostgreSQL, frente a esquema estrella único con vistas de dominio en MonetDB para analítica. Los esquemas `people` y `analytics_bsc`, incorporados en ADR-007, no encajan en ninguna de las dos categorías: residen en el mismo clúster PostgreSQL que los esquemas operacionales, pero carecen de `tenant_id`/RLS por ser de alcance interno de AeroHub (no de un aeropuerto tenant). La Vista General de arquitectura (8.1) y el Stack por Componente (8.2) tampoco reflejaban estos esquemas, ni el job de agregación diaria que puebla `analytics_bsc.kpi_snapshot`, ni las integraciones externas de CRM y costos PaaS documentadas en la Sección 7.5, ni la tecnología de escaneo TLS que respalda la nueva PN-10. |
| **Decisión** | (1) Reconocer formalmente una tercera categoría de esquema junto a las dos de ADR-005: **"interno-AeroHub"** — physically hosted en PostgreSQL por conveniencia operativa (mismo motor, mismo mecanismo de backup/PITR que el resto de D5), pero sin RLS por no requerir aislamiento por tenant, dado que ningún aeropuerto contratante puede acceder a estos datos bajo ningún rol (matriz 4.3); (2) actualizar la Vista General (8.1) diferenciando explícitamente "PostgreSQL — esquemas tenant-scoped" de "PostgreSQL — esquemas internal-scope"; (3) incorporar al Stack (8.2) las filas de agregación BSC, recopilación de evidencia SOC 2, integraciones externas y escaneo TLS, todas reutilizando tecnología ya adoptada (Airflow, GitHub Actions) en vez de introducir componentes nuevos. |
| **Alternativas** | (a) Migrar `people` y `analytics_bsc` a MonetDB, tratándolos como extensión del esquema analítico: descartada porque no son datos analíticos de gran volumen ni consultados vía vistas de dominio por tenants — son tablas pequeñas de configuración/agregación interna, y MonetDB está reservado por ADR-003 exclusivamente al DW estrella `dw`. (b) Crear un tercer motor de base de datos dedicado a datos internos: descartada por añadir un componente de infraestructura adicional sin justificación de volumen o patrón de acceso distinto al que PostgreSQL ya resuelve. (c) Forzar `tenant_id` nulo sobre estas tablas dentro del mismo esquema `tenants`: parcialmente adoptada para `okr_interno` (ADR-007), pero se descartó para `people`/`analytics_bsc` por mantener la segregación de propiedad funcional clara frente a un esquema (`tenants`) cuyo propósito central sí es la gestión de tenants. |
| **Consecuencias** | ADR-005 queda vigente para su alcance original (operacional vs. analítica) y se complementa, no se contradice, con esta tercera categoría. La Vista General y el Stack por Componente (8.1, 8.2) quedan sincronizados con todas las adiciones de ADR-006 a ADR-009. No se introduce infraestructura nueva: el job de agregación BSC y la recopilación de evidencia SOC 2 reutilizan Airflow (ya presente por ADR-003), y el escaneo TLS se integra a la misma tubería de GitHub Actions que ya ejecuta Ruff/bandit/trivy/Spectral. |

## ADR-011 — Sincronización del Análisis de Mercado (Sección 12) y del Plan de Acción (Sección 13) con ADR-006 a ADR-010

| Campo | Contenido |
|:---|:---|
| **Contexto** | El Plan de Acción original (32 iniciativas + Acción 14b) fue definido en v5.0 y nunca actualizado tras las cuatro rondas de auditoría posteriores: no existía iniciativa alguna que desplegara `people`/`analytics_bsc`, el job de agregación del tablero BSC (CU-E01), la validación de licencia (RF-O18/CU-O20), el sandbox (CU-T13), el escaneo TLS (PN-10) o el módulo M6 — Passenger Experience (CU-O19), pese a que todos estos componentes ya estaban formalmente especificados en el catálogo de requisitos, casos de uso y modelo de datos. Adicionalmente, el FODA (12.1) citaba las acciones "23 y 29" como plan de remediación de la debilidad D5 (ausencia de SOC 2), cuando la Acción 29 corresponde a la migración IaC (OT5), no a SOC 2; las acciones correctas son 23 y 31 (OT14). |
| **Decisión** | (1) Corregir la referencia de remediación de D5 a "acciones 23 y 31"; (2) incorporar una nueva debilidad (D6) reconociendo la dependencia del CRM comercial externo introducida por ADR-007; (3) añadir una nota de trazabilidad en el modelo de planes de suscripción (12.4) vinculando los límites por plan al mecanismo técnico RF-O18/CU-O20; (4) incorporar seis acciones al Plan (15b, 18b, 18c, 27b, 28b, 28c) usando la misma convención de numeración decimal ya establecida por la Acción 14b en v5.0, evitando renumerar las 32 acciones originales y preservando toda referencia cruzada existente a números de acción específicos en el resto del documento. |
| **Alternativas** | (a) Renumerar todas las acciones consecutivamente (1-39) para eliminar la notación decimal: descartada porque exigiría actualizar cada referencia cruzada a números de acción específicos dispersa en el documento (FODA D5, ADR-007, Sección 12.1), replicando el mismo costo de mantenimiento que motivó preservar la convención decimal usada para 14b en v5.0. (b) No añadir acciones nuevas y asumir que los componentes de ADR-006 a ADR-010 se implementarían implícitamente dentro de acciones existentes: descartada porque ninguna acción existente menciona `people`, `analytics_bsc`, RF-O18, CU-T13, PN-10 o M6, y la Sección 11.6 exige evidencia de ejecución trazable por objetivo, no una inferencia de cobertura implícita. |
| **Consecuencias** | El Plan de Acción crece a 39 iniciativas. Todo componente incorporado desde ADR-006 posee ahora una acción de implementación programada con fase, dependencia, departamento responsable, OT de origen y KPI de éxito verificable, cerrando el último eslabón de la cadena Objetivo→Requisito→Caso de Uso→Tabla→**Acción de implementación** que las auditorías previas no habían cubierto explícitamente. El documento completo (Secciones 3 a 13) queda mutuamente consistente tras cinco rondas de auditoría (ADR-006 a ADR-011). |

## ADR-012 — ClickHouse como Almacén Analítico Único, Segmentado en Dos Bases por Nivel de Objetivo

| Campo | Contenido |
|:---|:---|
| **Contexto** | ADR-003 asignaba a ClickHouse el rol de staging y a MonetDB el de Data Warehouse. La decisión de plataforma de v6.0 traslada MonetDB a la capa operacional (ADR-013), dejando la analítica sin motor. Simultáneamente, la Sección 3 distingue tres niveles de objetivo (estratégico, táctico, operativo) cuyos consumidores tienen necesidades de granularidad, latencia y horizonte temporal marcadamente distintas, servidas hasta v5.1 por un único esquema estrella. |
| **Decisión** | ClickHouse asume el almacén analítico completo, segmentado en dos bases: `ah_tactico` (hechos por vuelo y turnaround, dimensiones conformadas, features de ML) y `ah_estrategico` (KPIs consolidados del BSC y resúmenes por período). Se adopta `ReplacingMergeTree` en todas las tablas de hechos para garantizar idempotencia ante recarga, y políticas de fila (`CREATE ROW POLICY`) para preservar el aislamiento por tenant a nivel de motor en la capa analítica. |
| **Alternativas** | (a) Base analítica única con esquemas separados: descartada porque no permite otorgar privilegios de conexión diferenciados ni aplicar cuotas de recursos por nivel de consumo, y porque un analista táctico con acceso al esquema estratégico erosiona la separación de niveles que motiva ADR-016. (b) Conservar MonetDB también como DW en paralelo a su rol operacional: descartada por acoplar la carga analítica pesada al mismo motor que atiende la operación en tiempo real, comprometiendo la latencia de RF-O04. (c) Tres bases, una por nivel de objetivo incluyendo el operativo: descartada porque el nivel operativo requiere el dato transaccional vivo, no una copia analítica; su base es la operacional por definición. |
| **Consecuencias** | La Sección 7.3 se reescribe íntegramente. `analytics_bsc.kpi_snapshot` (ADR-007) migra a `ah_estrategico.kpi_snapshot`, eliminando el esquema `analytics_bsc` de la base operacional y con él una de las dos categorías "interno-AeroHub" que ADR-010 introdujo. El aislamiento analítico se refuerza respecto a v5.1 (pasa de lógico por vistas a estructural por políticas de fila), compensando parcialmente la degradación operacional de ADR-014. |

## ADR-013 — MonetDB como Motor de la Base Operacional

| Campo | Contenido |
|:---|:---|
| **Contexto** | Decisión de plataforma que sustituye a PostgreSQL (ADR-001) en la capa operacional. MonetDB es un motor columnar orientado a cargas analíticas; su adopción en un rol transaccional de alta concurrencia (cambios de estado de vuelo, asignación de puertas, registro de tareas de rampa) implica renunciar a tres capacidades sobre las que v5.1 construyó su modelo de seguridad y continuidad: Row-Level Security, replicación streaming con Point-In-Time Recovery, y triggers para la auditoría append-only. |
| **Decisión** | Adoptar MonetDB como base operacional, con tres consecuencias asumidas explícitamente y sus respectivos controles compensatorios: (1) el aislamiento multi-tenant migra a la capa de aplicación (ADR-014); (2) la auditoría de `compliance.log_auditoria` pasa a ser poblada por la capa de repositorio en vez de por triggers de base de datos, quedando su completitud sujeta a la misma verificación estática que el filtro de tenant; (3) la estrategia de continuidad (RTO < 15 min, RPO <= 5 min de RNF-R y RF-O09) debe rediseñarse sobre respaldo lógico programado y replicación a nivel de almacenamiento, dado que MonetDB no ofrece PITR equivalente — este rediseño es la Acción 1b del Plan y constituye un riesgo abierto hasta su validación por prueba de recuperación. |
| **Alternativas** | (a) Conservar PostgreSQL en la operacional y ClickHouse en la analítica, eliminando MonetDB del stack: técnicamente superior en todos los ejes evaluados (preserva RLS, PITR, triggers y reduce el stack de tres motores a dos), pero descartada por ser MonetDB una restricción de plataforma no negociable en este proyecto. Se deja constancia de esta alternativa por exigencia de ISO/IEC/IEEE 42010 sobre registro de rationale: la decisión adoptada no es la óptima en atributos de calidad, sino la impuesta por el contexto, y los controles compensatorios de ADR-014 existen precisamente para acotar esa brecha. (b) MonetDB operacional con una réplica PostgreSQL dedicada exclusivamente al enforcement de aislamiento: descartada por duplicar el estado transaccional en dos motores, introduciendo un problema de consistencia peor que el que resuelve. |
| **Consecuencias** | Se reescriben las Secciones 7.2 (modelo operacional completo), 4.3 (matriz RBAC), 5.4 (RNF-S01/S02/S04), 10.2 (modelo de aislamiento) y 11.4 (pruebas negativas PN-01 a PN-08). La fortaleza F6 del FODA y el diferenciador competitivo de la Sección 12.5 se reformulan: el aislamiento sigue siendo verificable por pruebas, pero su enforcement es de aplicación en la capa operacional y de motor en la analítica, no de motor en ambas. |

## ADR-014 — Migración del Aislamiento Multi-Tenant a la Capa de Aplicación

| Campo | Contenido |
|:---|:---|
| **Contexto** | Al perder Row-Level Security con ADR-013, el aislamiento por tenant deja de ser un control estructural —imposible de eludir desde el código de aplicación— y pasa a depender de que toda consulta incluya el filtro correspondiente. Bajo ISO/IEC 27002 8.3 esto constituye una degradación de control, no una equivalencia: un control estructural falla cerrado ante un error de programación; uno procedimental falla abierto. |
| **Decisión** | Reubicar el enforcement con cuatro controles compensatorios de aplicación obligatoria y verificación automatizada: (1) **capa de repositorio única** — ningún componente fuera de ella puede emitir SQL hacia MonetDB, concentrando el filtro de tenant en un punto auditable; (2) **inyección desde el token** — el `tenant_id` se toma siempre del JWT validado, nunca del cuerpo o de parámetros de la petición, de modo que un cliente no pueda declarar un tenant distinto al suyo; (3) **regla de análisis estático en CI** que rechaza literales SQL fuera de la capa de repositorio, convirtiendo la convención en puerta de release; (4) **suite de pruebas cruzadas por tenant** que ejecuta cada endpoint con credenciales del tenant A y afirma cero filas del tenant B, ampliada a filas canario permanentes por tenant para verificación continua. |
| **Alternativas** | (a) Confiar en revisión de código y disciplina del equipo: descartada por ser exactamente el modo de fallo que el RLS eliminaba, y por no producir evidencia verificable para la auditoría SOC 2 (OT14). (b) Interponer un proxy SQL que reescriba consultas inyectando el predicado de tenant: descartada por complejidad operativa y por trasladar el punto único de fallo a un componente de infraestructura adicional sin comunidad ni soporte maduro para MonetDB. (c) Una base de datos física por tenant: descartada por el costo operativo de administrar decenas de instancias y por romper el modelo de agregación multi-tenant que el BSC requiere. |
| **Consecuencias** | El aislamiento pasa a ser verificable por prueba en vez de garantizado por construcción. Las pruebas negativas PN-01 a PN-03 se reescriben para atacar la capa de aplicación y se añade PN-15 (SQL fuera de la capa de repositorio bloquea el build). La cobertura de la suite cruzada por tenant se incorpora como criterio de salida obligatorio de la fase Sistema (Sección 11.5). El riesgo residual —un desarrollador que añada una consulta correcta sintácticamente pero omita el filtro dentro de la propia capa de repositorio— se mitiga con la fila canario, no se elimina. |

## ADR-015 — Arquitectura Medallion con Estados de Ejecución Desacoplados de las Capas

| Campo | Contenido |
|:---|:---|
| **Contexto** | El pipeline de v5.1 transformaba datos en capas Raw/Cleansed internas a ClickHouse, sin artefactos intermedios auditables ni registro del estado de cada ejecución. La solicitud de v6.0 introduce una carpeta de datos con archivos en tres estados (crudo, procesado, terminado) y tres capas (bronce, plata, oro). Estas dos nociones son ortogonales: un archivo "procesado" no indica si reside en plata o si es un artefacto de bronce cuyo procesamiento concluyó, ambigüedad que se manifestaría como incidentes de reproceso duplicado. |
| **Decisión** | Separar formalmente ambas dimensiones. **Capa** (bronce/plata/oro) describe el grado de refinamiento y determina la ubicación en `/data`. **Estado** (`CRUDO`, `PROCESANDO`, `TERMINADO`, `RECHAZADO`) describe el punto del ciclo de la ejecución y se persiste tanto en `_manifest.json` como en `etl_control.etl_ejecucion`. Se añade la capa `/cuarentena` para artefactos rechazados, con retención de 180 días como evidencia de calidad de datos. El formato es Parquet en las tres capas, particionado por fecha y tenant. La unicidad `(run_id, capa)` en la tabla de control es el mecanismo de bloqueo de reprocesos concurrentes. |
| **Alternativas** | (a) Usar los tres estados como nombres de las tres capas (crudo=bronce, procesado=plata, terminado=oro): descartada porque impide expresar el estado de una ejecución *dentro* de una capa; sin ella, no existe forma de distinguir un archivo de oro en construcción de uno ya cargado a ClickHouse, ni de bloquear un reproceso concurrente. (b) Mantener el estado solo en Airflow (XCom / metadata de la DAG): descartada porque el estado se perdería ante purga de la metadata del orquestador, y porque no sería consultable desde el producto para el tablero de calidad de datos de CU-O21. |
| **Consecuencias** | Se incorporan el esquema `etl_control` (Sección 7.2.9), los requisitos RF-O19 y RF-T12, los casos de uso CU-O21 y CU-T14, y las pruebas negativas PN-12 y PN-14. RF-T04 se amplía de un único punto de validación a cinco transiciones verificadas. El pipeline gana reproducibilidad: cualquier carga de ClickHouse es rastreable hasta el artefacto de bronce que la originó y hasta su checksum de recepción. |

## ADR-016 — Alineación entre Nivel de Objetivo y Capa de Datos de Servicio

| Campo | Contenido |
|:---|:---|
| **Contexto** | Hasta v5.1 no existía una regla que determinara qué capa de datos sirve a cada nivel de objetivo. En la práctica, CU-E01 (tablero BSC estratégico) consultaba `analytics_bsc` en la base operacional, CU-E02 consultaba vistas del DW, y varios casos de uso tácticos accedían indistintamente a una u otra, sin criterio documentado. Esto permitía que una consulta estratégica impactara la base transaccional y que dos tableros de nivel distinto reportaran cifras divergentes del mismo indicador. |
| **Decisión** | Establecer una regla direccional explícita: los objetivos **estratégicos** (OE1-OE6) se sirven de `ah_estrategico`; los **tácticos** (OT1-OT14), de `ah_tactico`; los **operativos** (OP1-OP16), de la base operacional MonetDB. Complementariamente, `ah_estrategico` se deriva exclusivamente de `ah_tactico`, nunca por ingesta paralela desde el origen, con reconciliación de tolerancia cero como condición de publicación. Se documenta la excepción: OP1, OP2a, OP2b y OP4 operan sobre dato vivo y no pueden servirse de la capa analítica bajo ninguna circunstancia. |
| **Alternativas** | (a) Permitir que cada caso de uso elija su fuente según conveniencia de implementación: es el estado de facto de v5.1, y es precisamente lo que produjo que el tablero BSC viviera en la base operacional. (b) Ingerir `ah_estrategico` en paralelo desde el origen para reducir latencia de publicación: descartada por permitir divergencia entre el tablero estratégico y el táctico — el modo de fallo más costoso en reputación de un BSC, dado que una vez que el directorio detecta dos cifras distintas de puntualidad, la confianza en el tablero completo se pierde y no se recupera con una corrección técnica. |
| **Consecuencias** | Se incorpora la Sección 3.5 con la regla y una columna "Capa de datos" en la matriz de trazabilidad 3.4. La Sección 8.3 hereda esta separación para el diseño de interfaz: tableros estratégicos en patrón Z sobre `ah_estrategico`, tácticos en patrón F sobre `ah_tactico`, operativos sin patrón de recorrido por regirse por *glanceability*. La regla es direccional, no bidireccional: los procesos operativos escriben en MonetDB como fuente de todo el pipeline, pero ningún consumidor estratégico o táctico lee de ella. |

---

# 10. Seguridad de la Información y Privacidad

Sección alineada con ISO/IEC 27001 (sistema de gestión), ISO/IEC 27002 (controles) e ISO/IEC 27701 (privacidad/PII).

## 10.1 Clasificación de la Información

| Clase | Ejemplos | Controles Mínimos |
|:---|:---|:---|
| **Crítica Operativa** | Itinerarios, estados de vuelo, asignaciones de puerta | Disponibilidad prioritaria (SLA), RLS, réplicas, auditoría de modificaciones. |
| **Financiera** | Tarifarios, facturas, conciliaciones Pax | Acceso restringido a D3 y `role_billing_officer`; cifrado en reposo; auditoría. |
| **Auditoría y Cumplimiento** | Logs de auditoría, reportes DGAC, incidentes, evidencia SOC 2 (`evidencia_soc2`), post-mortems (`post_mortem`) | Append-only para logs/reportes/incidentes/evidencia SOC 2; excepción controlada de UPDATE solo en `post_mortem` (Sección 7.2.4); retención regulatoria; acceso nominal del auditor. |
| **Datos Personales (usuarios del sistema)** | Emails y credenciales de usuarios internos y del tenant | Minimización, hashing de credenciales, MFA, derechos ARCO del titular. |
| **Interna Corporativa** | eNPS, métricas de talento (`people.*`), OKRs internos (`tenants.okr_interno`) | Agregada y anónima; acceso exclusivo `role_people_viewer` para `people`; `role_business_viewer`/`role_platform_admin` para OKRs. |
| **Operativa Agregada Sin PII** | Tiempos de espera por terminal (`billing.tiempo_espera_agregado`, RNF-S05) | Sin campos nominales de pasajero por diseño; verificación dinámica en PN-11 (v5.1). |

## 10.2 Modelo de Doble Eje de Aislamiento (Asimétrico desde v6.0)

Hasta v5.1 ambos ejes se aplicaban estructuralmente en el motor operacional. Con la adopción
de MonetDB (ADR-013), que no implementa Row-Level Security, el modelo pasa a ser asimétrico y
debe describirse con precisión para no sobreestimar la garantía real:

| Eje | Base Operacional (MonetDB) | Capa Analítica (ClickHouse) |
|:---|:---|:---|
| **Tenant** | Control de **aplicación**: filtro inyectado desde el token por la capa de repositorio (ADR-014). Falla abierto ante error de programación; mitigado por PN-01, PN-02, PN-15 y filas canario. | Control **estructural**: políticas de fila (`CREATE ROW POLICY`) evaluadas por el motor. Falla cerrado. |
| **Departamento** | Control **estructural**: privilegios de esquema en el motor, conforme a la matriz 4.3.1. Falla cerrado. | Control **estructural**: privilegios por base y por tabla, conforme a la matriz 4.3.2. Falla cerrado. |

**Lectura correcta de esta tabla:** tres de los cuatro cuadrantes conservan enforcement de
motor. El único degradado es el eje de tenant en la capa operacional, y esa degradación es la
consecuencia directa y asumida de ADR-013. La superficie de mayor volumen de datos históricos
—la analítica, y por tanto la de mayor impacto ante una fuga— mantiene garantía estructural.

**Controles compensatorios obligatorios** (ADR-014), sin los cuales el eje de tenant operacional
carecería de garantía verificable:

1. Capa de repositorio como único emisor de SQL hacia MonetDB.
2. `tenant_id` tomado siempre del token validado, nunca del cuerpo de la petición.
3. Análisis estático en CI que rechaza SQL fuera de la capa de repositorio (PN-15).
4. Suite de pruebas cruzadas por tenant sobre el 100% de los endpoints, con filas canario
   permanentes por tenant para verificación continua.

**Riesgo residual declarado:** una consulta añadida dentro de la propia capa de repositorio que
omita el filtro de tenant no sería detectada por PN-15 (el SQL está en el lugar correcto) y
solo se detectaría por la suite cruzada si el endpoint afectado está cubierto. Este riesgo es
inherente a la migración del control al plano de aplicación y no se elimina; se acota mediante
la cobertura obligatoria del 100% de endpoints como criterio de salida (Sección 11.5).

## 10.3 Controles Aplicables (ISO/IEC 27002)

| Control | Implementación en AeroHub |
|:---|:---|
| 5.15 / 5.18 — Control y revisión de accesos | Matriz RBAC 4.3; recertificación trimestral por departamento. |
| 8.2 / 8.3 — Privilegios y restricción de acceso | Mínimo privilegio por rol; segregación de funciones inter-departamental. |
| 8.5 — Autenticación segura | MFA para internos y `role_tenant_admin`; JWT de corta vida; API Keys con scopes. |
| 8.15 — Registro de eventos | `compliance.log_auditoria` append-only poblado por triggers. |
| 8.16 — Monitoreo | Observabilidad LGTM con alertas por severidad. |
| 8.24 — Criptografía | TLS 1.2+ (objetivo 1.3) en tránsito; cifrado en reposo en MonetDB y ClickHouse; secretos en vault con rotación (RF-O12). |
| 8.25 / 8.28 — Desarrollo seguro | SAST (bandit), análisis de dependencias y contenedores (trivy), lint de código (Ruff) y de API (Spectral) en CI, bloqueando hallazgos críticos. |
| 5.24-5.26 — Gestión de incidentes | Severidades Sev1-Sev3, runbooks, post-mortems blameless en < 72h (RF-O13, OP16). |

## 10.4 Privacidad (ISO/IEC 27701)

- **Roles de tratamiento:** AeroHub actúa como Encargado del Tratamiento (Processor); cada aeropuerto tenant es Responsable (Controller). El Acuerdo de Tratamiento de Datos (DPA) forma parte del contrato marco.
- **Minimización:** los módulos operativos y el FIDS no capturan ni almacenan PII de pasajeros (RNF-S05). El componente de visión artificial para estimación de flujos, presente en versiones previas, queda retirado del alcance por implicar tratamiento biométrico de alta sensibilidad sin necesidad funcional demostrada.
- **PII gestionada:** se limita a datos de usuarios del sistema (email, identidad de acceso). Se implementan derechos del titular (acceso, rectificación, supresión lógica), plazos de retención y registro de actividades de tratamiento.
- **Transferencias y residencia:** en fase Scale, la arquitectura multi-región garantiza residencia de datos por país (Ecuador, Perú, Colombia), conforme a las leyes locales de protección de datos (LOPDP Ecuador, Ley 29733 Perú, Ley 1581 Colombia).

---

# 11. Estrategia de Verificación y Validación (ISO/IEC/IEEE 29119)

## 11.1 Niveles de Prueba

| Nivel | Alcance | Responsable | Automatización |
|:---|:---|:---|:---|
| Unitarias | Lógica de servicios FastAPI, transformaciones Polars, reglas de tarifario | Desarrollador | 100% en CI; cobertura objetivo >= 80% en módulos críticos (AODB, Billing). |
| Integración | API Gateway <-> capa de repositorio <-> MonetDB; DAGs Airflow <-> capas medallion <-> ClickHouse | Desarrollador / Data Engineer | En CI con contenedores efímeros; incluye la suite cruzada por tenant de ADR-014. |
| Sistema | Flujos extremo a extremo por caso de uso (CU-O01, CU-O17, CU-O18) | QA | Suite E2E nocturna. |
| Aceptación | Criterios de aceptación de RF por el tenant piloto | Implementación + Tenant | Checklist por RF en onboarding. |

## 11.2 Técnicas de Diseño de Pruebas por Tipo de Requisito

| Requisito | Técnica | Ejemplo de Condición de Prueba |
|:---|:---|:---|
| RF-O15 (facturación) | Partición de equivalencia y valores límite | Tarifas en los bordes de vigencia; períodos con 0 movimientos; cambio de tarifario a mitad de mes. |
| RF-O02 (asignación de puertas) | Tablas de decisión | Combinaciones de tipo de aeronave, tipo de puerta y solapamiento temporal. |
| RF-T04 (contratos de datos) | Pruebas basadas en especificación | Lotes con esquema inválido, dominios fuera de catálogo, registros duplicados y campos nulos obligatorios. |
| RF-O04 (tiempo real) | Pruebas de desempeño | Propagación de cambio de estado < 1 s bajo carga con 1000 pantallas concurrentes. |
| RF-O09 (continuidad) | Pruebas de recuperación | Restauración semanal automatizada midiendo RTO < 15 min y RPO <= 5 min; caos controlado sobre la réplica. |

## 11.3 Validación del Modelo ML

- **Partición temporal estricta:** entrenamiento sobre el tramo histórico inicial del año operativo y holdout sobre los períodos finales, prohibiendo mezclas aleatorias que induzcan fuga temporal.
- **Criterio de promoción:** MAPE <= 12% sobre el holdout; comparación obligatoria contra el modelo vigente (champion-challenger).
- **Monitoreo en producción:** drift de features y de predicciones (Evidently) con umbrales que disparan reentrenamiento anticipado (RF-T05).
- **Explicabilidad:** valores SHAP globales y locales versionados junto al modelo, como evidencia ante el tenant y el regulador.

## 11.4 Pruebas Negativas de Seguridad (Obligatorias por Release)

> **Reescritura en v6.0:** al migrar el aislamiento de tenant del motor a la capa de aplicación
> (ADR-014), PN-01 a PN-03 dejan de verificar el comportamiento del motor y pasan a atacar la
> capa de repositorio y el API Gateway. Se incorpora PN-15 como control del propio mecanismo
> compensatorio: sin él, el aislamiento sería una convención de código sin puerta de release.

| ID | Condición de Prueba | Punto de Enforcement | Resultado Esperado |
|:---|:---|:---|:---|
| PN-01 | Usuario del tenant A solicita por API un recurso identificado del tenant B (manipulación de identificador en la ruta) | Capa de repositorio | HTTP 404, no 403: no debe confirmarse la existencia del recurso ajeno. Evento registrado con el `tenant_id` del token. |
| PN-02 | Petición con `tenant_id` explícito en el cuerpo distinto al del token JWT | API Gateway | El valor del cuerpo se ignora; prevalece el del token. Discrepancia registrada y alertada como posible intento de suplantación. |
| PN-03 | Rol sin privilegio sobre un esquema departamental intenta consultarlo | Motor MonetDB (privilegios de esquema) | Denegación por el motor; el eje departamental conserva enforcement estructural aun sin RLS. |
| PN-04 | Intento de UPDATE o DELETE sobre `compliance.log_auditoria` | Motor + capa de repositorio | Denegación; la capa de repositorio no expone método de mutación para esa tabla. |
| PN-05 | Asignación de dos vuelos solapados a la misma puerta | Capa de aplicación | Rechazo por conflicto de intervalos; se propone puerta alternativa. Verificación explícita en v6.0 porque MonetDB carece de restricción de exclusión por rango. |
| PN-06 | API Key revocada o expirada invoca cualquier endpoint | API Gateway | HTTP 401; evento auditado. |
| PN-07 | Token JWT expirado o con scope insuficiente contra la API analítica | API Gateway | HTTP 401/403; sin fuga de información en el mensaje de error. |
| PN-08 | Cualquier rol distinto de `role_people_viewer`, incluido `role_platform_admin`, consulta el esquema `people` | Motor MonetDB | Denegación; segregación de datos de RRHH incluso frente al rol de mayor privilegio. |
| PN-09 | Tenant sin licencia activa para un módulo invoca su API | API Gateway (RF-O18) | HTTP 403; evento en `compliance.log_auditoria`; ningún dato del módulo se expone. |
| PN-10 | Conexión con TLS < 1.2 o cifrado en reposo deshabilitado en un servicio gestionado | Infraestructura / CI | Conexión rechazada; escaneo integrado como puerta de release (RNF-S03). |
| PN-11 | Petición a `billing.tiempo_espera_agregado` o a endpoints de M2/M6 con un campo que identifique nominalmente a un pasajero | Validación de esquema | Rechazo; el campo no tiene columna de destino en el modelo (RNF-S05). |
| PN-12 | Artefacto con contrato de datos inválido intenta promover de bronce a plata | Great Expectations / DAG | No promueve; se deriva a `/cuarentena` con informe; ejecución marcada `RECHAZADO` (RF-T12). |
| PN-13 | `role_business_viewer` consulta `ah_tactico`; `role_tenant_analyst` consulta filas de otro tenant en `ah_tactico` | ClickHouse (privilegios + política de fila) | Denegación en el primer caso; 0 filas en el segundo. Verifica la frontera entre bases analíticas y el aislamiento estructural conservado en la capa analítica. |
| PN-14 | Dos DAGs intentan procesar concurrentemente el mismo `(run_id, capa)` | MonetDB (restricción única) | La segunda ejecución es rechazada por violación de unicidad, no por convención de código (RF-O19). |
| PN-15 | Un módulo fuera de la capa de repositorio contiene un literal SQL dirigido a MonetDB | Análisis estático en CI | El build falla. Control que sustituye al RLS perdido; su ausencia invalidaría todas las garantías de PN-01 y PN-02 (ADR-014). |

## 11.5 Criterios de Entrada y Salida

| Fase | Criterio de Entrada | Criterio de Salida |
|:---|:---|:---|
| Integración | Unitarias en verde; contratos OpenAPI validados | 0 defectos críticos abiertos; contratos de datos en verde. |
| Sistema | Entorno de staging con datos sintéticos representativos y al menos dos tenants poblados | Suite E2E y PN-01..PN-15 en verde; suite de pruebas cruzadas por tenant con cobertura del 100% de los endpoints que acceden a datos de tenant (ADR-014); prueba de restauración cumpliendo RNF-R01. |
| Aceptación (onboarding) | CU-O18 completado con aislamiento verificado | Checklist de RF Must del plan contratado aprobado por el tenant. |

## 11.6 Trazabilidad

Cadena obligatoria y versionada en el repositorio: **Objetivo (OE/OT/OP) -> Requisito (RF/RNF) -> Caso de Uso (CU) -> Condición de Prueba -> Caso de Prueba -> Evidencia de Ejecución**. Ningún RF Must se declara completo sin evidencia de prueba asociada.

---

# 12. Análisis Estratégico y de Mercado

## 12.1 Análisis FODA

### Fortalezas

- **F1:** Plataforma cloud-native sobre PaaS con despliegue automatizado y observabilidad completa (LGTM), que permite implementaciones modulares rápidas con un equipo reducido.
- **F2:** Integración nativa de modelos ML explicables (SHAP) para justificar ante las aerolíneas las predicciones de demora y la planificación de recursos.
- **F3:** ERP todo-en-uno que unifica AODB, FIDS y facturación comercial, eliminando la necesidad de múltiples contratos de software.
- **F4:** Estructura organizativa Remote-First, permitiendo tarifas competitivas frente a competidores legacy.
- **F5:** Arquitectura de APIs moderna (OpenAPI 3.1, SDKs) y bien documentada para integrarse al software propio de las aerolíneas locales.
- **F6:** Modelo de aislamiento de doble eje (tenant + departamento) verificable por una batería de quince pruebas negativas ejecutadas en cada release. Desde v6.0 el enforcement es asimétrico (estructural en la capa analítica y en el eje departamental; de aplicación en el eje de tenant de la base operacional, ADR-014), por lo que la fortaleza reside en la **verificabilidad continua** del aislamiento, no en su garantía por motor en todos los cuadrantes.

### Debilidades

- **D1:** Operación de PostgreSQL a alta concurrencia en aeropuertos de gran tráfico exige tuning especializado y monitoreo continuo (mitigada por ADR-001: servicio gestionado, réplicas y pruebas de carga del plan de acción).
- **D2:** Dependencia de las fuentes externas de registros e itinerarios de vuelo provistas por cada aeropuerto y sus entes de datos.
- **D3:** Marca nueva en el sector aeroportuario LatAm, con inercia de compra hacia proveedores históricos.
- **D4:** Equipo inicial concentrado, con riesgo de sobrecarga durante onboardings simultáneos de múltiples terminales.
- **D5:** Ausencia de certificación SOC 2 en el primer año, requisito común en concesiones internacionales (plan de remediación en acciones 23 y 31; evidencia continua automatizada desde 2027 vía CU-T11/RF-T11, ADR-007).
- **D6:** Dependencia de un CRM comercial externo (Sección 7.5) para el pipeline de ventas de OT13; la visibilidad del embudo comercial no es nativa de la plataforma y requiere mantener la integración por webhook vigente. *(v5.1)*
- **D7:** El motor operacional MonetDB carece de Row-Level Security, PITR nativo y triggers, lo que traslada el aislamiento por tenant y la escritura de auditoría a la capa de aplicación y obliga a una estrategia de continuidad construida a medida (ADR-013, ADR-014; mitigación en Acción 1b y en los controles compensatorios verificados por PN-01, PN-02 y PN-15). *(v6.0)*

### Oportunidades

- **O1:** Creciente ola de concesiones privadas de aeropuertos regionales en LatAm (Ecuador, Colombia, Perú) que buscan reducir el OPEX mediante software moderno.
- **O2:** Presión de las aerolíneas por reducir el tiempo de turnaround, generando demanda de analítica operativa y predicción de demoras.
- **O3:** Vacío tecnológico en aeropuertos medianos (Manta, Loja, Cuenca) que no pueden costear sistemas tradicionales de alto valor.
- **O4:** Requisitos de reporte de eficiencia y sostenibilidad en aeropuertos bajo compromisos globales.

### Amenazas

- **A1:** Competidores tradicionales (SITA, Amadeus, Sabre) con ofertas agresivas o réplicas de capacidades predictivas.
- **A2:** Cambios repentinos en normativas de las DGAC locales que fuercen desarrollos a medida no previstos.
- **A3:** Ataques dirigidos a infraestructuras críticas nacionales (ransomware), que exigen máxima seguridad perimetral y de acceso.
- **A4:** Concentración de ingresos si el primer gran contrato supera el 50% de la facturación inicial.

## 12.2 Tamaño del Mercado (TAM / SAM / SOM)

| Dimensión | Descripción | Valor Estimado | Base de Cálculo |
|:---|:---|:---|:---|
| **TAM** | Mercado global de software y servicios de tecnología de operaciones y facturación aeroportuaria. | USD 1,200M | Aeropuertos comerciales, terminales de carga y helipuertos a nivel global. |
| **SAM** | Software operativo para aeropuertos medianos y regionales en Latinoamérica y el Caribe. | USD 180M | ~350 aeropuertos comerciales medianos e internacionales secundarios en la región. |
| **SOM** | Ingreso acumulado obtenible en los primeros 5 años con el foco comercial andino y centroamericano. | USD 8.5M | ~25 aeropuertos captados progresivamente con mix Pro/Enterprise; rampa de ARR aproximada de 0.3 / 0.9 / 1.6 / 2.4 / 3.3 millones USD en los años 1 a 5. |

La cifra de SOM se expresa como ingreso acumulado del quinquenio, consistente con el pricing de la Sección 12.4: un mix estimado de 15 tenants Pro (~USD 18k/año) y 10 Enterprise (promedio ~USD 84k/año más cobros variables Pax) sostiene la rampa declarada.

## 12.3 Segmentos de Clientes Objetivo

| Segmento | Descripción | Necesidades Clave | Modelo Comercial | Estrategia de Adquisición |
|:---|:---|:---|:---|:---|
| **Concesionarias de Aeropuertos** | Empresas privadas que administran grupos de 3 a 10 terminales. | Consolidación financiera, optimización del OPEX, reportes de cumplimiento. | Enterprise (contrato marco multiaeropuerto). | Venta directa C-Level, pilotos en terminales de bajo tráfico. |
| **Aeropuertos Internacionales Medianos** | Terminales de 1M a 5M de pasajeros anuales. | Asignación automática de puertas, FIDS de bajo costo, facturación automatizada. | Enterprise / Pro (suscripción por volumen Pax). | Demos en vivo, webinars de digitalización. |
| **Aeropuertos Regionales / Locales** | Terminales pequeños con operaciones limitadas. | AODB simplificada, FIDS básico por WebSockets. | Pro (tarifa fija baja). | Inbound marketing, eventos de aviación civil. |
| **Terminales de Carga Aérea** | Áreas de logística y almacenamiento de carga. | Monitoreo de turnaround de cargueros, control de zonas de acopio. | Pro / Personalizado. | Casos de estudio de reducción de tiempos en pista. |
| **Autoridades de Aviación Civil (DGAC)** | Reguladores estatales de seguridad y tráfico. | Dashboards nacionales, auditoría de puntualidad, control de slots. | Enterprise / Suscripción de datos. | Licitaciones públicas, alianzas de modernización. |

## 12.4 Modelo de Revenue y Planes de Suscripción

| Plan | Tarifa Base | Características | Límites | Soporte / SLA |
|:---|:---|:---|:---|:---|
| **Developer / Sandbox** | USD 0 / mes | Especificación de API del AODB, SDKs, datos de vuelos sintéticos. | 1 aeropuerto de prueba, 10,000 llamadas API/mes. | Documentación y foro; sin SLA. |
| **Pro** | USD 1,500 / mes | AODB y FIDS activos, diseñador de plantillas, 3 usuarios concurrentes de rampa. | Hasta 100 vuelos diarios, 10 pantallas FIDS. | Email/chat < 8h hábiles; Uptime 99.9%. |
| **Enterprise** | USD 3,500 a 15,000 / mes | Todo lo de Pro + Asignación de Puertas, Rampa, Facturación automatizada, Modelos ML. | Vuelos, usuarios y pantallas ilimitados. | Canal dedicado, soporte 24/7; Uptime 99.9% (MVP) / 99.95% (Scale). |
| **Pay-per-Pax (Add-on)** | USD 0.05 a 0.15 por pasajero procesado | Facturación de pasajeros y control de tasas de salida y llegada. | Pago variable según reportes verificados del tenant. | Soporte prioritario y conciliación mensual. |

**Nota v5.1:** los límites de módulos por plan (columna "Características") se hacen cumplir técnicamente mediante RF-O18 (CU-O20, Sección 5.3/6.1), que verifica `tenants.licencia` en cada acceso; el plan Developer/Sandbox es la contraparte comercial de CU-T13 (Sección 6.2).

## 12.5 Mapa Competitivo

| Competidor | Modelo de Precios | Ventajas Clave | Desventajas Clave | Diferenciador AeroHub |
|:---|:---|:---|:---|:---|
| **SITA (Airport Management)** | Muy elevado (licenciamiento + CAPEX hardware). | Marca estándar global, presencia en terminales internacionales. | Despliegues de 6 a 18 meses, contratos rígidos, interfaces obsoletas. | Despliegue cloud en < 30 días, interfaz moderna, 40-50% menor TCO. |
| **Amadeus (Airport IT)** | Licencias por terminal + mantenimiento. | Integración nativa con sistemas de reservas (GDS). | Foco en aeropuertos grandes, integraciones complejas con hardware local. | Solución modular para aeropuertos medianos, APIs abiertas. |
| **Sabre Airport Solutions** | Contratos de largo plazo, licenciamiento restrictivo. | Relaciones con aerolíneas norteamericanas. | Arquitectura legacy, soporte remoto lento en LatAm. | Soporte local en español, updates continuos, ML integrado sin costo extra. |
| **Ultra Electronics (AODB)** | Proyectos a medida de alto costo de consultoría. | Personalización para terminales en Europa y Asia. | Costos prohibitivos para medianos/pequeños en LatAm, nulo enfoque cloud. | Multitenancy nativo SaaS con facturación automatizada integrada. |

**Ventaja competitiva principal:** AeroHub es el único sistema que consolida AODB, FIDS y un motor de facturación aeroportuaria automatizado en una sola plataforma SaaS, con modelos de IA explicables (SHAP) para predecir demoras sin consultorías adicionales, y un modelo de seguridad de doble eje (tenant + departamento) cuya efectividad se demuestra ante el cliente mediante evidencia de pruebas negativas por release, no mediante declaración contractual.

---

# 13. Plan de Acción Estratégico

44 iniciativas en tres fases: MVP (2026), Growth (2027) y Scale (2028). Cada acción incluye dependencias, departamento responsable, objetivo táctico de origen (columna OT, incorporada en v5.1 para cerrar la trazabilidad de la Sección 3.4) y KPI de éxito medible. Las acciones 15b, 18b, 18c, 27b, 28b y 28c se incorporaron en v5.1 (ADR-006 a ADR-010). En v6.0 se añaden 1b, 1c, 11b, 11c y 26b, y se reescriben las acciones 1, 9, 10, 11, 26 y 28c para reflejar el cambio de motores y la arquitectura medallion (ADR-012 a ADR-016).

| # | Acción | Plazo | Dep. | Departamento | OT Fuente | KPI de Éxito |
|:---|:---|:---|:---|:---|:---|:---|
| 1 | Aprovisionar MonetDB con los esquemas departamentales normalizados (Sección 7.2) y los privilegios de la matriz 4.3.1 | Q3 2026 | — | D5 | OT6 | Esquemas creados en BCNF; PN-03, PN-04 y PN-08 en verde en el entorno base. |
| 1b | Diseñar y validar la estrategia de continuidad de MonetDB (respaldo lógico programado + replicación de almacenamiento) ante la ausencia de PITR nativo | Q3 2026 | 1 | D5 | OT5 | Prueba de restauración cumple RTO < 15 min y RPO <= 5 min (RNF-R01). **Riesgo abierto hasta su validación.** *(v6.0)* |
| 1c | Implementar la capa de repositorio como único emisor de SQL, con inyección de `tenant_id` desde el token y regla de análisis estático en CI | Q3 2026 | 1 | D5 | OT6 | PN-01, PN-02 y PN-15 en verde; 0 literales SQL fuera de la capa de repositorio (ADR-014). *(v6.0)* |
| 2 | Desarrollar portal de administración de tenants en Angular + API Gateway FastAPI | Q3 2026 | 1 | D5 / D6 | OT1 | Aprovisionamiento de tenant (CU-O18) en < 10 minutos. |
| 3 | Diseñar la API base del AODB y su especificación OpenAPI 3.1 | Q3 2026 | — | D1 / D5 | OT3 | Especificación con 0 errores de lint (Spectral) en CI. |
| 4 | Implementar el primer FIDS con WebSockets sobre el gateway (players Angular ligeros) | Q3 2026 | 3 | D1 | OT4 | Latencia de cambio en panel < 1 s (interno). |
| 5 | Desplegar infraestructura PaaS con despliegue automático de frontend y servicios | Q3 2026 | — | D5 | OT5 | Front y back en producción con deploy automático por commit. |
| 6 | Configurar CI/CD con GitHub Actions (Ruff + bandit + trivy + Spectral) | Q3 2026 | 5 | D5 | OT6 | Despliegue a staging en < 5 min por PR; bloqueo por hallazgos críticos. |
| 7 | Diseñar términos legales, DPA (Processor/Controller) y contratos aeroportuarios | Q3 2026 | — | Dirección General | — | ToS + DPA aprobados por asesoría legal. |
| 8 | Crear landing page y secuencias de marketing B2B aeroportuario | Q3 2026 | — | D3 | OT13 | Lead scoring automatizado activo en CRM. |
| 9 | Construir la DAG de ingesta diaria hacia la capa bronce, con verificación de checksum y registro en `etl_control` | Q3-Q4 2026 | 1, 3 | D4 | OT7 | DAG diaria sin pérdida de registros; toda ejecución trazable en `etl_ejecucion` (RF-O19). |
| 10 | Implementar la promoción bronce→plata con contratos de datos y derivación a cuarentena de los rechazados | Q4 2026 | 9 | D4 | OT7 | Ciclo bronce→plata con veredicto en < 15 min; PN-12 en verde (RF-T12). |
| 11 | Implementar la promoción plata→oro y la carga idempotente a `ah_tactico` en ClickHouse | Q4 2026 | 10 | D4 | OT7 | Carga incremental diaria en < 10 min; recarga del mismo período no duplica registros (`ReplacingMergeTree`). |
| 11b | Construir la base `ah_estrategico` derivada de `ah_tactico`, con reconciliación de tolerancia cero como condición de publicación | Q1 2027 | 11 | D4 | OT7 | Todo KPI estratégico reproducible desde el detalle táctico; PN-13 en verde (ADR-016). *(v6.0)* |
| 11c | Configurar las políticas de fila por tenant en ClickHouse y la segregación entre bases analíticas | Q1 2027 | 11, 11b | D5 | OT6 | PN-13 en verde; `role_business_viewer` sin acceso a `ah_tactico`. *(v6.0)* |
| 12 | Entrenar el modelo ML v1 de predicción de demoras de salida y llegada (XGBoost + SHAP) | Q4 2026 | 11 | D4 | OT8 | MAPE <= 12% en el holdout temporal. |
| 13 | Configurar la observabilidad del MVP (Grafana: Prometheus + Loki) | Q4 2026 | 5 | D5 | OT6 | Dashboards de métricas y logs activos con alertas por severidad. |
| 14 | Lanzar el piloto MVP en un aeropuerto regional de Ecuador | Q4 2026 | 2, 4, 13 | D6 | OT10, OT11 | Onboarding del primer aeropuerto en < 30 días. |
| 14b | Implementar captura manual trimestral de NPS/CSAT (formulario simple, sin automatización) en el aeropuerto piloto, como proxy de medición de OE6 durante el MVP | Q4 2026 | 14 | D6 | OT11 | Primera medición de NPS registrada antes del cierre del piloto MVP. |
| 15 | Implementar rate limiting y control de cuotas en el API Gateway | Q4 2026 | 3, 5 | D5 | OT6 | Bloqueo automático ante excesos de cuota por API Key. |
| 15b | Implementar la validación de licencia por módulo en el API Gateway (RF-O18, CU-O20) | Q4 2026 | 1, 2 | D5 | OT13 | Batería PN-09 en verde; solicitud a módulo sin licencia retorna 403 en el 100% de los casos. *(v5.1)* |
| 16 | Desarrollar el módulo de billing y facturación Pax/slots (CU-O17) | Q4 2026 | 1, 2 | D3 | OT2 | Factura mensual concilia sin diferencias con los movimientos. |
| 17 | Ejecutar pruebas de carga del FIDS simulando 1000 pantallas concurrentes | Q1 2027 | 4, 13 | D5 | OT4 | Latencia WebSocket estable < 1 s bajo carga. |
| 18 | Realizar pruebas de caos inyectando fallos en la base operacional y su réplica | Q1 2027 | 1, 5 | D5 | OT5 | Failover automático cumpliendo RTO < 15 min y RPO <= 5 min. |
| 18b | Integrar el escaneo de configuración TLS/cifrado (PN-10) al pipeline CI/CD existente | Q1 2027 | 6 | D5 | OT6 | Batería PN-10 en verde; ningún despliegue procede con protocolos o cifrados débiles activos. *(v5.1)* |
| 18c | Habilitar el aprovisionamiento de sandbox con datos sintéticos por tenant (CU-T13) | Q1 2027 | 2 | D6 | OT1 | Sandbox operativo en < 10 minutos desde la solicitud (RF-T01). *(v5.1)* |
| 19 | Iniciar experimentación A/B de precios por slots y volumen Pax | Q1-Q2 2027 | 16 | D3 | OT2 | 3 variantes de tarifario validadas con prospectos. |
| 20 | Publicar artículos técnicos sobre resiliencia FIDS y arquitectura AODB | Q1-Q2 2027 | 17 | D6 | OT4 | 2+ artículos publicados en medios de aviación civil. |
| 21 | Implementar MLOps completo: MLflow (registry) + Evidently (drift) | Q2 2027 | 12 | D4 | OT8 | Registry activo y alertas de drift configuradas. |
| 22 | Optimizar costos PaaS mediante alertas de consumo y right-sizing | Q2 2027 | 13 | D5 | OT14 | Reducción de recursos ociosos > 15%. |
| 23 | Iniciar recopilación continua de evidencias para SOC 2 Tipo II | Q2 2027 | 6, 13 | D5 | OT14 | Evidencias recolectadas de forma continua por 6 meses; formalizada como CU-T11/RF-T11 desde v5.1 (job Airflow sobre `compliance.log_auditoria`). |
| 24 | Publicar SDKs oficiales de la API del AODB en Python y TypeScript | Q2 2027 | 3 | D6 | OT3 | SDKs en PyPI y npm con documentación sincronizada. |
| 25 | Ampliar las suites de contratos de datos a todas las fuentes de cada tenant | Q2-Q3 2027 | 10 | D4 | OT7 | 100% de fuentes con contrato de datos definido. |
| 26 | Lanzar el dashboard Angular de BI auto-servicio para tenants sobre `ah_tactico`, en patrón de lectura F | Q3 2027 | 11, 11c, 13 | D4 | OT8 | Tenants generan reportes propios sin soporte; revisión de diseño conforme a RNF-U01 y Sección 8.3. |
| 26b | Implementar el tablero de calidad de datos del pipeline medallion (CU-O21) | Q3 2027 | 10, 11 | D4 | OT7 | Estado de toda ejecución y motivo de rechazo consultables por capa, tenant y fecha (RF-O19). *(v6.0)* |
| 27 | Lanzar el módulo de gestión de terminales y puertas con optimización PuLP | Q3 2027 | 1, 2 | D1 | OT5 | Asignación automática de puertas operativa (RF-O02). |
| 27b | Lanzar el módulo M6 Passenger Experience: estimación de tiempos de espera agregados por terminal (CU-O19) | Q3 2027 | 27 | D3 | — (fuente directa OE4) | Estimación visible con actualización <= 15 min; PN-11 en verde, 0 campos de PII (RF-O17). *(v5.1)* |
| 28 | Integrar encuestas automáticas de NPS y CSAT para operadores | Q3 2027 | 14 | D3 | OT11 | Tasa de respuesta > 35%. |
| 28b | Desplegar el esquema `people`, la encuesta trimestral de eNPS (CU-E06) y el módulo de OKRs internos (CU-E05, `tenants.okr_interno`) | Q3 2027 | 13 | Dirección General / D5 (hosting) | OT9 | Batería PN-08 en verde; primera encuesta eNPS y primer ciclo de OKRs registrados. *(v5.1)* |
| 28c | Construir el tablero BSC estratégico sobre `ah_estrategico.kpi_snapshot` en patrón de lectura Z (CU-E01) | Q4 2027 | 11b, 16, 28b | D3 / D4 | OT13 | KPIs de las 4 perspectivas visibles con corte <= 24h (RF-E01); diseño conforme a RNF-U01. |
| 29 | Migrar la infraestructura a IaC con Terraform (preparación multi-región) | Q4 2027 | 5, 23 | D5 | OT5 | Infraestructura completa declarada en código. |
| 30 | Desplegar arquitectura multi-región con residencia de datos por país | Q1-Q2 2028 | 29 | D5 | OT5 | Nodos activos en Ecuador, Perú y Colombia; SLA asciende a 99.95%. |
| 31 | Obtener la certificación SOC 2 Tipo II | Q2 2028 | 23 | D5 | OT14 | Auditoría externa aprobada y certificado emitido. |
| 32 | Establecer alianzas con concesionarios e integradores regionales | Q3-Q4 2028 | 26 | Dirección General | OT13 | 3 partners integrados al ecosistema. |

---

# Anexo A. Procesos Internos de Ingeniería (ISO/IEC 12207 — Procesos Organizacionales)

Los siguientes procesos pertenecen a la gestión del ciclo de vida del desarrollo y no forman parte de la funcionalidad del producto; por ello se documentan fuera del catálogo de casos de uso del sistema.

## A.1 Gestión de Sprints de Desarrollo

| Elemento | Descripción |
|:---|:---|
| **Participantes** | Todo el equipo de ingeniería; facilitación del Tech Lead. |
| **Cadencia** | Sprints quincenales con planning, dailies asíncronas (Slack) y retrospectiva. |
| **Flujo** | 1. Planning con estimación en puntos de historia según prioridades del trimestre.<br>2. Actualización diaria de progreso y bloqueos.<br>3. Evaluación del burndown y la velocidad al cierre.<br>4. Retrospectiva documentada y reprogramación de pendientes. |
| **Métricas** | Velocidad histórica, cycle time por equipo, precisión de estimación; insumo del CTO para proyectar fechas de despliegue de módulos. |

## A.2 Gestión de Post-Mortems (Complemento de CU-O13)

Cadencia y responsabilidad organizacional del proceso blameless: convocatoria del equipo de guardia, reconstrucción automática de la línea de tiempo desde la observabilidad, análisis de causa raíz (5 Porqués), creación de tickets de remediación priorizados y publicación en la base de conocimientos interna en un máximo de 72 horas (OP16).

## A.3 Gestión de Decisiones Arquitectónicas

Todo cambio estructural (motor de datos, framework, topología) exige un ADR aprobado por el owner del departamento afectado y por D5 antes de su implementación (RF-T09), preservando la trazabilidad del rationale conforme a ISO/IEC/IEEE 42010.

## A.4 Gestión de Capacitación y Desempeño (Complemento de OE5)

*Reubicado desde el catálogo de Objetivos Tácticos (OT10, v5.0) mediante ADR-006, por
corresponder a un proceso organizacional interno sin RF ni CU de producto derivado.*

| Elemento | Descripción |
|:---|:---|
| **Participantes** | Dirección de Talento y Cultura; líderes de departamento (D1-D6). |
| **Cadencia** | Evaluaciones de desempeño semestrales; capacitación continua en industria aeronáutica y MLOps. |
| **Flujo** | 1. Definición de objetivos individuales alineados a los OKRs departamentales (`tenants.okr_interno`, CU-E05).<br>2. Evaluación semestral por competencias, registrada en `people.empleado_metrica`.<br>3. Diseño e impartición de plan de capacitación derivado de las brechas identificadas. |
| **Métricas** | Tasa de Retención Anual y Time-to-Productivity (BSC, Sección 2.4.4), calculadas sobre `people.empleado_metrica`. La evaluación semestral en sí es un proceso de RRHH interno sin RF propio; la encuesta de eNPS que la complementa **sí** posee RF de producto (RF-E06, CU-E06) desde ADR-007, al estar respaldada por `people.encuesta_enps` y consumida por el mismo tablero BSC que CU-E01. *(nota corregida en la revisión de cierre v5.1)* |

---

AeroHub S.A. — Análisis Documental Estratégico · Versión 6.0 · 2026
