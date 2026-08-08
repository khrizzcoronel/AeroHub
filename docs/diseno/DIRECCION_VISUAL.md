# Dirección visual de AeroHub

| Campo | Contenido |
|:---|:---|
| **Estado** | Aprobado — 2026-08-02 |
| **Alcance** | Todas las vistas de `apps/web` y `apps/fids-player` |
| **Método** | Skill `frontend-design` (regla de trabajo del proyecto para toda vista nueva o rediseñada) |
| **Se ejecuta en** | Sprints S1.11 a S1.14 (`specs/013-` a `specs/016-`) |

Documento de referencia **transversal a los 4 sprints** de rediseño. Cada sprint tiene su propio
`specs/NNN-*/` con spec/plan/tasks, y todos apuntan acá para la dirección estética — no la redefinen.

---

## 1. Punto de partida

De las 14 vistas existentes, **6 tienen identidad visual** (las de S1.10) y **6 no tienen ninguna** —
HTML sin clases, sin `styleUrl`, renderizado por defecto del navegador.

| Vista | Módulo | Estado visual | Líneas | Sprint |
|:---|:---|:---|---:|:---|
| `auth/login` | Identidad | ✅ S1.10 | 61 | revisión en S1.13 |
| `auth/cambiar-password` | Identidad | ✅ S1.10 | 41 | revisión en S1.13 |
| `auth/recuperar` | Identidad | ✅ S1.10 | 35 | revisión en S1.13 |
| `auth/restablecer` | Identidad | ✅ S1.10 | 34 | revisión en S1.13 |
| `auth/verificar-correo` | Identidad | ✅ S1.10 | 18 | revisión en S1.13 |
| `auth/aceptar-invitacion` | Identidad | ✅ S1.10 | 40 | revisión en S1.13 |
| `usuarios/invitar` | Identidad | ✅ S1.10 | 40 | revisión en S1.13 |
| `shell` | — | ✅ S1.10 | — | revisión en S1.13 |
| `vuelos/estado-tiempo-real` | M1 AODB | ❌ sin estilo | 48 | **S1.11** |
| `puertas/tablero-puertas` | M3 Gates | ❌ sin estilo | 103 | **S1.12** |
| `rampa/panel-turnaround` | M4 Ground Ops | ❌ sin estilo | 192 | **S1.12** |
| `billing/panel-facturas` | M5 Billing | ❌ sin estilo | 149 | **S1.13** |
| `tenants/tenant-creation` | Tenancy | ❌ sin estilo | 98 | **S1.13** |
| `fids-player/pantalla-player` | M2 FIDS | ✅ S1.14 | 56 → 3 modos | S1.14 |

### Hallazgo que amplía el alcance (decisión 2 aprobada)

Las vistas sin estilo **todavía piden el JWT pegado a mano en un `<textarea>`**, y sus 4 servicios
(`billing.service.ts`, `puertas.service.ts`, `rampa.service.ts`, y el WS de vuelos) siguen recibiendo
`tokenJwt: string` por parámetro. S1.10 solo lo eliminó de `tenant-creation` (FR-029, T035).

Desde S1.10 eso es **código muerto y engañoso**: el `authInterceptor` ya agrega `Authorization` a toda
petición. El rediseño no puede maquillar un formulario que no debería existir — se elimina, y eso toca
el `.ts` y el `.service.ts`, no solo el HTML.

### Fuera de alcance (decisión 1 aprobada)

M6 (Passenger Experience), M8 (Observability) y M9 (Compliance Hub) están implementados en backend pero
no tienen vista Angular. **Crear vistas nuevas es construir funcionalidad, no rediseñar** — queda fuera
de estos 4 sprints. Si más adelante se les crea vista, deberá seguir esta misma dirección visual.

---

## 2. Dirección de diseño

### 2.1 De dónde sale

El sujeto no es "un SaaS": es una **consola de operaciones aeroportuarias**. Quien la usa mira decenas de
vuelos a la vez, bajo presión de tiempo, muchas veces en una pantalla compartida. El mundo material de
ese usuario tiene artefactos propios y reconocibles:

- La **tira de progreso de vuelo** (*flight progress strip*): tira física de papel, una por vuelo, que el
  controlador mueve entre bahías conforme el vuelo cambia de estado. Ya se usó como motivo decorativo en
  el login de S1.10 — acá pasa a ser **estructural**.
- El **tablero de salidas** (split-flap): monoespaciada, alineación por columnas, contraste alto,
  legible a distancia.
- La **carta de turnaround**: hitos en línea de tiempo (calzos puestos, puertas abiertas, catering,
  combustible, puertas cerradas, calzos fuera).

### 2.2 La decisión central: densidad, no aire

La tentación por defecto sería el dashboard SaaS moderno: tarjetas con mucho margen, números grandes con
etiqueta chica, gradientes suaves. **Se rechaza deliberadamente.** Un controlador que necesita ver 40
vuelos no quiere ver 6 tarjetas bonitas. La referencia correcta es una terminal de operaciones: filas
compactas, numerales tabulares, jerarquía por peso y color, no por tamaño ni por espacio en blanco.

Consecuencia asumida: obliga a que tipografía y espaciado sean **precisos** — la elegancia de una
interfaz densa está en el ritmo vertical exacto, no en la generosidad.

### 2.3 Sistema de tokens

Extiende —no reemplaza— lo definido en `apps/web/src/styles.scss` en S1.10.

**Color:**

| Token | Valor | Uso |
|:---|:---|:---|
| `--ah-navy-950` | `#0a1830` | Fondo de chrome (shell, rail de login) |
| `--ah-navy-900` | `#0e2142` | Superficie elevada sobre navy |
| `--ah-navy-800` | `#16305c` | Borde/divisor sobre navy |
| `--ah-blue-500` | `#2f6fed` | Acción primaria, foco, enlace |
| `--ah-amber-500` | `#f5a623` | Marcador de bahía activa (la tira) |
| `--ah-paper-50` | `#f7f8fa` | Fondo de área de trabajo |
| `--ah-ink-900/600/400` | — | Texto principal / secundario / terciario |
| `--ah-danger-600/50` | — | Error |
| **Nuevos** — semáforo operacional | | |
| `--ah-estado-ok` | verde sobrio | En horario, completado, conciliado |
| `--ah-estado-atencion` | ámbar | Demorado, pendiente, por vencer |
| `--ah-estado-critico` | rojo | Incidencia, SLA vencido, sin señal |
| `--ah-estado-neutro` | gris | Programado, sin datos |

Los cuatro de semáforo son **el único lugar donde entra color saturado** en el área de trabajo. Todo lo
demás es navy/tinta/papel. Eso es lo que hace que un estado crítico salte en una lista de 40 filas.

**Tipografía:**

| Rol | Familia | Uso |
|:---|:---|:---|
| Display | IBM Plex Sans (600) | Títulos de vista, wordmark |
| Cuerpo | IBM Plex Sans (400/500) | Etiquetas, prosa, botones |
| **Datos** | **IBM Plex Mono** | **Todo dato operacional**: vuelo, hora, puerta, id, importe |

La regla del mono define el carácter: en una consola real los datos se alinean por columna porque se
comparan verticalmente. Números proporcionales en una tabla de horarios es un error funcional, no
estético.

**Layout:** rejilla de 4 px, escala `4/8/12/16/24/32/48`. Alto de fila: 40 px. Ancho máximo: sin límite
en vistas de tabla (aprovechan el ancho real), 480 px en formularios.

**Adenda S1.14 — escala tipográfica propia de `fids-player`:** los tokens de color y familia
tipográfica de esta sección se copian tal cual a `apps/fids-player` (sin `@use` del paquete de
primitivos de consola, que no aplica a una pantalla sin interacción), pero la *escala de tamaño* NO
se reutiliza — está pensada para consolas leídas de cerca (40-60cm), no para una pantalla pública
leída a 3+ metros. `fids-player` define su propio tamaño vía `clamp()` con mínimo ≥ 3rem para el
contenido de la plantilla activa, ver `specs/016-fids-player-rediseno/research.md` Decisión 5.

### 2.4 El elemento distintivo: la tira

> **⚠️ SUPERSEDIDA EL 2026-08-04 — leer §2.4.2 antes de aplicar esta sección.**
> El usuario decidió explícitamente migrar las 5 vistas operativas de `.ah-tira` a
> `.ah-tabla`. Esta sección se conserva como registro de la decisión original y porque
> `fids-player` (S1.14) sí conserva el espíritu de la tira; **no describe el estado actual
> de `apps/web`.**

**Un solo componente estructural, reutilizado en los cinco módulos:**

```
│▌ AH 214    MEC → UIO    Puerta 12    14:35    ABORDANDO       │
 ↑  ↑         ↑            ↑            ↑        ↑
 │  mono      mono         mono         mono     estado
 └─ barra de estado (4 px, color de semáforo)
```

| Módulo | Qué representa una tira | Qué marca la barra |
|:---|:---|:---|
| M1 AODB | un vuelo | estado del vuelo |
| M2 FIDS | un vuelo (en grande, sobre navy) | estado del vuelo |
| M3 Gates | una puerta | ocupación / conflicto |
| M4 Ground Ops | un turnaround | desviación del estándar |
| M5 Billing | una factura | estado de conciliación |

Que sea **el mismo componente** es el punto: quien aprende a leer una pantalla ya sabe leer las otras
cinco. No es reutilización por ahorro de código, es coherencia de lectura.

### 2.4.1 Primitivos de diálogo, insignias y retroalimentación (Toasts)

- **`.ah-pill`**: Insignia de estado sólida y redondeada (`.ah-pill--ok`, `.ah-pill--atencion`, `.ah-pill--critico`). Diseñada para columnas de tablas donde el estado es la columna principal.
- **`.ah-modal-fondo` / `.ah-modal`**: Diálogo superpuesto para operaciones de alta o edición sin navegación de página ni pérdida de contexto. Ancho fijo `max-width: 560px`.
- **`.ah-switch`**: Switch visual (checkbox nativo + pista/thumb propios) para un estado binario dentro de un modal — reemplaza "un botón por transición" cuando solo hay 2 estados posibles.
- **`.ah-toast-container` / `.ah-toast`**: Notificaciones flotantes en la esquina superior derecha (`.ah-toast--exito`, `.ah-toast--error`, `.ah-toast--info`, `.ah-toast--aviso`) que confirman operaciones completadas (aprovisionamiento, actualización, borrado físico, copiado al portapapeles).
- **`.ah-btn--peligro`**: Variante de botón destructiva (rojo) para salvaguardas y confirmación de acciones irreversibles (borrado físico).

**La estructura completa del workpanel (lista + búsqueda + paginación) y
del modal "Ver detalles" (tarjeta de contexto, campos editables de
guardado diferido, switch, distribución 70/30, botones a la derecha) está
catalogada aparte, con `usuarios/usuario-list` como referencia viva, en
`docs/diseno/MODAL_Y_WORKPANEL.md` — no se repite acá.

### 2.4.2 Decisión vigente (2026-08-04): la tabla reemplaza a la tira en `apps/web`

Tras completar el workpanel de `tenants` y `usuarios`, el usuario decidió explícitamente —vía
consulta directa— **migrar las 5 vistas operativas de `.ah-tira` a `.ah-tabla`**, unificándolas con
los paneles administrativos. El catálogo completo del patrón de workpanel resultante vive en
`docs/diseno/MODAL_Y_WORKPANEL.md`.

**Estado real de `apps/web` desde esa fecha** — el patrón único es:

> `.ah-panel` (búsqueda) + `.ah-tabla` (columnas) + `.ah-pill` (estado) + `.ah-paginacion` (10 en 10)
> + `.ah-modal` (alta / detalle), con una sola acción por fila ("Ver detalles").

| Vista | Unidad estructural vigente | Semáforo |
|:---|:---|:---|
| `vuelos/estado-tiempo-real` (M1) | fila de `.ah-tabla` | `.ah-pill` por estado de vuelo |
| `puertas/tablero-puertas` (M3) | fila de `.ah-tabla` | `.ah-pill` de ocupación/conflicto |
| `rampa/panel-turnaround` (M4) | fila de `.ah-tabla` | `.ah-pill` de desviación |
| `billing/panel-facturas` (M5) | fila de `.ah-tabla` | `.ah-pill` de estado de factura |
| `tenants` / `usuarios` / `api-keys` / `licencias` | fila de `.ah-tabla` | `.ah-pill` |

**Qué se conserva de §2.2 y §2.4** (la decisión NO fue "hacer un SaaS con aire"): la densidad,
la tipografía mono para todo dato operacional, el semáforo de 4 tonos como único color saturado, y
la coherencia de lectura entre módulos. Lo que cambió es **el contenedor** de esa densidad —de una
tira con barra lateral a una fila de tabla con insignia—, no la filosofía.

**Dónde sigue viva la tira**: `apps/fids-player` (S1.14) conserva el espíritu del artefacto físico
—contenido en mono, alto contraste, sin cromo de interfaz—, que es el contexto donde la metáfora
original tenía más sentido: una pantalla pública leída a distancia.

**Regla para vistas futuras de `apps/web`: usar `.ah-tabla`, no `.ah-tira`.**

### 2.5 Autocrítica (antes de construir)

Revisado contra el riesgo de "diseño genérico de IA":

- ❌ No es crema + serif + terracota, ni negro + verde ácido, ni broadsheet de reglas finas.
- ✅ El navy/ámbar viene del contexto (torre de control nocturna, marcadores de bahía), no de una paleta
  de moda.
- ✅ Densidad y mono son decisiones **funcionales** discutibles, y por eso reales — un diseñador que no
  conociera el dominio habría hecho tarjetas con aire.
- ⚠️ **Riesgo asumido**: la densidad castiga al usuario ocasional (quien entra a facturación una vez al
  mes). Mitigación: en vistas de baja frecuencia (billing, tenants) el ritmo se afloja un escalón, sin
  cambiar el sistema.
- ⚠️ **Lo que NO se hace**: animación ambiental más allá de la del login. En una consola operativa el
  movimiento injustificado es ruido. Única animación nueva permitida: transición de 150 ms del color de
  la barra de estado cuando un estado cambia en vivo — eso **sí** comunica algo.

---

## 3. División en sprints

Cuatro sprints, cada uno con su ciclo Spec Kit completo. La división busca que cada uno cierre con algo
verificable y que ninguno cargue demasiado contexto.

### S1.11 — Sistema de diseño + deuda de JWT + vista canónica (`specs/013-`)

**Por qué primero**: el sistema de diseño necesita un consumidor real que lo pruebe; AODB aporta la tira
canónica que define el patrón del resto. Y la deuda del JWT bloquea cualquier rediseño honesto.

- Sistema: tokens completos (incluido semáforo), primitivos compartidos (`.ah-tira`, `.ah-tabla`,
  `.ah-campo`, `.ah-btn`, `.ah-alerta`, `.ah-vacio`), ritmo vertical. Consolidar `styles.scss` +
  `_auth-form.scss`.
- Deuda: eliminar el `<textarea>` de JWT de las 5 vistas y refactorizar los 4 servicios para que no
  reciban `tokenJwt` — el interceptor ya lo hace.
- Vista: `vuelos/estado-tiempo-real` (M1) — la tira canónica.

**Cierra con**: el sistema existe y está probado en una vista real; la aplicación deja de pedir un token
que ya no necesita en ninguna pantalla.

### S1.12 — Tableros operativos densos (`specs/014-`)

**Por qué juntas**: ambas son consolas de monitoreo denso, mismo ritmo y mismos primitivos; hacerlas
seguidas evita reinterpretar el sistema dos veces.

- `puertas/tablero-puertas` (M3) — tira + ocupación temporal.
- `rampa/panel-turnaround` (M4) — la vista más grande (192 líneas), incorpora la carta de hitos.

**Cierra con**: los dos tableros de tiempo real coherentes entre sí y con M1.

### S1.13 — Vistas administrativas + consolidación (`specs/015-`)

**Por qué juntas**: ambas son de baja frecuencia (ritmo aflojado, mismo criterio), y es el momento
correcto para auditar que las 6 vistas de S1.10 sigan coherentes con el sistema ya formalizado.

- `billing/panel-facturas` (M5) — tira + detalle de factura.
- `tenants/tenant-creation` — formulario, reusa primitivos.
- Auditoría de las 8 vistas de S1.10 (7 de auth/invitación + shell) contra el sistema.

**Cierra con**: `apps/web` completa y coherente de punta a punta.

### S1.14 — FIDS player (`specs/016-`)

**Por qué aparte**: es otra aplicación, otro usuario (nadie — corre sola) y otras restricciones. Se ve a
**3+ metros**, sin interacción, 24/7. Tipografía enorme, contraste máximo, cero elementos de interfaz,
y comportamiento correcto ante "sin señal". Es donde el sistema se lleva al extremo.

- `fids-player/pantalla-player` (M2).

**Cierra con**: el rediseño completo de ambos frontends.

---

## 4. Verificación (todos los sprints)

Cada vista se verifica en el navegador real contra el backend real en Docker (Principio III de la
constitución), no solo "compila":

- Renderiza con datos reales del backend, no con mocks.
- Escritorio y móvil (el shell ya es responsivo; cada vista debe serlo).
- Foco de teclado visible en todo control interactivo.
- `prefers-reduced-motion` respetado (ya global en `styles.scss`).
- Sin errores en consola del navegador.
