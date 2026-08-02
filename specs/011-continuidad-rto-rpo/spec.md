# Feature Specification: Continuidad operacional (RTO/RPO)

**Feature Branch**: `main`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Sprint S1.9 del docs/PLAN_IMPLEMENTACION_v2.0.md §8.9: Continuidad operacional (ADR-018). Objetivo: construir el mecanismo completo de RTO/RPO y ponerlo a medir -- sprint dedicado, el riesgo mayor del proyecto. Accion fuente: 1b (ADR-018). Requisitos: RNF-R01, RF-O09, OP7. Entregables: C1 continuidad.journal_mutacion con lsn monotono y checksum_sha256 (YA EXISTE desde S0.2 -- este sprint agrega retencion/purga si falta); C2 hot_snapshot cada 6h + volcado logico diario hacia MinIO/S3, catalogo de snapshots con su lsn de corte, verificacion de integridad por checksum; C3 standby caliente restaurado desde snapshot, shipper idempotente que drena por lsn y registra el ultimo aplicado, metrica aerohub_standby_lag_seconds en Prometheus con alerta a 120s; C4 failover por cambio de DSN en la capa de repositorio, prueba de restauracion semanal automatizada publicando rpo_observado_segundos y rto_observado_segundos, runbook de conmutacion. DoD: el mecanismo opera y publica sus metricas -- RNF-R01 NO se declara cerrado en este sprint (requiere 4 semanas consecutivas en verde + 1 game day en S4.2), se reporta como riesgo abierto con mecanismo y metrica."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Punto de partida recuperable siempre disponible (Priority: P1)

Un responsable de plataforma necesita, en cualquier momento, un respaldo base reciente y verificado desde el cual reconstruir la base de datos operacional si el sistema primario se pierde por completo, sin depender de que alguien recuerde generarlo a mano.

**Why this priority**: Es el punto de partida de todo el mecanismo de continuidad -- sin un respaldo base confiable y catalogado, no hay desde dónde restaurar ni desde dónde arrancar una réplica caliente (User Story 2).

**Independent Test**: Puede probarse íntegramente esperando a que corra el ciclo programado y verificando que aparece un respaldo nuevo, catalogado con su punto de corte y su verificación de integridad en verde -- sin depender de que exista todavía una réplica caliente o un mecanismo de conmutación.

**Acceptance Scenarios**:

1. **Given** el sistema en operación normal, **When** transcurre el intervalo programado, **Then** se genera un respaldo base nuevo y queda registrado en un catálogo consultable junto con su punto de corte y el resultado de su verificación de integridad.
2. **Given** un respaldo recién generado, **When** se verifica su integridad, **Then** el sistema detecta y marca como no confiable cualquier respaldo corrupto o incompleto antes de que alguien intente usarlo para restaurar.
3. **Given** el respaldo base programado, **When** también corre el volcado lógico diario independiente, **Then** ambos quedan catalogados por separado, cada uno con su propio punto de corte.

---

### User Story 2 - Réplica caliente con atraso siempre visible (Priority: P1)

Un ingeniero de guardia necesita saber, en todo momento y sin tener que investigar, cuánto tiempo de datos separa a la réplica de respaldo del sistema primario, para decidir con confianza si puede conmutar hacia ella sin perder más de lo tolerable.

**Why this priority**: Es el componente que realmente determina el objetivo de punto de recuperación (RPO) -- sin una réplica que se mantenga al día y sin visibilidad de su atraso, la conmutación (User Story 3) sería una apuesta a ciegas.

**Independent Test**: Puede probarse de forma aislada aplicando cambios sintéticos al primario y verificando que la réplica los recibe en el mismo orden, que reaplicar un cambio ya recibido no produce ningún efecto adicional, y que el atraso observado se publica de forma continua -- sin necesidad de ejecutar una conmutación real.

**Acceptance Scenarios**:

1. **Given** una réplica de respaldo restaurada desde el último punto de partida verificado, **When** ocurren mutaciones nuevas en el primario, **Then** la réplica las recibe en el mismo orden en que ocurrieron, sin saltos.
2. **Given** un cambio que ya fue recibido y aplicado por la réplica, **When** ese mismo cambio se reintenta (p. ej. tras una interrupción), **Then** no produce ningún efecto adicional ni un error.
3. **Given** la réplica en operación continua, **When** un responsable de guardia consulta su estado, **Then** ve el atraso actual respecto al primario, sin necesidad de pedir el dato a Ingeniería.
4. **Given** un atraso que cruza el umbral de alerta, **When** eso ocurre, **Then** el responsable de guardia recibe una alerta antes de que el atraso se convierta en un incumplimiento del objetivo de recuperación.

---

### User Story 3 - Conmutación desde un único punto (Priority: P1)

Cuando el sistema primario falla, un responsable de plataforma puede redirigir todo el tráfico de la aplicación hacia la réplica de respaldo cambiando un único punto de configuración, sin coordinar cambios manuales en varios servicios ni arriesgarse a que una parte de la aplicación quede hablando con el primario caído y otra con la réplica.

**Why this priority**: Es el mecanismo de contención ante el fallo real -- sin él, un respaldo verificado (User Story 1) y una réplica al día (User Story 2) no se traducen en continuidad real del servicio.

**Independent Test**: Puede probarse en un escenario simulado deteniendo el acceso al primario, ejecutando el procedimiento de conmutación documentado, y verificando que toda la aplicación queda sirviendo desde la réplica sin que ninguna parte quede apuntando al sistema anterior.

**Acceptance Scenarios**:

1. **Given** un fallo confirmado del sistema primario, **When** un responsable de plataforma ejecuta la conmutación, **Then** toda la aplicación queda sirviendo desde la réplica de respaldo mediante el cambio de un único punto de configuración.
2. **Given** una conmutación en curso, **When** se completa, **Then** ninguna parte de la aplicación queda escribiendo o leyendo del sistema primario original.
3. **Given** el procedimiento de conmutación documentado, **When** lo sigue una persona distinta a quien lo diseñó, **Then** puede ejecutarlo sin necesitar contexto adicional no escrito.

---

### User Story 4 - Evidencia semanal automática de recuperación real (Priority: P2)

Un responsable de continuidad/cumplimiento necesita evidencia recurrente y objetiva -- no una promesa de diseño -- de que el mecanismo completo (respaldo, réplica, conmutación) realmente restaura el servicio dentro de los tiempos exigidos, generada sola cada semana sin que nadie tenga que acordarse de probarlo.

**Why this priority**: Es la capa de verificación continua que sostiene la credibilidad de las tres historias anteriores en el tiempo -- depende de que existan (User Stories 1-3), por eso es P2 y no P1.

**Independent Test**: Puede probarse dejando correr el ciclo semanal automatizado sobre datos sintéticos y verificando que produce, sin intervención humana, un resultado con el tiempo de recuperación observado y la ventana de pérdida de datos observada de esa ejecución.

**Acceptance Scenarios**:

1. **Given** el ciclo semanal programado, **When** se ejecuta, **Then** restaura el servicio sobre datos sintéticos y mide, sin intervención manual, el tiempo real de recuperación y la ventana real de pérdida de datos de esa corrida.
2. **Given** una ejecución ya completada, **When** un responsable de continuidad la consulta, **Then** encuentra el resultado publicado como evidencia consultable (no solo un "aprobado/rechazado"), incluyendo ambas métricas observadas.
3. **Given** varias ejecuciones semanales acumuladas, **When** se revisan en conjunto, **Then** permiten distinguir una tendencia sostenida de una mejora puntual aislada.

---

### User Story 5 - El registro de cambios no crece sin límite (Priority: P3)

Un responsable de plataforma necesita que el registro continuo de cambios se depure automáticamente pasada su ventana de utilidad, sin intervención manual y sin arriesgarse a borrar un cambio que la réplica de respaldo todavía no haya recibido.

**Why this priority**: Es una tarea de higiene operativa sobre un componente que ya existe -- no bloquea el resto del mecanismo, pero sin ella el registro crecería indefinidamente.

**Independent Test**: Puede probarse de forma aislada generando cambios sintéticos, esperando a que se cumpla la ventana de retención, y verificando que las entradas más antiguas que esa ventana desaparecen automáticamente -- excepto que la réplica de respaldo ya las haya procesado, en cuyo caso su ausencia no afecta a nada corriente.

**Acceptance Scenarios**:

1. **Given** entradas del registro más antiguas que la ventana de retención definida, **When** se cumple esa ventana, **Then** se eliminan automáticamente sin intervención manual.
2. **Given** una entrada dentro de la ventana de retención que la réplica de respaldo todavía no procesó, **When** se evalúa la depuración, **Then** esa entrada NO se elimina hasta que la réplica confirme haberla aplicado.

---

### Edge Cases

- ¿Qué pasa si el proceso que aplica cambios a la réplica se interrumpe a mitad de un lote? Debe reanudar exactamente donde quedó, sin duplicar ni saltar entradas (User Story 2).
- ¿Qué pasa si se detecta que un respaldo recién generado está corrupto o incompleto justo cuando se necesita para restaurar? Debe quedar marcado como no confiable desde su propia verificación, no descubrirse recién al intentar usarlo.
- ¿Qué pasa si se aplica un cambio de esquema (una migración) mientras la réplica está desincronizada? La migración debe aplicarse a ambos sistemas por el mismo procedimiento versionado; una migración aplicada solo al primario es una divergencia silenciosa que el mecanismo debe impedir, no solo detectar después.
- ¿Qué pasa si el sistema primario original vuelve a estar disponible después de una conmutación? El procedimiento debe dejar explícito si corresponde una reconmutación o si la réplica pasa a ser el nuevo sistema de referencia -- no queda ambiguo para quien ejecuta el runbook.
- ¿Qué pasa si la ventana de retención del registro de cambios se cumple para entradas que la réplica todavía no procesó (por ejemplo, por una interrupción prolongada del proceso de réplica)? La purga debe ceder ante la replicación pendiente, nunca al revés.
- ¿Qué pasa si dos ciclos de respaldo se solapan en el tiempo (el programado cada pocas horas y el volcado diario)? Ambos deben completarse y catalogarse de forma independiente, sin que uno interfiera con el otro.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST generar un respaldo base completo de forma recurrente y automática, sin intervención manual.
- **FR-002**: El sistema MUST generar además un volcado lógico completo diario, independiente del formato interno del respaldo base, como respaldo de último recurso.
- **FR-003**: El sistema MUST mantener un catálogo consultable de cada respaldo generado, registrando su punto de corte y el resultado de su verificación de integridad.
- **FR-004**: El sistema MUST verificar la integridad de cada respaldo generado y marcar como no confiable cualquiera que resulte corrupto o incompleto, antes de que se intente usar para restaurar.
- **FR-005**: El sistema MUST mantener una réplica de respaldo restaurada a partir del último respaldo verificado disponible.
- **FR-006**: El sistema MUST aplicar sobre la réplica de respaldo, en el mismo orden en que ocurrieron, todos los cambios registrados en el registro continuo de cambios.
- **FR-007**: El sistema MUST hacer que reaplicar un cambio ya aplicado sobre la réplica no produzca ningún efecto adicional ni un error (idempotencia).
- **FR-008**: El sistema MUST registrar de forma durable cuál fue el último cambio aplicado con éxito sobre la réplica, de modo que el proceso de aplicación pueda reanudar tras una interrupción sin reprocesar ni saltar entradas.
- **FR-009**: El sistema MUST publicar de forma continua el atraso actual de la réplica de respaldo respecto al sistema primario.
- **FR-010**: El sistema MUST emitir una alerta cuando el atraso de la réplica supere un umbral definido, antes de que ese atraso constituya un incumplimiento del objetivo de recuperación.
- **FR-011**: El sistema MUST permitir redirigir todo el tráfico de la aplicación hacia la réplica de respaldo mediante el cambio de un único punto de configuración.
- **FR-012**: El sistema MUST contar con un procedimiento de conmutación documentado y ejecutable por una persona distinta a quien lo diseñó, sin necesitar contexto adicional no escrito.
- **FR-013**: El sistema MUST ejecutar, de forma automática y recurrente (semanal), una prueba de restauración completa sobre datos sintéticos.
- **FR-014**: El sistema MUST medir y publicar, de cada prueba de restauración, el tiempo real de recuperación observado y la ventana real de pérdida de datos observada -- no solo un resultado binario de aprobado/rechazado.
- **FR-015**: El sistema MUST depurar automáticamente las entradas del registro continuo de cambios más antiguas que su ventana de retención definida, sin intervención manual.
- **FR-016**: El sistema MUST impedir que se depure una entrada del registro de cambios que la réplica de respaldo todavía no haya aplicado, sin importar su antigüedad.
- **FR-017**: Toda migración de esquema MUST aplicarse al sistema primario y a la réplica de respaldo mediante el mismo procedimiento versionado, verificado automáticamente antes de aceptar el cambio.
- **FR-018**: El sistema MUST hacer visible el estado del mecanismo completo (último respaldo verificado, atraso de réplica, resultado de la última prueba de restauración) sin que un responsable de continuidad tenga que solicitar el dato a Ingeniería.

### Key Entities *(include if feature involves data)*

- **RespaldoBase**: un respaldo catalogado del sistema operacional; punto de corte, momento de generación, resultado de verificación de integridad, tipo (programado recurrente o volcado lógico diario).
- **EstadoReplica**: posición de aplicación de la réplica de respaldo respecto al registro continuo de cambios; último cambio aplicado, atraso observado respecto al primario.
- **PruebaRestauracion**: una ejecución del ciclo semanal automatizado de restauración; momento de ejecución, tiempo de recuperación observado, ventana de pérdida de datos observada, resultado.
- **RegistroDeCambios (existente)**: el flujo continuo y ordenado de cambios ya capturado por el mecanismo de continuidad desde un sprint anterior; este sprint le agrega ventana de retención con purga automática condicionada al avance de la réplica.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En todo momento existe un respaldo base verificado con una antigüedad máxima igual al intervalo programado entre respaldos.
- **SC-002**: El atraso de la réplica de respaldo respecto al sistema primario es consultable en todo momento y, en operación normal, se mantiene por debajo del umbral de alerta definido.
- **SC-003**: Un responsable de plataforma puede completar la conmutación hacia la réplica de respaldo en menos de 3 minutos desde que decide iniciarla, sin coordinar cambios en más de un punto de configuración.
- **SC-004**: Cada semana, sin intervención manual, se produce una prueba de restauración con su tiempo de recuperación y su ventana de pérdida de datos observados, publicados como evidencia consultable.
- **SC-005**: Reaplicar un cambio ya replicado nunca produce un resultado distinto ni un error visible para el resto del sistema.
- **SC-006**: Ningún cambio queda sin registrar en el flujo continuo de cambios como consecuencia de la mutación de negocio que lo originó -- se confirman ambos juntos o ninguno.
- **SC-007**: El costo adicional de tiempo de respuesta introducido por la captura continua de cambios no degrada de forma perceptible los tiempos de propagación de estado ya comprometidos en sprints anteriores.
- **SC-008**: Un responsable de continuidad puede determinar, en cualquier momento y sin reconstruir el estado a mano, si el mecanismo completo (respaldo, réplica, conmutación, prueba semanal) está operando dentro de los objetivos de recuperación definidos.

## Assumptions

- El "game day" mensual con conmutación real sobre datos sintéticos y la ventana de observación de cuatro semanas consecutivas en verde son actividades operativas posteriores a este sprint (Fase 4 del plan de implementación); este sprint construye el mecanismo completo y lo pone a medir, pero no declara cerrado el riesgo de continuidad operacional -- se reporta como riesgo abierto con mecanismo y métrica, tal como exige la fuente normativa.
- Los datos usados en la prueba de restauración semanal automatizada son sintéticos, no datos reales de ningún tenant.
- El almacenamiento de objetos replicado donde se alojan los respaldos y el registro de cambios ya está desplegado y disponible; este sprint no construye esa infraestructura de almacenamiento, solo la usa.
- La conmutación hacia la réplica de respaldo es iniciada por una persona responsable (con verificación humana de que el fallo es real), no un mecanismo completamente automático sin supervisión.
- El mecanismo cubre la base de datos operacional del sistema; no cubre la continuidad de otros almacenes de datos del proyecto fuera del alcance declarado.
- El umbral de alerta sobre el atraso de la réplica se fija en un valor sensiblemente menor al objetivo de pérdida de datos tolerado, para que la degradación sea visible antes de convertirse en incumplimiento.
- La ventana de retención del registro continuo de cambios es la ya establecida desde su creación (48 horas); este sprint agrega la purga automática que la hace cumplir, no redefine su duración.
