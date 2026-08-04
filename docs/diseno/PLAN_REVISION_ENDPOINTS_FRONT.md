# Plan de revisión: endpoints backend ↔ consumo del frontend

| Campo | Contenido |
|:---|:---|
| **Estado** | Plan — inventario hecho, revisión sin empezar |
| **Fecha del inventario** | 2026-08-04, commit `2285ced` |
| **Alcance** | Los 83 endpoints HTTP/WS de `services/*/aerohub_*/api/` frente a `apps/web` y `apps/fids-player` |
| **Origen** | `docs/estrategia/ANALISIS_RUMBO_Y_BRECHAS_2026-08.md` §1 |
| **Cifra base** | **45 endpoints con consumidor (54 %) · 38 sin consumidor (46 %)** |

Este documento hace dos cosas distintas que suelen confundirse:

- **Revisión de cobertura** — qué endpoints no tiene nadie del lado del cliente (§2, §3).
- **Revisión de integridad del contrato** — de los que **sí** están conectados, cuáles pueden estar rotos sin que nada lo detecte (§4). Esta es la parte que hoy no tiene ninguna red de seguridad y, por eso, la más urgente de las dos.

---

## 1. Hallazgo que condiciona todo el resto

**`docs/api/openapi.yaml` está desactualizado y CI valida ese archivo obsoleto.**

- El contrato publicado tiene **60 rutas**; el backend real expone **~72 rutas distintas** (83 operaciones).
- Faltan, entre otras, **todas** las rutas del workpanel construido después del 2026-08-02: `GET /usuarios`, `GET|PATCH /usuarios/{id}`, `POST /usuarios/{id}/estado`, `GET /tenants/validar`, `GET|PATCH|DELETE /tenants/{id}`, `POST /tenants/{id}/estado`, `GET /licencias/mi-tenant`, `GET /catalogo/aeropuertos`, `GET /catalogo/planes`.
- El workflow de CI corre `spectral lint docs/api/openapi.yaml --fail-severity=error`. **Pasa en verde porque el archivo es válido — no porque describa la API real.** RF-T02 (*"OpenAPI 3.1 validada automáticamente"*) está cumplido en la forma y vacío en el fondo.

Consecuencia práctica: no existe hoy ninguna fuente de verdad confiable del contrato. Cualquier revisión que se apoye en `openapi.yaml` heredará el error. Por eso la tarea R0 (§5) es regenerarlo desde FastAPI antes de revisar nada más.

---

## 2. Matriz completa de cobertura

Leyenda: **✅** consumido por el frontend · **❌** sin consumidor · **⬜** sin consumidor *por decisión documentada*

### 2.1 M1 AODB — `services/aodb` · 1 de 4

| M | Ruta | Estado | Vista consumidora / nota |
|:--|:--|:--|:--|
| WEBSOCKET | `/vuelos/ws/estado` | ✅ | `vuelos/estado-tiempo-real` |
| POST | `/vuelos` | ❌ | **No se puede crear un vuelo desde la aplicación** |
| GET | `/vuelos/{vuelo_id}` | ❌ | Sin consulta puntual de vuelo |
| POST | `/vuelos/{vuelo_id}/estados` | ❌ | **No se puede registrar un cambio de estado** — la vista los muestra pero no los produce |

### 2.2 M2 FIDS — `services/fids` · 3 de 6

| M | Ruta | Estado | Vista consumidora / nota |
|:--|:--|:--|:--|
| GET | `/fids/pantallas/{codigo}` | ✅ | `fids-player` |
| POST | `/fids/pantallas/{id}/heartbeat` | ✅ | `fids-player` |
| WEBSOCKET | `/fids/ws/pantalla/{codigo}` | ✅ | `fids-player` |
| POST | `/fids/plantillas` | ❌ | RF-T03 sin superficie |
| POST | `/fids/pantallas` | ❌ | **El player pide un código que nada en la UI crea** |
| PATCH | `/fids/pantallas/{id}/plantilla` | ❌ | Sin asignación de plantilla a pantalla |

### 2.3 M3 Gates — `services/gates` · 3 de 4

| M | Ruta | Estado | Vista consumidora / nota |
|:--|:--|:--|:--|
| GET | `/puertas/tablero` | ✅ | `puertas/tablero-puertas` |
| POST | `/puertas/asignaciones` | ✅ | `puertas/tablero-puertas` (modal) |
| POST | `/puertas/asignaciones/automatica` | ✅ | `puertas/tablero-puertas` |
| POST | `/puertas/asignaciones/{id}/cancelar` | ❌ | Endpoint huérfano en una vista que ya existe — **la brecha más barata de cerrar del proyecto** |

### 2.4 M4 Ground Ops — `services/ramp` · 6 de 6 ✅

| M | Ruta | Estado |
|:--|:--|:--|
| POST | `/rampa/turnarounds` | ✅ |
| GET | `/rampa/turnarounds` | ✅ |
| POST | `/rampa/turnarounds/{id}/tareas` | ✅ |
| GET | `/rampa/turnarounds/{id}/tareas` | ✅ |
| POST | `/rampa/tareas/{id}/finalizar` | ✅ |
| GET | `/rampa/incidencias` | ✅ |

> Único módulo con paridad completa. Sirve de referencia de "qué se siente completo".

### 2.5 M5 Billing — `services/billing` · 5 de 11

| M | Ruta | Estado | Vista consumidora / nota |
|:--|:--|:--|:--|
| POST | `/billing/facturacion/calcular` | ✅ | `billing/panel-facturas` (modal) |
| GET | `/billing/facturas` | ✅ | `billing/panel-facturas` |
| GET | `/billing/facturas/{id}` | ✅ | `billing/panel-facturas` (modal detalle) |
| POST | `/billing/facturas/{id}/emitir` | ✅ | `billing/panel-facturas` |
| POST | `/billing/facturas/{id}/disputar` | ✅ | `billing/panel-facturas` |
| POST | `/billing/tarifarios` | ❌ | **RF-T10 exige "sin despliegue de código" y hoy exige tocar la base** |
| POST | `/billing/tarifarios/{id}/conceptos` | ❌ | idem |
| POST | `/billing/tarifarios/{id}/activar` | ❌ | idem |
| POST | `/billing/conciliaciones` | ❌ | CU-O17 a medias |
| GET | `/billing/conciliaciones/{id}` | ❌ | idem |
| POST | `/billing/conciliaciones/{id}/conciliar` | ❌ | idem |

### 2.6 M6 Passenger — `services/passenger` · 0 de 2 ⬜

| M | Ruta | Estado | Nota |
|:--|:--|:--|:--|
| GET | `/passenger/tiempos-espera` | ⬜ | Decisión documentada: su consumidor natural es la pantalla pública (FIDS), no un panel administrativo |
| POST | `/passenger/tiempos-espera/recalcular` | ⬜ | Proceso de fondo |

> **Revisar la decisión**: `GET /passenger/tiempos-espera` es exactamente el dato que una plantilla FIDS querría mostrar, y `fids-player` no lo consume. La decisión de "fuera de alcance" era del *rediseño*, no del producto.

### 2.7 M9 Compliance — `services/compliance` · 0 de 11 ❌

| M | Ruta | Estado |
|:--|:--|:--|
| POST | `/compliance/incidentes` · GET `/compliance/incidentes` | ❌ |
| POST | `/compliance/post-mortems` · GET/PATCH `/compliance/post-mortems/{id}` | ❌ |
| POST | `/compliance/post-mortems/{id}/acciones` | ❌ |
| POST | `/compliance/post-mortems/{id}/acciones/{accion_id}/completar` | ❌ |
| POST | `/compliance/post-mortems/{id}/publicar` | ❌ |
| POST | `/compliance/reportes-dgac` | ❌ |
| POST | `/compliance/evidencia-soc2` | ❌ |
| POST | `/compliance/accesos-auditor` | ❌ |

> Backend completo desde S1.7 (11 endpoints), cero superficie. `role_regulatory_auditor` y `role_sre` tienen rol asignado y ninguna pantalla. **No hay razón arquitectónica — simplemente no se construyó.**

### 2.8 D6 Support — `services/support` · 0 de 11 ❌

| M | Ruta | Estado |
|:--|:--|:--|
| POST/GET | `/support/tickets` · GET `/support/tickets/{id}` | ❌ |
| PATCH | `/support/tickets/{id}/estado` | ❌ |
| POST | `/support/tickets/{id}/mensajes` | ❌ |
| POST/GET | `/support/kb/articulos` · GET `/support/kb/articulos/{id}` | ❌ |
| POST/GET | `/support/changelog` | ❌ |
| GET | `/support/observabilidad/uptime` | ❌ |

> Backend completo desde S1.8. `GET /support/observabilidad/uptime` es el único que tiene sustituto legítimo (Grafana); los otros 10 no.

### 2.9 Tenancy / Identidad — `services/tenancy` · 27 de 28

Todos consumidos salvo uno:

| M | Ruta | Estado | Nota |
|:--|:--|:--|:--|
| POST | `/auth/solicitar-verificacion` | ❌ | No hay forma de reenviar el correo de verificación desde la UI |

---

## 3. Triaje de las 38 brechas

| Clase | Qué significa | Endpoints | Acción |
|:---|:---|---:|:---|
| **A — Bloquea un caso de uso confirmado** | Hay un CU con actor humano que no puede ejecutarse | 12 | Construir vista. Prioridad P1/P2 de `ANALISIS_RUMBO_Y_BRECHAS` §3.3 |
| **B — Módulo completo sin superficie** | Backend íntegro, cero pantallas | 21 | Decisión de producto explícita: construir o declarar formalmente "solo API" |
| **C — Endpoint huérfano en vista existente** | La vista existe, solo falta el botón | 2 | Cerrar de inmediato, es trabajo de horas |
| **D — Sin consumidor por diseño** | Proceso de fondo o herramienta externa | 3 | Documentar y cerrar como no-brecha |

**Clase A (12)** — `POST /vuelos`, `GET /vuelos/{id}`, `POST /vuelos/{id}/estados`, `POST /fids/plantillas`, `POST /fids/pantallas`, `PATCH /fids/pantallas/{id}/plantilla`, los 3 de tarifarios, los 3 de conciliaciones.

**Clase C (2)** — `POST /puertas/asignaciones/{id}/cancelar`, `POST /auth/solicitar-verificacion`. Ambos son un botón en una pantalla que ya existe.

---

## 4. Revisión de integridad de los 45 endpoints que SÍ están conectados

Estar conectado no significa estar correcto. Hoy hay **cero garantías automáticas** de que el frontend y el backend hablen el mismo idioma:

| Riesgo | Situación actual | Por qué importa |
|:---|:---|:---|
| **Deriva de contrato** | **34 interfaces TypeScript escritas a mano** en los `*.service.ts`, espejando modelos Pydantic. Sin generación de código desde OpenAPI. | Si el backend renombra un campo, TypeScript **no falla** — el frontend lee `undefined` y la pantalla muestra un hueco en silencio |
| **OpenAPI obsoleto** | 60 rutas documentadas vs. ~72 reales (§1) | La única fuente de verdad del contrato no describe la API |
| **Sin test de integración front↔back** | No hay suite E2E ni contract test | Nada detecta una regresión de contrato antes de producción |
| **Precisión de ids Snowflake** | Convención documentada (siempre string en JSON) pero **verificada por revisión humana**, no por tipo ni por test | Un id emitido como número JSON se corrompe en silencio sobre `Number.MAX_SAFE_INTEGER` — el bug más caro de detectar tarde |

**Procedimiento de revisión por endpoint conectado** (checklist a aplicar a los 45):

1. **Forma**: ¿los campos que el `.service.ts` declara existen con ese nombre y tipo en el response Pydantic?
2. **Ids**: ¿todo id Snowflake viaja como `str` en el modelo de respuesta y como `string` en la interfaz TS?
3. **Errores**: ¿los códigos que el backend puede devolver (404/409/422/502) están contemplados en el `error:` del `subscribe`, o caen al mensaje genérico?
4. **Estados vacíos**: ¿la vista distingue "no hay datos" de "no cargó todavía" de "falló"?
5. **Scope**: ¿el scope que exige `requiere_scope(...)` lo tiene el rol que la vista ofrece en el menú? (esta es la clase de fallo que produjo el 500 de `role_platform_admin` en `/usuarios`)
6. **Tenant**: ¿el endpoint filtra por `contexto_tenant_id()` y la vista nunca envía `tenant_id`?

---

## 5. Plan de ejecución

### R0 — Restablecer la fuente de verdad *(bloquea todo lo demás)*

- [ ] R0.1 Regenerar `docs/api/openapi.yaml` desde el esquema real de FastAPI (`app.openapi()`), no a mano.
- [ ] R0.2 Agregar a CI un paso que **falle si el yaml comiteado difiere del generado** — convierte el lint de Spectral (hoy verde sobre un archivo obsoleto) en una compuerta real.
- [ ] R0.3 Registrar la matriz de §2 como archivo versionado y regenerable, no como una tabla escrita a mano que se desactualice igual que el yaml.

### R1 — Cerrar la Clase C *(horas, sin decisiones pendientes)*

- [ ] R1.1 Botón "Cancelar asignación" en `puertas/tablero-puertas`.
- [ ] R1.2 "Reenviar correo de verificación" en la vista de verificación.

### R2 — Revisión de integridad de los 45 conectados *(§4)*

- [ ] R2.1 Aplicar el checklist de 6 puntos, módulo por módulo, empezando por Tenancy (27 endpoints, la superficie más grande y la que más creció sin spec).
- [ ] R2.2 Evaluar generación de tipos TS desde OpenAPI para eliminar las 34 interfaces manuales. **Decisión pendiente**: adoptar codegen es infraestructura nueva y debe pasar por ADR.
- [ ] R2.3 Test de humo por endpoint conectado: una llamada real contra el gateway en Docker que verifique forma de respuesta y tipo de los ids.

### R3 — Clase A, por prioridad de `ANALISIS_RUMBO_Y_BRECHAS` §3.3

- [ ] R3.1 Vista de alta/edición de vuelos y registro de estado (M1) — desbloquea el módulo núcleo.
- [ ] R3.2 Administración de plantillas y pantallas FIDS (M2).
- [ ] R3.3 Tarifarios y conciliaciones (M5).

### R4 — Clase B, previa decisión de producto

- [ ] R4.1 Decidir explícitamente, con el propietario, si M9 Compliance y D6 Support llevan interfaz o se declaran "solo API". **No implementar sin esa decisión** — son 21 endpoints y la respuesta cambia el alcance de una fase entera.
- [ ] R4.2 Revisar si `GET /passenger/tiempos-espera` debe consumirse desde `fids-player` (§2.6).

---

## 6. Métrica de seguimiento

Una sola cifra, medida por el generador de R0.3 y revisada al cerrar cada sprint:

> **Cobertura de superficie = endpoints con consumidor / endpoints que deben tenerlo**

El denominador **excluye** la Clase D (procesos de fondo, herramientas externas) documentada endpoint por endpoint. Hoy: **45 / 80 = 56 %**.

Umbral propuesto como compuerta de fin de fase (§6.4 del plan de implementación): **ningún sprint puede cerrar dejando un endpoint de Clase A nuevo** — es decir, no se agrega backend con actor humano sin su superficie, o se registra explícitamente por qué no.

Esa regla, aplicada desde el principio, habría evitado las 12 brechas de Clase A actuales.
