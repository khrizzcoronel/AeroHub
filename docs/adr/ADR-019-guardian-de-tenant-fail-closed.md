# ADR-019 — Guardián de ejecución de tenant: convertir el aislamiento operacional en *fail-closed*

| Campo | Contenido |
|:---|:---|
| **Estado** | Aceptado — **el riesgo residual permanece declarado por mandato de la SRS** |
| **Fecha** | 2026-07-30 |
| **Decide sobre** | Tratamiento del riesgo residual de aislamiento multi-tenant en la base operacional |
| **Deriva de** | AEROHUB-SRS-001 v2.0 §9.2, §9.3, §9.4, §11 · ADR-014 |
| **Requisitos relacionados** | RNF-S01, RNF-S02, PN-01, PN-02, PN-15 |

---

## Contexto

La SRS §9.2 describe el modelo de aislamiento asimétrico: de los cuatro cuadrantes (tenant × departamento) × (operacional × analítica), tres conservan enforcement de motor y **falla cerrado**; el cuadrante tenant-operacional se degradó a control de aplicación y **falla abierto**.

§9.4 acota el riesgo residual con precisión:

> Una consulta añadida dentro de la propia capa de repositorio que omita el filtro de tenant no sería detectada por el análisis estático (el SQL está en el lugar correcto) y solo se detectaría por la suite cruzada si el endpoint afectado está cubierto.

Y cierra con un mandato del que este ADR no se aparta:

> Este riesgo debe permanecer visible en toda revisión de seguridad futura y **no debe presentarse como mitigado**.

Los cuatro controles compensatorios de §9.3 son correctos pero comparten una debilidad: los tres primeros verifican **dónde** está el SQL, no **qué contiene**; el cuarto (suite cruzada al 100 % de endpoints) depende de que alguien recuerde escribir la prueba de cada endpoint nuevo. La cobertura por disciplina se degrada con el tiempo — no porque el equipo sea negligente, sino porque es una obligación repetida en un punto que crece.

El objetivo de este ADR es **cambiar la naturaleza del control**: pasar de "detectar la omisión después" a "hacer que la omisión no se pueda ejecutar".

---

## Decisión

Se incorporan cuatro mecanismos en `packages/repository`, punto único que la arquitectura ya garantiza (P1, ADR-017).

### G1 — Registro declarativo de alcance por tabla

Cada tabla declara su alcance en el metadata, derivado **literalmente** de la SRS §7.1 y del SDD-DATA-001:

```python
Table("vuelo", metadata, ..., schema="ops", info={"alcance": "tenant"})
Table("aeropuerto", metadata, ..., info={"alcance": "global"})
Table("encuesta_enps_respuesta", metadata, ..., schema="people", info={"alcance": "interno"})
```

Un test de conformidad verifica que **toda** tabla de un esquema declarado "por tenant" tenga alcance `tenant`, posea columna `tenant_id NOT NULL` y la use como primer componente de su PK o índice compuesto. Una tabla nueva sin declaración explícita **hace fallar el build** — no se asume un valor por defecto permisivo.

### G2 — Guardián en tiempo de ejecución (*fail-closed*)

Un manejador del evento `before_execute` de SQLAlchemy Core intercepta **toda** sentencia antes de enviarla al motor:

1. Recorre el árbol de la sentencia compilada e identifica las tablas involucradas.
2. Si alguna tiene alcance `tenant`, exige que la cláusula `WHERE` contenga un predicado de igualdad sobre `tenant_id` **cuyo parámetro vinculado sea exactamente el valor del contexto de la petición**.
3. Si no lo encuentra, lanza `TenantScopeViolation` y **aborta la sentencia**, registrando el intento en `compliance.log_auditoria` con severidad de incidente.

La verificación recorre el AST, no el texto del SQL: un comentario, una concatenación o un alias no la engañan. Este es el punto central del ADR — el cuadrante tenant-operacional recupera comportamiento **fail-closed**, aunque el enforcement resida en la aplicación y no en el motor.

### G3 — Contexto obligatorio y excepciones enumerables

- El `tenant_id` vive en un `ContextVar` poblado por el middleware del Gateway a partir del JWT validado. Ausencia de contexto + tabla de alcance tenant = violación.
- Los accesos legítimamente transversales (extracción de `role_elt_reader` hacia bronce, aprovisionamiento de un tenant nuevo, diagnóstico de plataforma) se declaran con un bloque explícito:

```python
with alcance_global(motivo="extraccion_bronce", rol="role_elt_reader"):
    ...
```

Cada uso escribe su propio registro en `compliance.log_auditoria`. La superficie de excepción deja de ser "cualquier método que olvide el filtro" y pasa a ser **una lista finita, nominal y auditada**, revisable en cada auditoría de accesos.

### G4 — Cobertura por construcción, no por disciplina

Un test enumera por introspección **todos** los métodos públicos de **todos** los repositorios, los invoca con datos canario del tenant A bajo contexto del tenant B, y exige 0 filas o excepción. Un método nuevo entra automáticamente al conjunto de prueba: nadie tiene que acordarse de cubrirlo.

Esto sustituye la cobertura del 100 % de endpoints *por disciplina* (§9.3, control 4) por cobertura del 100 % de métodos de acceso a datos *por construcción*. La suite cruzada por endpoint se conserva además, como verificación de extremo a extremo, junto con las filas canario permanentes por tenant.

---

## Alternativas consideradas

| Alternativa | Motivo de descarte |
|:---|:---|
| Solo los cuatro controles de §9.3 | Es la línea base; deja el riesgo tal como está descrito, dependiente de cobertura por disciplina. |
| Revisión obligatoria por pares de todo cambio en el repositorio | Control humano, no verificable ni reproducible; se degrada bajo presión de entrega. Se mantiene como práctica, no como control. |
| Vistas por tenant en MonetDB (una vista filtrada por tenant) | Multiplica objetos de base por número de tenants, rompe el aprovisionamiento en < 10 min (RNF-P04) y traslada el problema al momento de creación de la vista. |
| Volver a un motor con RLS nativo | Decisión de plataforma superior (ADR-013); fuera del alcance de este ADR. |

---

## Consecuencias

**Positivas**

- El cuadrante degradado recupera semántica *fail-closed*: una consulta sin filtro **no se ejecuta**, en lugar de ejecutarse y devolver datos ajenos.
- La cobertura de prueba deja de depender de que alguien la escriba para cada endpoint nuevo.
- Las excepciones al aislamiento son nominales y auditadas, no implícitas.
- El guardián documenta el modelo de datos: la clasificación de alcance por tabla queda expresada en código verificable, no solo en la SRS.

**Negativas y costes asumidos**

- Coste por sentencia: la inspección del AST se ejecuta en cada consulta. Debe medirse contra RNF-P01; se cachea el análisis por sentencia compilada para amortizarlo.
- Consultas analíticas legítimas con `JOIN` complejos pueden requerir ajuste para que el predicado sea reconocible por el guardián. Se acepta: preferimos un falso positivo que obliga a explicitar el filtro sobre un falso negativo que expone datos.
- Se añade un componente crítico propio que debe mantenerse y probarse.

## Riesgo residual — declarado, no mitigado

Conforme al mandato de §9.4, el riesgo **permanece abierto y visible en toda revisión de seguridad futura**. Lo que este ADR cambia es su **magnitud y su detectabilidad**, no su existencia:

| | Antes (línea base §9.3) | Después (con G1–G4) |
|:---|:---|:---|
| Superficie de fallo | Cualquier método del repositorio que omita el filtro | Un defecto en el propio guardián · una tabla mal clasificada en G1 · un uso indebido de `alcance_global` |
| Momento de detección | Ejecución en producción, o nunca si el endpoint no está cubierto | Ejecución bloqueada por el guardián · o build fallido por G1/G4 |
| Comportamiento ante omisión | Falla abierto (devuelve datos ajenos) | Falla cerrado (aborta y audita) |
| Naturaleza de la superficie | Ilimitada y creciente con el código | Finita, enumerable y auditada |

Las tres superficies residuales son **acotadas y revisables**, a diferencia de la original. Aun así, **no se declara el riesgo como mitigado ni eliminado** en ningún informe, revisión de seguridad ni criterio de salida de fase: se reporta con su magnitud reducida y su mecanismo de contención explícito.
