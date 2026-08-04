# Análisis de rumbo y brechas — agosto 2026

| Campo | Contenido |
|:---|:---|
| **Fecha** | 2026-08-04 |
| **Fuentes cruzadas** | `docs/estrategia/AEROHUB-ANALISIS-ESTRATEGICO-v6.0.md`, `docs/PLAN_IMPLEMENTACION_v2.0.md`, `docs/srs/AEROHUB-SRS-001-v2.0.md`, código real en `services/` y `apps/` |
| **Método** | Inventario automático de los 83 endpoints reales del backend contra las 38 rutas que el frontend consume; lectura de los catálogos RF/CU frente a lo implementado |
| **Estado del repo al analizar** | commit `2285ced` (S1.14 cerrado), Fase 1 del plan completa, Fases 2-4 sin empezar |

---

## 1. Veredicto de rumbo

**El proyecto está bien encaminado en profundidad y mal balanceado en superficie.**

Lo que está sólido, y no es poco:

- La **capa de aislamiento** (Principio I, ADR-014/019) no es aspiracional: el guardián G1/G2 aborta consultas reales, y hay una batería de pruebas negativas que lo demuestra. Es la parte más difícil de un multi-tenant y está resuelta antes que la cosmética, que es el orden correcto.
- La **independencia de módulos** está verificada por `import-linter` en CI, no confiada a la disciplina. Los 9 módulos de `services/` respetan `domain`/`application`/`infrastructure`/`api`.
- La **continuidad (RNF-R01)** tiene mecanismo real y métricas publicadas, y —correctamente— **no** se declaró cerrada. Que un riesgo siga abierto con evidencia parcial es señal de honestidad del plan, no de atraso.
- La **trazabilidad** OE→OT→OP→RF→CU→sprint del v6 se sostiene: cada sprint cerrado apunta a requisitos concretos.

Lo que está desbalanceado:

> **De los 83 endpoints HTTP/WS que expone el backend, 38 (46 %) no tienen ningún consumidor en `apps/web` ni en `apps/fids-player`.**

No es un defecto de ejecución de los sprints —cada uno cumplió su DoD tal como estaba escrito—, es un **defecto de especificación del plan v2**: sus DoD se redactaron como criterios verificables por API o por test (*"factura mensual concilia sin diferencias"*, *"PN-09 en verde"*), nunca como *"el actor X puede hacer Y desde la aplicación"*. El plan se cumplió al pie de la letra y aun así quedaron casos de uso que un humano no puede ejecutar.

### 1.1 El desglose que importa

| Situación | Módulos | Endpoints sin front | Lectura |
|:---|:---|---:|:---|
| **Sin ninguna vista** | M6 Passenger, M8 Observability, M9 Compliance, D6 Support | 24 | Decisión consciente y documentada (M8 vive en Grafana; M6 se consume desde FIDS). **M9 y D6 son la excepción: no hay razón arquitectónica, solo no se construyeron.** |
| **Con vista, pero incompleta** | M1 AODB, M2 FIDS, M5 Billing, M3 Gates, Tenancy | 14 | **El hallazgo real de este análisis.** Estos módulos SÍ tienen pantalla, pero la pantalla no expone todo lo que el backend ya sabe hacer. |
| **Cobertura completa** | M4 Ground Ops | 0 | Único módulo donde front y back están a la par. |

### 1.2 Los tres casos más graves

**M1 AODB — el módulo núcleo es el más incompleto.** La vista `vuelos/estado-tiempo-real` solo consume el WebSocket. Los tres endpoints REST del módulo no tienen consumidor:

- `POST /vuelos` — no se puede dar de alta un vuelo desde la aplicación
- `GET /vuelos/{id}` — no se puede consultar un vuelo puntual
- `POST /vuelos/{id}/estados` — no se puede registrar un cambio de estado

Es decir: la pantalla **muestra** cambios de estado en vivo pero no permite **producirlos**. Todo el flujo de escritura de M1 (CU-O02, el corazón del AODB) solo es accesible por API. `role_operations_controller` tiene los scopes `vuelos:escribir` pero ninguna interfaz donde usarlos.

**M2 FIDS — se puede reproducir, no configurar.** `apps/fids-player` consume los 3 endpoints de lectura/heartbeat, pero los 3 de administración (`POST /fids/plantillas`, `POST /fids/pantallas`, `PATCH /fids/pantallas/{id}/plantilla`) no tienen vista. El player pide un código de pantalla que **nada en la interfaz puede crear**. RF-T03 (*"diseñar y publicar plantillas FIDS"*) está cumplido en backend y es inalcanzable para su actor.

**M5 Billing — RF-T10 es inoperable en la práctica.** RF-T10 promete *"variantes de tarifario aplicables por tenant **sin despliegue de código**"*. Los 3 endpoints de tarifarios existen, pero sin UI la única forma de cambiar una tarifa es un `INSERT` a mano en MonetDB — que es exactamente el "despliegue de código" que el requisito quería evitar. Los 3 endpoints de conciliación (CU-O17) están en la misma situación.

---

## 2. Informes simples y compuestos

### 2.1 El concepto no existe hoy en el proyecto

Búsqueda exhaustiva en `docs/`, `specs/` y `CLAUDE.md`: **no hay ninguna mención a informes simples ni compuestos**. Lo más cercano son tres cosas que no son informes:

| Lo que existe | Por qué NO es un informe |
|:---|:---|
| Los workpanels de lista (`tenants`, `usuarios`, `facturas`, `turnarounds`…) | Son paneles **operativos**: filtran en memoria, no tienen rango de fechas, no totalizan, no exportan, no tienen composición para impresión. Sirven para *operar*, no para *rendir cuentas*. |
| `GET /billing/facturas/{id}` (factura + líneas + total) | Es el que más se aproxima a un compuesto —une dos entidades y totaliza— pero es una **vista de detalle transaccional**, con un solo registro raíz, no un informe de un período. |
| `compliance.reporte_dgac` | **Este sí es el arquetipo correcto** de informe compuesto: período, contenido exportable, `hash_contenido` SHA-256 para integridad, append-only. Pero no tiene UI ni generalización — es un caso especial regulatorio. |

Conclusión: el proyecto tiene **paneles**, no **informes**. Son cosas distintas y hoy están conflacionadas.

### 2.2 Definición operativa que propongo adoptar

| Tipo | Definición | Pregunta que responde | Estructura |
|:---|:---|:---|:---|
| **Informe simple** | Una entidad principal, filtros explícitos (rango de fechas + 1-2 dimensiones), listado plano, exportable | *"¿Qué hay?"* | `SELECT ... FROM una_tabla WHERE filtros ORDER BY` |
| **Informe compuesto** | Dos o más entidades relacionadas, agrupación por una o más dimensiones, **subtotales por grupo y total general**, exportable | *"¿Cuánto y cómo se comporta?"* | `SELECT ... FROM a JOIN b GROUP BY dim ... ` + agregados |

La diferencia funcional real no es la cantidad de tablas: es que **el compuesto agrega y totaliza**, y por eso necesita decidir el nivel de granularidad y qué se suma. Un `JOIN` sin `GROUP BY` sigue siendo un informe simple con columnas de otra tabla.

### 2.3 Dónde deben vivir — la decisión arquitectónica que hay que tomar primero

Aquí hay una tensión real con `ADR-016` (v6 §3.5), que fija:

> *Nivel táctico (OT1-OT14) → `ah_tactico` (ClickHouse). Horizonte mensual/trimestral; **análisis comparativo** por vuelo, ruta y aerolínea.*
> *La regla **prohíbe** que un consumidor estratégico o táctico lea de la base operacional.*

Un informe compuesto es, por definición, análisis agregado. Leído literalmente, **todo informe compuesto pertenecería a ClickHouse** — que es Fase 2 y no existe todavía. Eso bloquearía los informes por meses.

Pero el propio §3.5 trae la salida, y no es un atajo:

> *"**Excepción documentada:** OP1 (aprovisionamiento), OP2a y OP2b (atención de incidencias) y **OP4 (facturación mensual)** operan sobre dato vivo y no pueden servirse desde la capa analítica bajo ninguna circunstancia, por su naturaleza transaccional."*

**Recomendación: dividir los informes por horizonte, no por complejidad de la consulta.**

| Horizonte del informe | Motor | Fase | Criterio |
|:---|:---|:---|:---|
| **Operativo** — el período en curso (hoy, este mes), necesario para *ejecutar* la operación o para emitir un documento con validez (factura, reporte DGAC) | **MonetDB**, dentro del módulo dueño | **Ahora (Fase 1.5)** | Cae bajo la excepción de §3.5 — es dato vivo transaccional, no análisis comparativo |
| **Táctico/estratégico** — comparativas multi-período, tendencias, rankings, series históricas | **ClickHouse `ah_tactico`** | **Fase 2 (S2.4)** | Es exactamente lo que §3.5 reserva a la capa analítica; construirlo en MonetDB sería violar el ADR, no interpretarlo |

Esto **respeta** ADR-016 en vez de romperlo, y desbloquea de inmediato los informes que la operación necesita para funcionar.

### 2.4 Catálogo de informes propuesto

Regla de ubicación, derivada del Principio II (independencia de módulos): **cada informe vive en el módulo dueño de su tabla raíz**. Ningún informe cruza módulos por `import`; si necesita una tabla ajena, redeclara la `Table()` localmente y re-registra su alcance G1, exactamente como ya hacen `gates` y `ramp` con `ops.vuelo`.

| Módulo | Informe simple | Informe compuesto | Motor |
|:---|:---|:---|:---|
| **M1 AODB** | Vuelos del período (filtros: fecha, aerolínea, sentido, estado) | Vuelos por aerolínea × estado, con conteo y % de puntualidad, subtotal por aerolínea | MonetDB |
| **M3 Gates** | Asignaciones del período | Ocupación por puerta × franja horaria, con % de utilización y conflictos detectados | MonetDB |
| **M4 Ground Ops** | Turnarounds del período | Turnarounds por tipo de tarea, con desviación promedio del estándar e incidencias asociadas, subtotal por severidad | MonetDB |
| **M5 Billing** | Facturas del período (por estado/aerolínea) | **Facturación por aerolínea × concepto de cargo, con subtotal por aerolínea y total general** — cierra RF-E02 en su parte operativa (OP4, excepción explícita de §3.5) | MonetDB |
| **Tenancy** | Usuarios / tenants con filtros | Tenants por plan × estado, con conteo de usuarios y licencias vigentes | MonetDB |
| **M9 Compliance** | Eventos de auditoría del período | `reporte_dgac` — **ya existe en backend**, solo necesita UI y generalización | MonetDB |
| **Táctico (Fase 2)** | — | Puntualidad por ruta y mes; demora media por aerolínea y trimestre; ingresos por tenant y período | ClickHouse |

### 2.5 Cómo implementarlos — patrón concreto, sin inventar arquitectura

Los informes **no son un módulo nuevo**. Se implementan con el patrón ya establecido, agregando una sola pieza por módulo:

```
services/<modulo>/aerohub_<modulo>/
├── application/
│   └── informes.py          # NUEVO: casos de uso de informe (parámetros -> filas + totales)
├── infrastructure/
│   └── consultas_informe.py # NUEVO: el SELECT con GROUP BY, tenant-scoped como cualquier otro
└── api/
    └── router.py            # + GET /<modulo>/informes/<nombre>
```

Reglas de diseño para que no se degraden en "otro panel más":

1. **Filtros obligatorios en el servidor, no en el cliente.** A diferencia de los workpanels actuales (que filtran en memoria sobre la lista ya cargada), un informe recibe `desde`/`hasta` y sus dimensiones como *query params* y filtra en SQL. Un informe que trae todo y filtra en el navegador no escala y no es auditable.
2. **Los totales los calcula el backend, nunca el frontend.** Si el navegador suma, dos personas con distinto filtro ven totales distintos del mismo dato y no hay forma de reconciliar. Esto es el mismo principio que §3.1 del v6 aplica al BSC ("reconciliación con tolerancia cero").
3. **Respuesta con forma explícita de informe**, no una lista plana:
   ```json
   {
     "parametros": { "desde": "...", "hasta": "...", "aerolinea_id": null },
     "generado_en": "2026-08-04T12:00:00Z",
     "grupos": [ { "clave": "AV", "filas": [...], "subtotal": {...} } ],
     "total": { "cantidad": 128, "monto": "45320.00" }
   }
   ```
   La estructura hace evidente en el contrato qué es fila, qué es subtotal y qué es total — el frontend no tiene que adivinarlo.
4. **Exportación desde el mismo endpoint** (`?formato=csv`), no un endpoint paralelo que pueda divergir del que se muestra en pantalla.
5. **Un solo primitivo visual nuevo**: `.ah-informe` (cabecera de parámetros + tabla con filas de subtotal y total diferenciadas). Reutiliza `.ah-tabla`, `.ah-panel` y `.ah-campo` que ya existen; solo agrega el tratamiento de fila-subtotal/fila-total y una composición para impresión.
6. **Auditoría**: la emisión de un informe con validez externa (facturación, DGAC) se registra en `compliance.log_auditoria`, igual que hoy hace `reporte_dgac`. Un listado interno no necesita auditarse.

### 2.6 Numeración de requisitos — advertencia

**No usar RF-O20, RF-O21 ni RF-O22.** El SRS v2.0 §Apéndice A los tiene reservados (residencia de datos, retención/archivado, validación de rol contra catálogo) y advierte explícitamente que no se reutilicen. El requisito operativo confirmado más alto es **RF-O19**.

Propongo una familia propia, que además deja claro que es una capacidad transversal y no de un módulo:

- **RF-I01** — El sistema emitirá informes simples por módulo con filtros de período y dimensión, exportables.
- **RF-I02** — El sistema emitirá informes compuestos con agrupación, subtotales y total general calculados en el servidor.
- **RF-I03** — Todo informe declarará sus parámetros y su fecha de generación en el propio artefacto.
- **RF-I04** — La emisión de informes con validez externa quedará registrada en el log de auditoría.

Esto requiere confirmación del propietario del producto antes de entrar al catálogo normativo del SRS, igual que cualquier requisito nuevo.

---

## 3. ¿Están bien planeadas las vistas?

**Parcialmente. El criterio de qué se construye está bien; el de qué NO se construye nunca se revisó.**

### 3.1 Lo que está bien

- La decisión de **no** replicar M8 Observability en Angular es correcta: Grafana ya lo hace mejor, reconstruirlo sería duplicar una herramienta madura.
- La decisión sobre **M6 Passenger** es correcta en su lógica: su consumidor natural es la pantalla pública (FIDS), no un panel administrativo.
- El sistema de diseño (S1.11-S1.14) es coherente y está aplicado de punta a punta. La consolidación en tabla + panel de búsqueda + paginación + modal es un patrón único y reconocible.

### 3.2 Lo que está mal planeado

**(a) La exclusión de M9 y D6 se heredó de un contexto que ya no aplica.** La decisión *"M6/M8/M9 quedan fuera"* se tomó en `DIRECCION_VISUAL.md` con una justificación explícita y correcta **para el rediseño**: *"crear vistas nuevas es construir funcionalidad, no rediseñar"*. Impecable en ese contexto. El problema es que esa exclusión se arrastró como si fuera una decisión de producto, y nunca se volvió a preguntar *"¿hay que construirlas?"*. M9 (post-mortems, reportes DGAC, incidentes) y D6 (tickets, KB, changelog) tienen backend completo, actores con rol asignado, y ninguna interfaz.

**(b) Se confundió "el módulo tiene vista" con "el módulo es operable".** M1 es el ejemplo: tiene vista, se rediseñó dos veces, y aun así no permite crear un vuelo. La planificación de vistas se hizo por *módulo*, cuando debía hacerse por *caso de uso* — un CU sin superficie es un CU sin entregar.

**(c) La decisión tira→tabla (2026-08-04) revirtió una decisión de diseño documentada sin actualizar su fuente.** `DIRECCION_VISUAL.md` §2.4 seguía presentando la tira como *"un solo componente estructural reutilizado en los cinco módulos"* cuando las 5 vistas ya son tablas. La decisión nueva es legítima y está registrada en `PLAN_WORKPANELS_MODULOS.md` §3.0, pero **el documento que se declara fuente de verdad estética había quedado desactualizado**. Riesgo concreto: la próxima vista construida siguiendo `DIRECCION_VISUAL.md` habría vuelto a usar tiras.

> **Corregido el 2026-08-04**: §2.4 quedó marcada como supersedida y se agregó §2.4.2 con la decisión vigente y la regla explícita para vistas futuras. **§2.2 ("densidad, no aire") NO se tocó porque sigue siendo válida** — lo que cambió es el contenedor de la densidad (fila de tabla en vez de tira), no la filosofía.

**(d) Falta la vista que el propio plan pide para Fase 2.** La Acción 26 del v6 (*"dashboard Angular de BI auto-servicio para tenants sobre `ah_tactico`, en patrón F"*) es una vista comprometida con fecha (Q3 2027) que no aparece como entregable en ningún sprint de §9. S2.4 menciona "tableros tácticos" pero sin desglose de vistas.

### 3.3 Vistas faltantes, priorizadas

| Prioridad | Vista | Módulo | Justificación |
|:---|:---|:---|:---|
| **P1** | Alta y edición de vuelos + registro de estado | M1 AODB | Desbloquea el módulo núcleo; `role_operations_controller` hoy no puede operar |
| **P1** | Administración de plantillas y pantallas FIDS | M2 | Sin esto no se puede dar de alta una pantalla; RF-T03 inalcanzable |
| **P2** | Tarifarios (alta, conceptos, activación) | M5 Billing | RF-T10 promete "sin despliegue de código" y hoy exige tocar la base |
| **P2** | Conciliación de pax | M5 Billing | CU-O17 a medias |
| **P2** | Informes (los del §2.4) | Transversal | Capacidad ausente completa |
| **P3** | Tickets, KB y changelog | D6 Support | Backend completo desde S1.8, sin superficie |
| **P3** | Post-mortems, incidentes, reportes DGAC | M9 Compliance | Backend completo desde S1.7, sin superficie |
| **P3** | Cancelar asignación de puerta | M3 Gates | Un solo endpoint huérfano en una vista que ya existe |

---

## 4. Recomendación sobre el Plan de Implementación

**Sí se justifica un v3, pero acotado — no una reescritura.**

Razones para v3 y no una enmienda a v2:

1. v2 se declara **"línea base única"** en su encabezado. Parchear una línea base sin cambiar su versión rompe justamente lo que la hace útil como referencia.
2. Los cambios no son cosméticos: agregan una fase, una familia de requisitos y corrigen el criterio de DoD de toda la Fase 1.
3. Ya hay 4 sprints (S1.11-S1.14) que se agregaron como §8.11-§8.14 sin estar en la estructura de fases original — v2 ya está de facto desactualizado.

### 4.1 Qué debería cambiar en v3

| # | Cambio | Alcance |
|:---|:---|:---|
| 1 | **Nueva Fase 1.5 — "Cierre de superficie de usuario"** entre Fase 1 y Fase 2, con los sprints de §3.3 (P1 y P2) | Sección nueva (§8-bis), ~4 sprints |
| 2 | **Corregir el criterio de DoD de la Fase 1**: agregar a la *Definition of Done* genérica (§6.5) que un CU con actor humano no está cerrado sin superficie de usuario | §6.5, ~1 párrafo |
| 3 | **Formalizar la familia RF-I** (informes) y su regla de motor por horizonte (§2.3 de este documento) | §5 nueva o anexo; requiere confirmación del propietario |
| 4 | **Incorporar S1.11-S1.14 a la estructura de fases** en vez de dejarlos como apéndices de la Fase 1 | §8, reordenamiento |
| 5 | **Desglosar las vistas de Fase 2** que hoy están implícitas (Acción 26 / patrón F) | §9.4 |
| 6 | **Registrar la matriz endpoint↔vista** como artefacto vivo del plan, con su umbral de cobertura | §6.4 (compuerta de pruebas) |

### 4.2 Qué NO debería cambiar

Las Fases 2, 3 y 4 (§9-§11) están bien construidas y no las toca este análisis: sus DoD son medibles, sus PN están mapeadas, y el tratamiento de RNF-R01 en S4.2 es correcto. Un v3 debe **conservarlas textualmente** para no introducir deriva donde no hay problema.

### 4.3 Corrección documental inmediata, independiente del v3

`DIRECCION_VISUAL.md` §2.2 y §2.4 deben reflejar la decisión tira→tabla ya tomada (punto 3.2.c). Es una corrección de una página, no depende de aprobar el v3, y sin ella el documento induce a error a la próxima vista que se construya.

---

## 5. Resumen ejecutivo

1. **Rumbo: correcto en lo difícil, incompleto en lo visible.** El aislamiento, la modularidad y la continuidad —lo que es caro de corregir tarde— están bien. Lo que falta es superficie, que es caro pero no estructural.
2. **46 % del backend no tiene consumidor.** Los casos graves no son los módulos sin vista (decisión consciente) sino los módulos **con vista incompleta**: M1 AODB no permite crear un vuelo, M2 FIDS no permite crear una pantalla, M5 no permite tocar un tarifario.
3. **Los informes no existen como concepto.** Hay paneles operativos, que son otra cosa. Se propone una definición, un catálogo de 12 informes, un patrón de implementación y una regla de motor que respeta ADR-016 en vez de romperlo.
4. **Las vistas están bien diseñadas y mal delimitadas.** El sistema visual es coherente; el criterio de qué construir se hizo por módulo cuando debía hacerse por caso de uso.
5. **Se recomienda v3 acotado**: agrega Fase 1.5, corrige el DoD genérico, formaliza RF-I, conserva Fases 2-4 intactas.
